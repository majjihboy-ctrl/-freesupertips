"""Corner grading, consensus odds parsing/mapping, and the sync helpers
(with a fake HTTP session -- no network)."""
import decimal
import random
from datetime import timedelta
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from . import market_data as md
from . import multibet_service as mbs
from .models import League, Match, Multibet, MultibetLeg, Prediction, Team
from .multibets import assemble_multibets


class ParsingTests(SimpleTestCase):
    def test_extract_corners(self):
        payload = {"stats": {"home": {"corner_kicks": 6}, "away": {"corner_kicks": 4}}}
        self.assertEqual(md.extract_corners(payload), (6, 4))

    def test_extract_corners_needs_both_sides(self):
        self.assertIsNone(md.extract_corners({"stats": {"home": {"corner_kicks": 6}, "away": {"corner_kicks": None}}}))
        self.assertIsNone(md.extract_corners({"stats": {}}))
        self.assertIsNone(md.extract_corners(None))
        self.assertEqual(md.extract_corners({"stats": {"home": {"corner_kicks": 0}, "away": {"corner_kicks": 0}}}), (0, 0))

    def test_extract_consensus_odds_drops_nulls_and_garbage(self):
        payload = {"event_id": 1, "odds": {"home_win": 1.17, "draw": None, "away_win": "x",
                                           "over_25_goals": 1.56, "btts_yes": 0.0, "foo": 3}}
        self.assertEqual(md.extract_consensus_odds(payload), {"home_win": 1.17, "over_25_goals": 1.56})
        self.assertIsNone(md.extract_consensus_odds({"odds": {}}))

    def test_leg_to_odds_key_mapping(self):
        k = md.odds_key_for_leg
        self.assertEqual(k("match_result", "Home Win"), "home_win")
        self.assertEqual(k("match_result", "Draw"), "draw")
        self.assertEqual(k("btts", "BTTS: Yes"), "btts_yes")
        self.assertEqual(k("btts", "BTTS: No"), "btts_no")
        self.assertEqual(k("over_under", "Over 2.5 Goals"), "over_25_goals")
        self.assertEqual(k("over_under", "Under 1.5 Goals"), "under_15_goals")
        self.assertIsNone(k("corners", "Corners Over 9.5"))
        self.assertIsNone(k("draw_no_bet", "Draw No Bet: X"))

    def test_market_odds_for_leg(self):
        blob = {"odds": {"over_25_goals": 1.56}, "fetched_at": "x"}
        self.assertEqual(md.market_odds_for_leg(blob, "over_under", "Over 2.5 Goals"), 1.56)
        self.assertIsNone(md.market_odds_for_leg(blob, "over_under", "Over 3.5 Goals"))
        self.assertIsNone(md.market_odds_for_leg(None, "btts", "BTTS: Yes"))


class CornerGradingTests(SimpleTestCase):
    def test_corners(self):
        g = lambda label, total: mbs.grade_selection("corners", label, 1, 1, "H", "A", total)
        self.assertEqual(g("Corners Over 9.5", 11), "won")
        self.assertEqual(g("Corners Over 9.5", 9), "lost")
        self.assertEqual(g("Corners Over 8.5", 9), "won")
        self.assertEqual(g("Corners Over 9.5", None), "unverified")


class MarketPricingTests(SimpleTestCase):
    def test_supplied_market_price_is_used_and_flagged(self):
        options = []
        for i in range(40):
            options.append({"match_id": i, "market_type": "match_result", "label": f"Home Win",
                            "probability": 70.0, "odds": 1.45, "odds_source": "market"})
            options.append({"match_id": i + 100, "market_type": "corners", "label": "Corners Over 9.5",
                            "probability": 70.0})
        result = assemble_multibets(options)
        self.assertTrue(result)
        for mb in result:
            for leg in mb["legs"]:
                if leg["match_id"] < 100:
                    self.assertEqual((leg["odds"], leg["odds_source"]), (1.45, "market"))
                else:
                    self.assertEqual(leg["odds_source"], "model")
                    self.assertAlmostEqual(leg["odds"], 1.43, places=2)
            self.assertTrue(4.0 <= mb["combined_odds"] <= 5.0)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, timeout=None):
        self.calls.append(url)
        for suffix, payload in self.routes.items():
            if url.endswith(suffix):
                return FakeResponse(payload)
        return FakeResponse({}, status=404)


class SyncTests(TestCase):
    def setUp(self):
        league = League.objects.create(name="L", country="C")
        self.home = Team.objects.create(name="H", short_name="H", league=league)
        self.away = Team.objects.create(name="A", short_name="A", league=league)
        self.league = league

    def _match(self, ext, status, kickoff):
        return Match.objects.create(league=self.league, home_team=self.home, away_team=self.away,
                                    external_id=ext, status=status, kickoff=kickoff,
                                    home_score=1 if status == "finished" else None,
                                    away_score=2 if status == "finished" else None)

    def test_sync_corners_fills_only_matches_in_corner_legs(self):
        now = timezone.now()
        in_leg = self._match("101", "finished", now - timedelta(hours=5))
        not_in_leg = self._match("102", "finished", now - timedelta(hours=5))
        no_data = self._match("103", "finished", now - timedelta(hours=4))
        mb = Multibet.objects.create(day=timezone.localdate(), tab="corners", number=1,
                                     combined_odds=decimal.Decimal("4.20"), combined_probability=20)
        for m in (in_leg, no_data):
            MultibetLeg.objects.create(multibet=mb, match=m, market_type="corners",
                                       label="Corners Over 9.5", probability=60, odds=decimal.Decimal("1.67"))
        session = FakeSession({
            "/events/101/stats/": {"stats": {"home": {"corner_kicks": 7}, "away": {"corner_kicks": 5}}},
            "/events/103/stats/": {"stats": {"home": {"corner_kicks": None}, "away": {"corner_kicks": None}}},
        })
        self.assertEqual(md.sync_corners(session), 1)
        in_leg.refresh_from_db(); not_in_leg.refresh_from_db(); no_data.refresh_from_db()
        self.assertEqual((in_leg.home_corners, in_leg.away_corners), (7, 5))
        self.assertIsNone(not_in_leg.home_corners)
        self.assertIsNone(no_data.home_corners)
        self.assertFalse(any("/events/102/" in c for c in session.calls))
        # the leg now grades (12 corners > 9.5) while the unreported one stays unverified
        leg = MultibetLeg.objects.select_related("match", "match__home_team", "match__away_team").get(match=in_leg)
        self.assertEqual(mbs.settle_leg(leg), "won")
        leg2 = MultibetLeg.objects.select_related("match", "match__home_team", "match__away_team").get(match=no_data)
        self.assertEqual(mbs.settle_leg(leg2), "unverified")

    def test_sync_odds_stores_consensus_for_upcoming_predicted_matches(self):
        now = timezone.now()
        soon = self._match("201", "scheduled", now + timedelta(hours=5))
        far = self._match("202", "scheduled", now + timedelta(days=5))
        unpredicted = self._match("203", "scheduled", now + timedelta(hours=6))
        for m in (soon, far):
            Prediction.objects.create(match=m, source="bzzoiro", tip_type="free", prediction="Home Win",
                                      odds=decimal.Decimal("1.50"), confidence=70, markets={})
        session = FakeSession({"/events/201/odds/": {"event_id": 201, "odds": {"home_win": 1.17, "btts_yes": 2.48}}})
        self.assertEqual(md.sync_odds(session), 1)
        soon.refresh_from_db(); far.refresh_from_db(); unpredicted.refresh_from_db()
        self.assertEqual(soon.market_odds["odds"], {"home_win": 1.17, "btts_yes": 2.48})
        self.assertIsNone(far.market_odds)
        self.assertIsNone(unpredicted.market_odds)

    def test_network_failures_leave_data_untouched(self):
        now = timezone.now()
        m = self._match("301", "scheduled", now + timedelta(hours=3))
        Prediction.objects.create(match=m, source="bzzoiro", tip_type="free", prediction="Home Win",
                                  odds=decimal.Decimal("1.50"), confidence=70, markets={})
        boom = mock.Mock()
        boom.get.side_effect = RuntimeError("down")
        self.assertEqual(md.sync_odds(boom), 0)
        m.refresh_from_db()
        self.assertIsNone(m.market_odds)

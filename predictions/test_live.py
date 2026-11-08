"""Live multibet tracking: feed parsing, provisional leg states, endpoint."""
import decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import market_data as md
from . import multibet_service as mbs
from .models import League, Match, Multibet, MultibetLeg, Team


class LiveParsingTests(SimpleTestCase):
    def test_parse_live_event(self):
        ev = {"id": 77, "home_score": 1, "away_score": 0, "current_minute": 63, "period": "2nd half",
              "extra_time_score": None, "penalty_shootout": None}
        self.assertEqual(md.parse_live_event(ev),
                         {"id": "77", "home": 1, "away": 0, "minute": 63, "period": "2nd half"})
        self.assertEqual(md.parse_live_event({"event_id": 5, "home_score": 0, "away_score": 0})["id"], "5")

    def test_parse_live_event_rejects_unusable_rows(self):
        self.assertIsNone(md.parse_live_event({"id": 1, "home_score": None, "away_score": 0}))
        self.assertIsNone(md.parse_live_event({"home_score": 1, "away_score": 0}))
        self.assertIsNone(md.parse_live_event("junk"))

    def test_fetch_live_events_handles_list_and_pagination(self):
        class Resp:
            status_code = 200
            def __init__(self, payload): self.payload = payload
            def json(self): return self.payload

        pages = {
            "https://sports.bzzoiro.com/api/v2/events/live/": {
                "results": [{"id": 1, "home_score": 1, "away_score": 1}],
                "next": "https://sports.bzzoiro.com/api/v2/events/live/?offset=1",
            },
            "https://sports.bzzoiro.com/api/v2/events/live/?offset=1": {
                "results": [{"id": 2, "home_score": 0, "away_score": 2}], "next": None},
        }
        session = mock.Mock()
        session.get.side_effect = lambda url, timeout=None: Resp(pages[url])
        out = md.fetch_live_events(session)
        self.assertEqual(set(out), {"1", "2"})
        failing = mock.Mock()
        failing.get.side_effect = RuntimeError("down")
        self.assertIsNone(md.fetch_live_events(failing))


class LiveStateTests(SimpleTestCase):
    def s(self, market, label, h, a):
        return mbs.live_leg_state(market, label, h, a, "Ajax", "PSV")

    def test_over_locks_when_cleared(self):
        self.assertEqual(self.s("over_under", "Over 1.5 Goals", 1, 1), "won")
        self.assertEqual(self.s("over_under", "Over 1.5 Goals", 1, 0), "losing")
        self.assertEqual(self.s("over_under", "Over 2.5 Goals", 0, 0), "losing")

    def test_under_locks_when_broken(self):
        self.assertEqual(self.s("over_under", "Under 2.5 Goals", 2, 1), "lost")
        self.assertEqual(self.s("over_under", "Under 2.5 Goals", 1, 1), "winning")

    def test_btts(self):
        self.assertEqual(self.s("btts", "BTTS: Yes", 1, 1), "won")
        self.assertEqual(self.s("btts", "BTTS: Yes", 1, 0), "losing")
        self.assertEqual(self.s("btts", "BTTS: No", 1, 1), "lost")
        self.assertEqual(self.s("btts", "BTTS: No", 2, 0), "winning")

    def test_result_markets_are_provisional(self):
        self.assertEqual(self.s("match_result", "Home Win", 1, 0), "winning")
        self.assertEqual(self.s("match_result", "Home Win", 0, 1), "losing")
        self.assertEqual(self.s("double_chance", "Double Chance: Ajax or Draw", 0, 0), "winning")
        self.assertEqual(self.s("draw_no_bet", "Draw No Bet: Ajax", 1, 1), "level")
        self.assertEqual(self.s("draw_no_bet", "Draw No Bet: Ajax", 0, 1), "losing")

    def test_corners_unknown(self):
        self.assertEqual(self.s("corners", "Corners Over 9.5", 2, 2), "unknown")


@override_settings(BZZOIRO_API_KEY="test-key")
class LiveEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = get_user_model().objects.create_user("boss", password="pw", is_staff=True)
        self.client.force_login(self.staff)
        league = League.objects.create(name="L", country="C")
        self.home = Team.objects.create(name="Ajax", short_name="AJX", league=league)
        self.away = Team.objects.create(name="PSV", short_name="PSV", league=league)
        self.league = league

    def _leg(self, ext, status="scheduled", label="Over 1.5 Goals", market="over_under"):
        match = Match.objects.create(league=self.league, home_team=self.home, away_team=self.away,
                                     external_id=ext, status=status, kickoff=timezone.now())
        mb, _ = Multibet.objects.get_or_create(day=timezone.localdate(), tab="mix", number=1,
                                               defaults={"combined_odds": decimal.Decimal("4.20")})
        return MultibetLeg.objects.create(multibet=mb, match=match, market_type=market, label=label,
                                          probability=70, odds=decimal.Decimal("1.43"))

    def test_nothing_to_track_makes_no_api_call(self):
        with mock.patch.object(md, "fetch_live_events") as fetch:
            data = self.client.get(reverse("api_live_scores")).json()
        self.assertEqual(data, {"live": False, "status": "no_legs", "matches": {}})
        fetch.assert_not_called()

    def test_live_match_returns_score_and_leg_state(self):
        leg = self._leg("900")
        other = self._leg("901", label="BTTS: Yes", market="btts")
        feed = {"900": {"id": "900", "home": 2, "away": 0, "minute": 58, "period": "2nd half"}}
        with mock.patch.object(md, "fetch_live_events", return_value=feed):
            data = self.client.get(reverse("api_live_scores")).json()
        self.assertTrue(data["live"])
        self.assertEqual(data["status"], "live")
        self.assertEqual(list(data["matches"]), ["900"])
        entry = data["matches"]["900"]
        self.assertEqual(entry["score"], "2\u20130")
        self.assertEqual(entry["minute"], 58)
        self.assertEqual(entry["legs"], {str(leg.id): "won"})
        self.assertNotIn(str(other.id), entry["legs"])

    def test_finished_matches_are_not_tracked_and_upstream_is_cached(self):
        self._leg("910", status="finished")
        with mock.patch.object(md, "fetch_live_events") as fetch:
            self.assertFalse(self.client.get(reverse("api_live_scores")).json()["live"])
            fetch.assert_not_called()
        self._leg("911")
        with mock.patch.object(md, "fetch_live_events", return_value={}) as fetch:
            self.client.get(reverse("api_live_scores"))
            self.client.get(reverse("api_live_scores"))
            self.assertEqual(fetch.call_count, 1)

    def test_upstream_down_degrades_quietly(self):
        self._leg("920")
        with mock.patch.object(md, "fetch_live_events", return_value=None):
            data = self.client.get(reverse("api_live_scores")).json()
        self.assertEqual(data, {"live": False, "status": "api_down", "matches": {}})

    def test_status_none_live_and_no_key_and_unparsed(self):
        self._leg("950")
        with mock.patch.object(md, "fetch_live_events", return_value={"1": {"id": "1", "home": 0, "away": 0,
                                                                          "minute": 5, "period": "1st"}}):
            self.assertEqual(self.client.get(reverse("api_live_scores")).json()["status"], "none_live")
        cache.clear()
        with override_settings(BZZOIRO_API_KEY=""):
            self.assertEqual(self.client.get(reverse("api_live_scores")).json()["status"], "no_key")

        cache.clear()
        def unparsed(session, max_pages=3, stats=None, raw_sample=None):
            stats.update(raw_count=4, parsed_count=0)
            raw_sample.append({"weird": "shape"})
            return {}
        with mock.patch.object(md, "fetch_live_events", side_effect=unparsed):
            self.assertEqual(self.client.get(reverse("api_live_scores")).json()["status"], "unparsed")

    def test_debug_output_for_admin_shows_raw_sample_and_bypasses_cache(self):
        self._leg("960")
        calls = []
        def fake(session, max_pages=3, stats=None, raw_sample=None):
            calls.append(1)
            stats.update(raw_count=1, parsed_count=1)
            raw_sample.append({"id": 960, "home_score": 1, "away_score": 0})
            return {"960": {"id": "960", "home": 1, "away": 0, "minute": 12, "period": "1st"}}
        with mock.patch.object(md, "fetch_live_events", side_effect=fake):
            first = self.client.get(reverse("api_live_scores") + "?debug=1").json()
            self.client.get(reverse("api_live_scores") + "?debug=1")
        self.assertEqual(len(calls), 2)  # debug always asks the API
        dbg = first["debug"]
        self.assertEqual(dbg["tracked_matches"], 1)
        self.assertTrue(dbg["api_key_set"])
        self.assertEqual(dbg["raw_first_item"], {"id": 960, "home_score": 1, "away_score": 0})
        self.assertEqual(dbg["tracked_external_ids"], ["960"])
        # no debug block unless asked
        with mock.patch.object(md, "fetch_live_events", side_effect=fake):
            self.assertNotIn("debug", self.client.get(reverse("api_live_scores")).json())

    def test_page_exposes_leg_ids_for_the_tracker(self):
        leg = self._leg("930")
        response = self.client.get(reverse("accumulator"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-leg-id="{leg.id}"')
        self.assertContains(response, reverse("api_live_scores"))
        self.assertContains(response, 'id="live-status"')

    def test_live_tracking_is_admin_only(self):
        self._leg("940")
        self.client.logout()
        with mock.patch.object(md, "fetch_live_events") as fetch:
            data = self.client.get(reverse("api_live_scores")).json()
        self.assertEqual(data, {"live": False, "matches": {}})
        fetch.assert_not_called()

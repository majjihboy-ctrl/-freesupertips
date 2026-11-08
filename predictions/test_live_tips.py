"""Near-real-time settlement of normal tips: label parsing, refresh from the
API into Match rows, per-tip live/final state, and the public endpoint."""
import decimal
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import live_service as ls
from .models import League, Match, Prediction, Team


class LabelTests(SimpleTestCase):
    def test_market_type_from_label(self):
        f = ls.market_type_from_label
        self.assertEqual(f("Home Win"), "match_result")
        self.assertEqual(f("Draw"), "match_result")
        self.assertEqual(f("BTTS: Yes"), "btts")
        self.assertEqual(f("Over 2.5 Goals"), "over_under")
        self.assertEqual(f("Under 1.5 Goals"), "over_under")
        self.assertEqual(f("Corners Over 9.5"), "corners")
        self.assertEqual(f("Draw No Bet: Ajax"), "draw_no_bet")
        self.assertEqual(f("Double Chance: Ajax or Draw"), "double_chance")


class FakeResp:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload


class FakeSession:
    """Routes /events/live/ and /events/ (list) to canned payloads."""

    def __init__(self, live=None, events=None, stats=None):
        self.live, self.events, self.stats = live or [], events or [], stats or {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if url.endswith("/events/live/"):
            return FakeResp({"results": self.live, "next": None})
        if url.endswith("/events/"):
            return FakeResp({"results": self.events, "next": None})
        for suffix, payload in self.stats.items():
            if url.endswith(suffix):
                return FakeResp(payload)
        return FakeResp({}, status=404)


class Base(TestCase):
    def setUp(self):
        cache.clear()
        league = League.objects.create(name="L", country="C")
        self.home = Team.objects.create(name="Ajax", short_name="AJX", league=league)
        self.away = Team.objects.create(name="PSV", short_name="PSV", league=league)
        self.league = league

    def match(self, ext, status="scheduled", minutes_ago=30, h=None, a=None):
        return Match.objects.create(
            league=self.league, home_team=self.home, away_team=self.away, external_id=ext,
            status=status, home_score=h, away_score=a,
            kickoff=timezone.now() - timedelta(minutes=minutes_ago),
        )


class RefreshTests(Base):
    def test_scheduled_becomes_live_with_score_and_minute(self):
        m = self.match("1")
        session = FakeSession(live=[{"id": 1, "home_score": 1, "away_score": 0, "current_minute": 33}])
        self.assertEqual(ls.refresh_scores(session), 1)
        m.refresh_from_db()
        self.assertEqual((m.status, m.home_score, m.away_score), ("live", 1, 0))
        self.assertEqual(ls.tip_state(m, "Home Win")["minute"], 33)

    def test_events_list_settles_finished_games(self):
        m = self.match("2", status="live", minutes_ago=110, h=1, a=1)
        session = FakeSession(events=[{"id": 2, "status": "finished", "home_score": 2, "away_score": 1}])
        self.assertEqual(ls.refresh_scores(session), 1)
        m.refresh_from_db()
        self.assertEqual((m.status, m.home_score, m.away_score), ("finished", 2, 1))

    def test_unknown_in_play_status_is_live_not_finished(self):
        m = self.match("3")
        session = FakeSession(events=[{"id": 3, "status": "2nd_half", "home_score": 0, "away_score": 0}])
        ls.refresh_scores(session)
        m.refresh_from_db()
        self.assertEqual(m.status, "live")

    def test_notstarted_changes_nothing_and_finished_is_never_reopened(self):
        waiting = self.match("4", minutes_ago=-20)
        done = self.match("5", status="finished", minutes_ago=120, h=3, a=0)
        session = FakeSession(
            live=[{"id": 5, "home_score": 3, "away_score": 0, "current_minute": 90}],
            events=[{"id": 4, "status": "notstarted", "home_score": None, "away_score": None},
                    {"id": 5, "status": "2nd_half", "home_score": 3, "away_score": 0}],
        )
        self.assertEqual(ls.refresh_scores(session), 0)
        waiting.refresh_from_db(); done.refresh_from_db()
        self.assertEqual(waiting.status, "scheduled")
        self.assertEqual(done.status, "finished")

    def test_newly_finished_corner_match_gets_its_corner_count(self):
        from .models import Prediction
        m = self.match("6", status="live", minutes_ago=110, h=1, a=0)
        Prediction.objects.create(match=m, source="bzzoiro", tip_type="free", prediction="Corners Over 9.5",
                                  market_type="corners", odds=decimal.Decimal("1.60"), confidence=65)
        session = FakeSession(
            events=[{"id": 6, "status": "finished", "home_score": 1, "away_score": 0}],
            stats={"/events/6/stats/": {"stats": {"home": {"corner_kicks": 7}, "away": {"corner_kicks": 5}}}},
        )
        ls.refresh_scores(session)
        m.refresh_from_db()
        self.assertEqual((m.home_corners, m.away_corners), (7, 5))
        self.assertEqual(ls.tip_state(m, "Corners Over 9.5")["state"], "won")

    @override_settings(BZZOIRO_API_KEY="k")
    def test_refresh_is_throttled_across_callers(self):
        with mock.patch.object(ls, "refresh_scores") as refresh:
            self.assertTrue(ls.refresh_if_due())
            self.assertFalse(ls.refresh_if_due())
            self.assertFalse(ls.refresh_if_due())
        self.assertEqual(refresh.call_count, 1)

    @override_settings(BZZOIRO_API_KEY="")
    def test_no_key_means_no_refresh(self):
        self.assertFalse(ls.refresh_if_due())


class TipStateTests(Base):
    def test_states(self):
        pending = self.match("10", minutes_ago=-30)
        self.assertEqual(ls.tip_state(pending, "Home Win")["state"], "pending")
        live = self.match("11", status="live", h=1, a=0)
        self.assertEqual(ls.tip_state(live, "Home Win")["state"], "winning")
        self.assertEqual(ls.tip_state(live, "Over 0.5 Goals")["state"], "won")       # locked in
        self.assertEqual(ls.tip_state(live, "BTTS: Yes")["state"], "losing")
        self.assertFalse(ls.tip_state(live, "Home Win")["final"])
        done = self.match("12", status="finished", minutes_ago=150, h=2, a=2)
        self.assertEqual(ls.tip_state(done, "Draw"), {"state": "won", "score": "2\u20132", "minute": None, "final": True})
        self.assertEqual(ls.tip_state(done, "Home Win")["state"], "lost")
        self.assertEqual(ls.tip_state(done, "Draw No Bet: Ajax")["state"], "void")
        self.assertEqual(ls.tip_state(done, "Corners Over 9.5")["state"], "unknown")
        off = self.match("13", status="postponed")
        self.assertEqual(ls.tip_state(off, "Home Win")["state"], "void")


@override_settings(BZZOIRO_API_KEY="k")
class EndpointTests(Base):
    def test_returns_states_and_ignores_garbage(self):
        done = self.match("20", status="finished", minutes_ago=150, h=1, a=0)
        data = self.client.get(reverse("api_live_tips"), {"tip": [f"{done.id}|Home Win", "bad", "x|y", f"{done.id}|"]}).json()
        self.assertEqual(list(data["tips"]), [f"{done.id}|Home Win"])
        self.assertEqual(data["tips"][f"{done.id}|Home Win"]["state"], "won")
        self.assertEqual(self.client.get(reverse("api_live_tips")).json(), {"tips": {}})

    def test_started_match_triggers_refresh_and_returns_fresh_state(self):
        m = self.match("21", status="scheduled", minutes_ago=50)

        def fake_refresh():
            Match.objects.filter(pk=m.pk).update(status="live", home_score=0, away_score=2)
            return True

        with mock.patch.object(ls, "refresh_if_due", side_effect=fake_refresh) as r:
            data = self.client.get(reverse("api_live_tips"), {"tip": f"{m.id}|Away Win"}).json()
        r.assert_called_once()
        self.assertEqual(data["tips"][f"{m.id}|Away Win"]["state"], "winning")
        self.assertEqual(data["tips"][f"{m.id}|Away Win"]["score"], "0\u20132")

    def test_future_or_finished_matches_do_not_trigger_refresh(self):
        future = self.match("22", minutes_ago=-60)
        done = self.match("23", status="finished", minutes_ago=200, h=1, a=1)
        with mock.patch.object(ls, "refresh_if_due") as r:
            self.client.get(reverse("api_live_tips"), {"tip": [f"{future.id}|Draw", f"{done.id}|Draw"]})
        r.assert_not_called()

    def test_tip_cards_carry_the_hooks(self):
        m = self.match("24", minutes_ago=-30)
        Prediction.objects.create(match=m, tip_type="free", prediction="Home Win",
                                  odds=decimal.Decimal("1.75"), confidence=70)
        response = self.client.get(reverse("tips_list", args=["free"]), {"day": "today"})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(f'data-match="{m.id}"', html)
        self.assertIn('data-label="Home Win"', html)
        self.assertIn(reverse("api_live_tips"), html)

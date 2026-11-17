import decimal
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import calls as C
from .models import League, Match, Prediction, Team

MARKETS = {
    "match_result": {"prob_home": 83.0, "prob_draw": 11.0, "prob_away": 6.0},
    "btts": {"prob_yes": 40.0},
    "over_under": {"prob_over_15": 82.0, "prob_over_25": 55.0, "prob_over_35": 30.0},
}


class CallsLogicTests(TestCase):
    def test_only_selections_at_or_above_floor_strongest_first(self):
        out = C.calls_for_markets(MARKETS, "Alpha", "Beta", floor=80)
        labels = [c[1] for c in out]
        self.assertIn("Home Win", labels)
        self.assertIn("Over 1.5 Goals", labels)
        self.assertIn("Double Chance: Alpha or Draw", labels)  # 83 + 11 = 94
        self.assertNotIn("Over 2.5 Goals", labels)
        self.assertEqual([c[2] for c in out], sorted((c[2] for c in out), reverse=True))

    def test_nothing_when_model_is_not_sure(self):
        weak = {"match_result": {"prob_home": 40, "prob_draw": 30, "prob_away": 30}}
        self.assertEqual(C.calls_for_markets(weak, "A", "B", floor=80), [])

    def test_grading(self):
        g = C.grade_call
        self.assertTrue(g("match_result", "Home Win", "A", "B", 2, 0))
        self.assertFalse(g("match_result", "Home Win", "A", "B", 0, 1))
        self.assertTrue(g("double_chance", "Double Chance: A or Draw", "A", "B", 1, 1))
        self.assertFalse(g("double_chance", "Double Chance: A or Draw", "A", "B", 0, 2))
        self.assertTrue(g("double_chance", "Double Chance: A or B", "A", "B", 3, 1))
        self.assertTrue(g("btts", "BTTS: Yes", "A", "B", 1, 1))
        self.assertTrue(g("over_under", "Over 1.5 Goals", "A", "B", 1, 1))
        self.assertFalse(g("over_under", "Under 1.5 Goals", "A", "B", 1, 1))
        self.assertIsNone(g("draw_no_bet", "Draw No Bet: A", "A", "B", 1, 1))  # push
        self.assertIsNone(g("match_result", "Home Win", "A", "B", None, None))  # not played


class CallsPageTests(TestCase):
    def setUp(self):
        self.league = League.objects.create(name="Test League", country="X", external_id="1")
        self.home = Team.objects.create(name="Alpha", short_name="ALP", external_id="11", league=self.league)
        self.away = Team.objects.create(name="Beta", short_name="BET", external_id="12", league=self.league)

    def _match(self, days, status="scheduled", hs=None, as_=None, markets=MARKETS):
        m = Match.objects.create(
            league=self.league, home_team=self.home, away_team=self.away,
            kickoff=timezone.now().replace(hour=12, minute=0) + timedelta(days=days),
            status=status, home_score=hs, away_score=as_, external_id=f"e{days}{status}{hs}",
        )
        Prediction.objects.create(match=m, source="bzzoiro", tip_type="free", prediction="Home Win",
                                  odds=decimal.Decimal("1.20"), confidence=83, markets=markets, market_type="match_result")
        return m

    @override_settings(CALLS_MIN_CONFIDENCE=80)
    def test_today_shows_strongest_call_and_more(self):
        self._match(0)
        resp = self.client.get(reverse("calls"), {"date": "today"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alpha")
        self.assertContains(resp, "more")
        self.assertContains(resp, "% sure")

    def test_yesterday_is_graded_and_counted(self):
        self._match(-1, status="finished", hs=2, as_=0)
        resp = self.client.get(reverse("calls"), {"date": "yesterday"})
        self.assertContains(resp, "Already played")
        self.assertContains(resp, "✓")

    def test_match_below_bar_is_hidden(self):
        self._match(0, markets={"match_result": {"prob_home": 40, "prob_draw": 30, "prob_away": 30}})
        resp = self.client.get(reverse("calls"), {"date": "today"})
        self.assertContains(resp, "No match clears")

    def test_bad_params_do_not_crash(self):
        resp = self.client.get(reverse("calls"), {"date": "nonsense", "league": "abc"})
        self.assertEqual(resp.status_code, 200)

"""End-to-end test of the /accumulator/ multibets page."""
import decimal
import random
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import League, Match, Prediction, Team


def _markets(rng):
    return {
        "match_result": {"prob_home": rng.uniform(40, 80), "prob_draw": rng.uniform(10, 25),
                         "prob_away": rng.uniform(5, 30)},
        "btts": {"prob_yes": rng.uniform(30, 80)},
        "over_under": {"prob_over_15": rng.uniform(60, 92), "prob_over_25": rng.uniform(35, 75),
                       "prob_over_35": rng.uniform(15, 50)},
        "corners": {"prob_over_85": rng.uniform(50, 85), "prob_over_95": rng.uniform(40, 75),
                    "prob_over_105": rng.uniform(25, 65)},
        "draw_no_bet": {"prob_home": rng.uniform(40, 90)},
    }


class AccumulatorViewTests(TestCase):
    def setUp(self):
        rng = random.Random(7)
        league = League.objects.create(name="Test League", country="Nowhere")
        today = timezone.localtime().date()
        day_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        for i in range(50):
            home = Team.objects.create(name=f"Home {i}", short_name=f"H{i:02d}", league=league)
            away = Team.objects.create(name=f"Away {i}", short_name=f"A{i:02d}", league=league)
            match = Match.objects.create(
                league=league, home_team=home, away_team=away, status="scheduled",
                kickoff=day_start + timedelta(hours=1, minutes=i % 23),
            )
            Prediction.objects.create(
                match=match, source="bzzoiro", tip_type="free", prediction="Home Win",
                odds=decimal.Decimal("1.50"), confidence=70, markets=_markets(rng),
            )

    def test_page_shows_ten_distinct_multibets(self):
        response = self.client.get(reverse("accumulator"))
        self.assertEqual(response.status_code, 200)
        multibets = response.context["multibets"]
        self.assertEqual(len(multibets), 10)
        seen = set()
        for mb in multibets:
            ids = [leg["match_id"] for leg in mb["legs"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertFalse(seen & set(ids))
            seen |= set(ids)
            self.assertLessEqual(len(ids), 5)
            self.assertTrue(4.0 <= mb["combined_odds"] <= 5.0)
        self.assertContains(response, "Multibet #10")

    def test_every_tab_obeys_the_rules_and_single_market_tabs_stay_pure(self):
        expected_market = {"1x2": "match_result", "gg": "btts", "goals": "over_under",
                           "corners": "corners", "dnb": "draw_no_bet"}
        built = 0
        for tab, market in expected_market.items():
            response = self.client.get(reverse("accumulator"), {"tab": tab})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(any(t["active"] and t["slug"] == tab for t in response.context["tabs"]))
            seen = set()
            for mb in response.context["multibets"]:
                built += 1
                ids = [leg["match_id"] for leg in mb["legs"]]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertFalse(seen & set(ids), f"{tab}: match repeated across multibets")
                seen |= set(ids)
                self.assertGreaterEqual(len(ids), 2)
                self.assertTrue(4.0 <= mb["combined_odds"] <= 5.0)
                self.assertTrue(all(leg["market_type"] == market for leg in mb["legs"]),
                                f"{tab}: mixed markets in one multibet")
        self.assertGreater(built, 0)

    def test_mega_tab_is_a_long_1x2_accumulator_near_222(self):
        response = self.client.get(reverse("accumulator"), {"tab": "mega"})
        self.assertEqual(response.status_code, 200)
        multibets = response.context["multibets"]
        self.assertTrue(multibets)
        self.assertEqual((response.context["min_odds"], response.context["max_odds"]), (200.0, 250.0))
        seen = set()
        for mb in multibets:
            ids = [leg["match_id"] for leg in mb["legs"]]
            self.assertFalse(seen & set(ids))
            seen |= set(ids)
            self.assertTrue(200 <= mb["combined_odds"] <= 250)
            self.assertGreater(len(ids), 5)
            self.assertTrue(all(leg["market_type"] == "match_result" and leg["label"] != "Draw"
                                for leg in mb["legs"]))
        self.assertContains(response, "1X2 favourites only")

    def test_unknown_tab_falls_back_to_mix(self):
        response = self.client.get(reverse("accumulator"), {"tab": "nonsense"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "mix")

    def test_page_renders_when_there_are_no_fixtures(self):
        Prediction.objects.all().delete()
        response = self.client.get(reverse("accumulator"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "multibets today")

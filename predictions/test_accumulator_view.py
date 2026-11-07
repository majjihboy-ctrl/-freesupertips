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

    def test_page_renders_when_there_are_no_fixtures(self):
        Prediction.objects.all().delete()
        response = self.client.get(reverse("accumulator"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No multibets yet")

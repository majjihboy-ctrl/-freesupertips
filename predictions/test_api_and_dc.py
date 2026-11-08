"""Double Chance tab + the public JSON endpoints."""
import decimal
import json
import random
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from . import multibet_service as mbs
from .market_picks import extract_family_selections
from .models import League, Match, Prediction, Team


class DoubleChanceTests(SimpleTestCase):
    def test_probabilities_are_sums_of_1x2(self):
        markets = {"match_result": {"prob_home": 50.0, "prob_draw": 30.0, "prob_away": 20.0}}
        sel = {l: p for t, l, p in extract_family_selections(markets, "Ajax", "PSV") if t == "double_chance"}
        self.assertEqual(sel["Double Chance: Ajax or Draw"], 80.0)
        self.assertEqual(sel["Double Chance: PSV or Draw"], 50.0)
        self.assertEqual(sel["Double Chance: Ajax or PSV"], 70.0)

    def test_grading(self):
        g = lambda label, h, a: mbs.grade_selection("double_chance", label, h, a, "Ajax", "PSV")
        self.assertEqual(g("Double Chance: Ajax or Draw", 1, 1), "won")
        self.assertEqual(g("Double Chance: Ajax or Draw", 0, 1), "lost")
        self.assertEqual(g("Double Chance: PSV or Draw", 0, 0), "won")
        self.assertEqual(g("Double Chance: PSV or Draw", 2, 1), "lost")
        self.assertEqual(g("Double Chance: Ajax or PSV", 0, 0), "lost")
        self.assertEqual(g("Double Chance: Ajax or PSV", 3, 0), "won")

    def test_tab_registered(self):
        self.assertIn("dc", mbs.TAB_MARKET)
        self.assertEqual(mbs.TAB_MARKET["dc"], "double_chance")


def _markets(rng):
    h = rng.uniform(25, 60)
    d = rng.uniform(15, 30)
    return {
        "match_result": {"prob_home": h, "prob_draw": d, "prob_away": 100 - h - d},
        "btts": {"prob_yes": rng.uniform(30, 80)},
        "over_under": {"prob_over_15": rng.uniform(60, 92), "prob_over_25": rng.uniform(35, 75),
                       "prob_over_35": rng.uniform(15, 50)},
        "corners": {"prob_over_85": rng.uniform(50, 85), "prob_over_95": rng.uniform(40, 75),
                    "prob_over_105": rng.uniform(25, 65)},
        "draw_no_bet": {"prob_home": rng.uniform(40, 90)},
    }


class ApiTests(TestCase):
    def setUp(self):
        rng = random.Random(3)
        league = League.objects.create(name="Test League", country="X")
        today = timezone.localdate()
        self.tomorrow = today + timedelta(days=1)
        t_start = timezone.make_aware(datetime.combine(self.tomorrow, datetime.min.time()))
        d_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        for i in range(50):
            for day_start, tag in ((d_start, "T"), (t_start, "N")):
                home = Team.objects.create(name=f"{tag}H{i}", short_name=f"{tag}H{i}", league=league)
                away = Team.objects.create(name=f"{tag}A{i}", short_name=f"{tag}A{i}", league=league)
                match = Match.objects.create(
                    league=league, home_team=home, away_team=away, status="scheduled",
                    kickoff=day_start + timedelta(hours=12, minutes=i % 40),
                )
                Prediction.objects.create(
                    match=match, source="bzzoiro", tip_type="free", prediction="Home Win",
                    market_type="match_result", odds=decimal.Decimal("1.50"),
                    confidence=50 + i, markets=_markets(rng),
                )

    def test_double_chance_page_obeys_the_rules(self):
        response = self.client.get(reverse("accumulator"), {"tab": "dc"})
        self.assertEqual(response.status_code, 200)
        seen = set()
        for mb in response.context["multibets"]:
            ids = [leg["match_id"] for leg in mb["legs"]]
            self.assertFalse(seen & set(ids))
            seen |= set(ids)
            self.assertTrue(2 <= len(ids) <= 5)
            self.assertTrue(4.0 <= mb["combined_odds"] <= 5.0)
            self.assertTrue(all(leg["market_type"] == "double_chance" for leg in mb["legs"]))
        self.assertTrue(response.context["multibets"])

    def test_tips_json_for_tomorrow(self):
        response = self.client.get("/api/tips/tomorrow.json?n=3")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["date"], self.tomorrow.isoformat())
        self.assertEqual(data["count"], 3)
        confidences = [t["confidence"] for t in data["tips"]]
        self.assertEqual(confidences, sorted(confidences, reverse=True))
        self.assertEqual(set(data["tips"][0]), {"match", "league", "kickoff", "pick", "market", "confidence", "odds"})
        self.assertEqual(self.client.get(f"/api/tips/{self.tomorrow.isoformat()}.json").status_code, 200)
        self.assertEqual(self.client.get("/api/tips/nonsense.json").status_code, 404)

    def test_multibets_json_public_has_no_results(self):
        response = self.client.get("/api/multibets/gg.json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["tab"], "gg")
        self.assertTrue(data["multibets"])
        self.assertNotIn("summary", data)
        mb = data["multibets"][0]
        self.assertTrue(4.0 <= mb["combined_odds"] <= 5.0)
        self.assertNotIn("status", mb)
        self.assertEqual(set(mb["legs"][0]), {"match", "kickoff", "pick", "confidence", "odds", "odds_source"})
        self.assertEqual(self.client.get("/api/multibets/nope.json").status_code, 404)
        self.assertIn("public", response["Cache-Control"])

    def test_multibets_json_admin_gets_grading_and_dates(self):
        staff = get_user_model().objects.create_user("boss", password="pw", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get("/api/multibets/gg.json")
        data = json.loads(response.content)
        self.assertIn("summary", data)
        mb = data["multibets"][0]
        self.assertIn("status", mb)
        self.assertEqual(set(mb["legs"][0]), {"match", "kickoff", "pick", "confidence", "odds",
                                              "odds_source", "result", "score"})
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.get(f"/api/multibets/gg/{timezone.localdate().isoformat()}.json").status_code, 200)

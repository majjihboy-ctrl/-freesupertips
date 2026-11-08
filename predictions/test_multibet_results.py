"""Multibet grading, saving and previous-day results."""
import decimal
import random
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from . import multibet_service as mbs
from .models import League, Match, Multibet, Prediction, Team
from .test_accumulator_view import _markets


class GradingTests(SimpleTestCase):
    def g(self, market, label, h, a):
        return mbs.grade_selection(market, label, h, a, "Home", "Away")

    def test_match_result(self):
        self.assertEqual(self.g("match_result", "Home Win", 2, 1), "won")
        self.assertEqual(self.g("match_result", "Home Win", 1, 1), "lost")
        self.assertEqual(self.g("match_result", "Draw", 0, 0), "won")
        self.assertEqual(self.g("match_result", "Away Win", 0, 3), "won")

    def test_btts(self):
        self.assertEqual(self.g("btts", "BTTS: Yes", 1, 1), "won")
        self.assertEqual(self.g("btts", "BTTS: Yes", 2, 0), "lost")
        self.assertEqual(self.g("btts", "BTTS: No", 2, 0), "won")

    def test_over_and_under_goals(self):
        self.assertEqual(self.g("over_under", "Over 2.5 Goals", 2, 1), "won")
        self.assertEqual(self.g("over_under", "Over 2.5 Goals", 1, 1), "lost")
        self.assertEqual(self.g("over_under", "Under 2.5 Goals", 1, 1), "won")
        self.assertEqual(self.g("over_under", "Under 1.5 Goals", 1, 1), "lost")

    def test_draw_no_bet(self):
        self.assertEqual(self.g("draw_no_bet", "Draw No Bet: Home", 1, 0), "won")
        self.assertEqual(self.g("draw_no_bet", "Draw No Bet: Away", 1, 0), "lost")
        self.assertEqual(self.g("draw_no_bet", "Draw No Bet: Home", 2, 2), "void")

    def test_corners_cannot_be_verified(self):
        self.assertEqual(self.g("corners", "Corners Over 9.5", 3, 3), "unverified")

    def test_multibet_status(self):
        self.assertEqual(mbs.settle_multibet(["won", "won", "won"]), "won")
        self.assertEqual(mbs.settle_multibet(["won", "lost", "pending"]), "lost")
        self.assertEqual(mbs.settle_multibet(["won", "pending"]), "pending")
        self.assertEqual(mbs.settle_multibet(["won", "unverified"]), "unverified")
        self.assertEqual(mbs.settle_multibet(["won", "void", "won"]), "won")
        self.assertEqual(mbs.settle_multibet(["void", "void"]), "void")


class PreviousDayResultsTests(TestCase):
    def setUp(self):
        # Multibet results are admin-only, so these tests act as staff.
        self.staff = get_user_model().objects.create_user("boss", password="pw", is_staff=True)
        self.client.force_login(self.staff)
        rng = random.Random(11)
        league = League.objects.create(name="L", country="C")
        today = timezone.localdate()
        self.yesterday = today - timedelta(days=1)
        start = timezone.make_aware(datetime.combine(self.yesterday, datetime.min.time()))
        for i in range(50):
            home = Team.objects.create(name=f"H{i}", short_name=f"H{i:02d}", league=league)
            away = Team.objects.create(name=f"A{i}", short_name=f"A{i:02d}", league=league)
            match = Match.objects.create(
                league=league, home_team=home, away_team=away, status="finished",
                home_score=rng.randint(0, 4), away_score=rng.randint(0, 4),
                home_corners=rng.randint(2, 9), away_corners=rng.randint(1, 8),
                kickoff=start + timedelta(hours=10, minutes=i),
            )
            Prediction.objects.create(
                match=match, source="bzzoiro", tip_type="free", prediction="Home Win",
                odds=decimal.Decimal("1.50"), confidence=70, markets=_markets(rng),
            )

    def test_yesterday_is_rebuilt_saved_and_graded(self):
        url = reverse("accumulator") + f"?date={self.yesterday.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        multibets = response.context["multibets"]
        self.assertEqual(len(multibets), 10)
        for mb in multibets:
            self.assertIn(mb["status"], ("won", "lost"))
            self.assertEqual(mb["source"], "reconstructed")
            self.assertTrue(all(leg["state"] in ("won", "lost", "void") for leg in mb["legs"]))
            if mb["status"] == "won":
                self.assertTrue(all(leg["state"] in ("won", "void") for leg in mb["legs"]))
            else:
                self.assertTrue(any(leg["state"] == "lost" for leg in mb["legs"]))
        summary = response.context["summary"]
        self.assertEqual(summary["won"] + summary["lost"], 10)
        self.assertNotContains(response, "Place on Mozzart")
        self.assertContains(response, "Rebuilt after the games")
        # saved, so the second view reads the same rows
        self.assertEqual(Multibet.objects.filter(day=self.yesterday, tab="mix").count(), 10)
        again = self.client.get(url).context["multibets"]
        self.assertEqual([m["combined_odds"] for m in again], [m["combined_odds"] for m in multibets])

    def test_other_tabs_work_for_past_days(self):
        for tab in ("1x2", "gg", "goals", "dnb", "corners"):
            response = self.client.get(
                reverse("accumulator"), {"tab": tab, "date": self.yesterday.isoformat()})
            self.assertEqual(response.status_code, 200)
            for mb in response.context["multibets"]:
                self.assertTrue(all(leg["market_type"] == mbs.TAB_MARKET[tab] for leg in mb["legs"]))
                if tab == "corners":
                    self.assertIn(mb["status"], ("won", "lost"))

    def test_dates_outside_the_window_fall_back_to_today(self):
        far = (timezone.localdate() - timedelta(days=90)).isoformat()
        response = self.client.get(reverse("accumulator"), {"date": far})
        self.assertTrue(response.context["is_today"])
        future = (timezone.localdate() + timedelta(days=3)).isoformat()
        self.assertTrue(self.client.get(reverse("accumulator"), {"date": future}).context["is_today"])
        self.assertTrue(self.client.get(reverse("accumulator"), {"date": "garbage"}).context["is_today"])

    def test_results_page_shows_multibet_record(self):
        self.client.get(reverse("accumulator") + f"?date={self.yesterday.isoformat()}")
        response = self.client.get(reverse("results"))
        self.assertEqual(response.status_code, 200)
        record = response.context["multibet_record"]
        self.assertTrue(any(r["slug"] == "mix" and r["won"] + r["lost"] == 10 for r in record))
        self.assertContains(response, "Multibets")

    def test_todays_snapshot_is_saved_and_freezes_after_kickoff(self):
        today = timezone.localdate()
        start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        rng = random.Random(5)
        league = League.objects.first()
        for i in range(50):
            home = Team.objects.create(name=f"TH{i}", short_name=f"T{i:02d}", league=league)
            away = Team.objects.create(name=f"TA{i}", short_name=f"U{i:02d}", league=league)
            # kickoffs in the future so the page can build them (clamped inside today)
            match = Match.objects.create(
                league=league, home_team=home, away_team=away, status="scheduled",
                kickoff=start + timedelta(hours=23, minutes=i % 59),
            )
            Prediction.objects.create(
                match=match, source="bzzoiro", tip_type="free", prediction="Home Win",
                odds=decimal.Decimal("1.50"), confidence=70, markets=_markets(rng),
            )
        first = self.client.get(reverse("accumulator")).context["multibets"]
        self.assertTrue(Multibet.objects.filter(day=today, tab="mix").exists())
        self.assertTrue(all(mb["status"] == "pending" for mb in first))
        # a game kicks off -> snapshot freezes: new fixtures no longer change it
        Match.objects.filter(
            id__in=Multibet.objects.filter(day=today, tab="mix").values_list("legs__match_id", flat=True)[:1]
        ).update(kickoff=timezone.now() - timedelta(minutes=5))
        frozen_before = list(Multibet.objects.filter(day=today, tab="mix").values_list("id", flat=True))
        self.client.get(reverse("accumulator"))
        frozen_after = list(Multibet.objects.filter(day=today, tab="mix").values_list("id", flat=True))
        self.assertEqual(frozen_before, frozen_after)

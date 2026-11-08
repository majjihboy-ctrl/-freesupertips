"""Multibet results (grading, history, win rates, live) are admin-only."""
import decimal
import random
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import League, Match, Multibet, Prediction, Team
from .test_accumulator_view import _markets


class AdminOnlyResultsTests(TestCase):
    def setUp(self):
        rng = random.Random(21)
        league = League.objects.create(name="L", country="C")
        today = timezone.localdate()
        self.yesterday = today - timedelta(days=1)
        for day, status in ((self.yesterday, "finished"), (today, "scheduled")):
            start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
            for i in range(50):
                home = Team.objects.create(name=f"{status}H{i}", short_name=f"{status[:1]}H{i}", league=league)
                away = Team.objects.create(name=f"{status}A{i}", short_name=f"{status[:1]}A{i}", league=league)
                match = Match.objects.create(
                    league=league, home_team=home, away_team=away, status=status,
                    home_score=rng.randint(0, 3) if status == "finished" else None,
                    away_score=rng.randint(0, 3) if status == "finished" else None,
                    home_corners=rng.randint(3, 9) if status == "finished" else None,
                    away_corners=rng.randint(2, 8) if status == "finished" else None,
                    kickoff=start + timedelta(hours=23 if status == "scheduled" else 10, minutes=i % 50),
                )
                Prediction.objects.create(
                    match=match, source="bzzoiro", tip_type="free", prediction="Home Win",
                    odds=decimal.Decimal("1.50"), confidence=70, markets=_markets(rng),
                )
        self.staff = get_user_model().objects.create_user("boss", password="pw", is_staff=True)
        self.user = get_user_model().objects.create_user("fan", password="pw")
        # saved history exists (as it would after yesterday was viewed by an admin)
        self.client.force_login(self.staff)
        self.client.get(reverse("accumulator"), {"date": self.yesterday.isoformat()})
        self.client.logout()

    RESULT_MARKERS = ("WON</span>", "LOST</span>", "PENDING</span>", "UNVERIFIED", "mb-mark", "mb-summary",
                      "data-final", "data-leg-id", "result-badge", "result-score", "Rebuilt after the games")

    def _assert_no_results(self, response):
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for marker in self.RESULT_MARKERS:
            self.assertNotIn(marker, html, f"leaked: {marker}")

    def test_anonymous_sees_todays_multibets_without_any_results(self):
        response = self.client.get(reverse("accumulator"))
        self._assert_no_results(response)
        self.assertTrue(response.context["multibets"])
        self.assertTrue(all(mb["status"] is None for mb in response.context["multibets"]))
        self.assertTrue(all(leg["state"] is None and leg["score"] == ""
                            for mb in response.context["multibets"] for leg in mb["legs"]))
        self.assertIsNone(response.context["summary"])
        self.assertEqual(response.context["days"], [])
        self.assertContains(response, "Place on Mozzart")

    def test_non_admin_cannot_reach_past_days(self):
        for who in (None, self.user):
            if who:
                self.client.force_login(who)
            response = self.client.get(reverse("accumulator"), {"date": self.yesterday.isoformat()})
            self._assert_no_results(response)
            self.assertTrue(response.context["is_today"])
            self.assertEqual(response.context["day"], timezone.localdate())

    def test_page_is_not_cacheable(self):
        response = self.client.get(reverse("accumulator"))
        self.assertIn("no-cache", response["Cache-Control"])

    def test_results_page_hides_multibet_record_from_non_admins(self):
        for who in (None, self.user):
            if who:
                self.client.force_login(who)
            response = self.client.get(reverse("results"))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["multibet_record"], [])
            self.assertNotContains(response, "Multibets — won / lost")

    def test_admin_sees_everything(self):
        self.client.force_login(self.staff)
        past = self.client.get(reverse("accumulator"), {"date": self.yesterday.isoformat()})
        self.assertFalse(past.context["is_today"])
        html = past.content.decode()
        self.assertTrue("WON</span>" in html or "LOST</span>" in html)
        self.assertIn("mb-summary", html)
        self.assertIsNotNone(past.context["summary"])
        results = self.client.get(reverse("results"))
        self.assertTrue(results.context["multibet_record"])
        self.assertContains(results, "Multibets — won / lost")
        today = self.client.get(reverse("accumulator"))
        self.assertContains(today, "data-leg-id")

    def test_non_staff_login_is_not_admin(self):
        self.client.force_login(self.user)
        self._assert_no_results(self.client.get(reverse("accumulator")))
        data = self.client.get("/api/multibets/mix.json").json()
        self.assertNotIn("summary", data)

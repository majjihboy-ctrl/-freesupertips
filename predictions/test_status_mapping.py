from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from predictions.management.commands.import_bzzoiro import map_status
from predictions.models import League, Match, Team


class MapStatusTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_known_statuses(self):
        k = self.now + timedelta(days=1)
        self.assertEqual(map_status("notstarted", k, now=self.now), "scheduled")
        self.assertEqual(map_status("upcoming", k, now=self.now), "scheduled")
        self.assertEqual(map_status("unresolved", k, now=self.now), "scheduled")
        self.assertEqual(map_status("2nd_half", self.now, now=self.now), "live")
        self.assertEqual(map_status("finished", self.now, now=self.now), "finished")
        self.assertEqual(map_status("Suspended", self.now, now=self.now), "postponed")

    def test_unknown_future_fixture_is_never_live(self):
        k = self.now + timedelta(days=1)
        self.assertEqual(map_status("something_new", k, now=self.now), "scheduled")
        self.assertEqual(map_status(None, k, now=self.now), "scheduled")

    def test_unknown_recent_kickoff_is_live(self):
        k = self.now - timedelta(hours=1)
        self.assertEqual(map_status("something_new", k, now=self.now), "live")

    def test_unknown_old_kickoff(self):
        k = self.now - timedelta(hours=10)
        self.assertEqual(map_status("something_new", k, has_score=True, now=self.now), "finished")
        self.assertEqual(map_status("something_new", k, has_score=False, now=self.now), "postponed")


class HomeLiveWindowTests(TestCase):
    def _match(self, ext, kickoff, status="live"):
        lg, _ = League.objects.get_or_create(name="Test League", defaults={"country": "X"})
        h, _ = Team.objects.get_or_create(name=f"H{ext}", defaults={"short_name": f"H{ext}", "league": lg})
        a, _ = Team.objects.get_or_create(name=f"A{ext}", defaults={"short_name": f"A{ext}", "league": lg})
        return Match.objects.create(league=lg, home_team=h, away_team=a, kickoff=kickoff, status=status, external_id=ext)

    def test_future_and_stale_live_rows_are_hidden(self):
        now = timezone.now()
        self._match("1", now + timedelta(days=1))   # flagged live but not kicked off
        self._match("2", now - timedelta(hours=20))  # stuck live
        ok = self._match("3", now - timedelta(minutes=50))
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        ids = [m.pk for m in resp.context["live_matches"]]
        self.assertEqual(ids, [ok.pk])

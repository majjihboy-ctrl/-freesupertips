"""
Basic regression tests for the predictions app.

Run with: python manage.py test predictions
(or `pytest` if pytest-django is configured)

Rewritten against the current schema: the old Tip/TipLeg pair was replaced
by the single-market `Prediction` model, there is no `stats` view in this
codebase, the Dixon-Coles engine was removed in favor of manually entered
predictions on Match (win_prob_home/draw/away, pick, proj_home/away_score),
and Stripe was replaced with manually-issued VIPCode redemption -- so tests
for all of those were removed rather than left broken.

These cover:
- Manual Match prediction fields
- VIP code redemption
- Prediction display / sitemap rendering
"""
import decimal

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import League, Team, Match, Prediction, Profile, VIPCode


def _make_match(**overrides):
    league = League.objects.create(name="Premier League", country="England")
    home = Team.objects.create(name="Home FC", short_name="HOM", league=league)
    away = Team.objects.create(name="Away FC", short_name="AWY", league=league)
    defaults = dict(
        league=league,
        home_team=home,
        away_team=away,
        kickoff=timezone.now(),
        status="scheduled",
    )
    defaults.update(overrides)
    return Match.objects.create(**defaults)


class MatchPredictionFieldTests(TestCase):
    def test_match_defaults_to_unpredicted(self):
        match = _make_match()
        self.assertIsNone(match.win_prob_home)
        self.assertIsNone(match.win_prob_draw)
        self.assertIsNone(match.win_prob_away)
        self.assertEqual(match.pick, "")
        self.assertIsNone(match.proj_home_score)

    def test_manually_entered_prediction_is_saved(self):
        match = _make_match(
            win_prob_home=55, win_prob_draw=25, win_prob_away=20,
            pick="1", proj_home_score=2, proj_away_score=1,
        )
        match.refresh_from_db()
        self.assertEqual(match.win_prob_home, 55)
        self.assertEqual(match.pick, "1")
        self.assertEqual((match.proj_home_score, match.proj_away_score), (2, 1))


class PredictionModelTests(TestCase):
    def setUp(self):
        self.match = _make_match()

    def test_prediction_str_includes_match_and_market(self):
        pred = Prediction.objects.create(
            match=self.match, tip_type="free", prediction="Over 2.5 Goals",
            odds=decimal.Decimal("1.85"),
        )
        self.assertIn("Over 2.5 Goals", str(pred))
        self.assertIn(str(self.match), str(pred))

    def test_default_tip_type_is_free(self):
        pred = Prediction.objects.create(
            match=self.match, prediction="Home Win", odds=decimal.Decimal("1.75"),
        )
        self.assertEqual(pred.tip_type, "free")

    def test_predictions_ordered_newest_first(self):
        older = Prediction.objects.create(
            match=self.match, prediction="1X", odds=decimal.Decimal("1.25"),
        )
        newer = Prediction.objects.create(
            match=self.match, prediction="X2", odds=decimal.Decimal("1.35"),
        )
        self.assertEqual(list(Prediction.objects.all()), [newer, older])


class VIPCodeRedemptionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="bettor", email="bettor@example.com", password="pw12345!"
        )
        Profile.objects.get_or_create(user=self.user)
        self.client.login(username="bettor", password="pw12345!")

    def test_code_self_generates_when_blank(self):
        code = VIPCode.objects.create(duration_days=30)
        self.assertEqual(len(code.code), 10)

    def test_valid_code_grants_vip_for_its_duration(self):
        code = VIPCode.objects.create(duration_days=7)
        response = self.client.post(reverse("redeem_vip_code"), {"code": code.code})
        self.assertRedirects(response, reverse("home"))

        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_vip)
        self.assertAlmostEqual(
            self.user.profile.vip_expires_at,
            timezone.now() + timedelta(days=7),
            delta=timedelta(seconds=5),
        )

        code.refresh_from_db()
        self.assertTrue(code.is_used)
        self.assertEqual(code.used_by, self.user)

    def test_code_redemption_is_case_insensitive_and_trims_whitespace(self):
        code = VIPCode.objects.create(duration_days=7)
        response = self.client.post(
            reverse("redeem_vip_code"), {"code": f"  {code.code.lower()}  "}
        )
        self.assertRedirects(response, reverse("home"))
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_vip)

    def test_already_used_code_is_rejected(self):
        code = VIPCode.objects.create(duration_days=7, is_used=True)
        response = self.client.post(reverse("redeem_vip_code"), {"code": code.code})
        self.assertRedirects(response, reverse("upgrade"))
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_vip)

    def test_unknown_code_is_rejected(self):
        response = self.client.post(reverse("redeem_vip_code"), {"code": "NOTAREALCODE"})
        self.assertRedirects(response, reverse("upgrade"))
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_vip)

    def test_valid_code_extends_existing_active_vip(self):
        self.user.profile.is_vip = True
        self.user.profile.vip_expires_at = timezone.now() + timedelta(days=5)
        self.user.profile.save()

        code = VIPCode.objects.create(duration_days=10)
        self.client.post(reverse("redeem_vip_code"), {"code": code.code})

        self.user.profile.refresh_from_db()
        self.assertAlmostEqual(
            self.user.profile.vip_expires_at,
            timezone.now() + timedelta(days=15),
            delta=timedelta(seconds=5),
        )


class ViewsTests(TestCase):
    def setUp(self):
        self.match = _make_match(status="live")

    def test_home_view_renders(self):
        Prediction.objects.create(
            match=self.match, tip_type="free", prediction="Home Win",
            odds=decimal.Decimal("1.75"),
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_tips_list_free_shows_free_predictions_only(self):
        Prediction.objects.create(
            match=self.match, tip_type="free", prediction="Home Win",
            odds=decimal.Decimal("1.75"),
        )
        Prediction.objects.create(
            match=self.match, tip_type="vip", prediction="Away Win",
            odds=decimal.Decimal("2.40"),
        )
        response = self.client.get(reverse("tips_list", args=["free"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["predictions"]), 1)

    def test_tips_list_vip_redirects_anonymous_user_to_upgrade(self):
        response = self.client.get(reverse("tips_list", args=["vip"]))
        self.assertRedirects(response, reverse("upgrade"))

    def test_tip_detail_vip_blocks_non_vip_user(self):
        pred = Prediction.objects.create(
            match=self.match, tip_type="vip", prediction="Away Win",
            odds=decimal.Decimal("2.40"),
        )
        response = self.client.get(reverse("tip_detail", args=[pred.pk]))
        self.assertRedirects(response, reverse("upgrade"))

    def test_tips_list_groups_predictions_into_fixtures(self):
        self.match.kickoff = timezone.now()
        self.match.save()
        Prediction.objects.create(
            match=self.match, tip_type="free", prediction="Home Win",
            odds=decimal.Decimal("1.75"),
        )
        Prediction.objects.create(
            match=self.match, tip_type="free", prediction="Over 2.5",
            odds=decimal.Decimal("1.90"),
        )
        response = self.client.get(reverse("tips_list", args=["free"]))
        self.assertEqual(response.status_code, 200)
        fixtures = response.context["fixtures"]
        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["tips_count"], 2)

    def test_match_tips_view_renders_and_links_resolve(self):
        self.match.kickoff = timezone.now()
        self.match.save()
        Prediction.objects.create(
            match=self.match, tip_type="free", prediction="Home Win",
            odds=decimal.Decimal("1.75"),
        )
        response = self.client.get(
            reverse("match_tips", args=["free", self.match.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["predictions"]), 1)

    def test_match_tips_404s_when_no_tips_of_that_type(self):
        response = self.client.get(
            reverse("match_tips", args=["free", self.match.pk])
        )
        self.assertEqual(response.status_code, 404)


class SitemapTests(TestCase):
    def test_sitemap_renders_without_error(self):
        match = _make_match()
        Prediction.objects.create(
            match=match, tip_type="free", prediction="Home Win",
            odds=decimal.Decimal("1.75"),
        )
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
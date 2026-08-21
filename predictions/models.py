from django.db import models
from django.contrib.auth.models import User
import secrets

# Avoids visually ambiguous characters (0/O, 1/I) so codes are easy to
# read back over WhatsApp/phone without transcription errors.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 10


def _generate_unique_code():
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
        if not VIPCode.objects.filter(code=code).exists():
            return code


class VIPCode(models.Model):
    """A single-use code that grants VIP access for a fixed number of days
    when redeemed. Generated in the admin, then handed to a customer
    (e.g. over WhatsApp) after payment is arranged manually -- there's no
    payment processor involved."""

    code = models.CharField(max_length=20, unique=True, blank=True)
    duration_days = models.PositiveIntegerField(
        default=30, help_text="How many days of VIP this code grants when redeemed."
    )
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="redeemed_vip_codes",
    )
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _generate_unique_code()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "used" if self.is_used else "unused"
        return f"{self.code} ({self.duration_days}d, {status})"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_vip = models.BooleanField(default=False)
    vip_expires_at = models.DateTimeField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, default="")

    @property
    def is_vip_active(self):
        from django.utils import timezone
        if not self.is_vip:
            return False
        if self.vip_expires_at and self.vip_expires_at < timezone.now():
            return False
        return True

    def __str__(self):
        return f"{self.user.username} Profile"


class League(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.country})"


class Team(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=10)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="teams")
    crest_color = models.CharField(max_length=7, default="#1a3a5c")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Match(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("live", "Live"),
        ("finished", "Finished"),
        ("postponed", "Postponed"),
    ]

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="matches")
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_matches")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_matches")
    kickoff = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-kickoff"]
        verbose_name_plural = "matches"

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class Prediction(models.Model):
    """A single client-facing tip: one match, one predicted market, one
    price. Replaces the old Tip/TipLeg pair — no stake, no result tracking,
    no free-text reasoning. Just what to bet on and at what odds."""

    TIP_TYPE = [("free", "Free"), ("vip", "VIP")]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="predictions")
    tip_type = models.CharField(max_length=10, choices=TIP_TYPE, default="free")
    prediction = models.CharField(
        max_length=100, help_text="e.g. 'Over 2.5 Goals', '1X', 'Home Win'"
    )
    odds = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.match} — {self.prediction} @ {self.odds}"
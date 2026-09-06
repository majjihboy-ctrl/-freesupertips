import re
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from predictions.models import League, Team, Match, Prediction

API_BASE = "https://sports.bzzoiro.com/api/v2"

# Bzzoiro's event.status values -> our Match.STATUS_CHOICES.
STATUS_MAP = {
    "notstarted": "scheduled",
    "postponed": "postponed",
    "cancelled": "postponed",
    "finished": "finished",
}
# Anything else (1st_half, 2nd_half, halftime, extra_time, etc.) is live.

# Skip generating a tip for a match that's already decided or called off --
# a "prediction" for a finished/cancelled game isn't useful to a customer.
SKIP_STATUSES = {"finished", "cancelled"}

PICK_LABELS = {"H": "Home Win", "D": "Draw", "A": "Away Win"}


def _short_name(name):
    """'Manchester United' -> 'MUN'. Best-effort abbreviation used only
    when first creating a Team row; editable afterwards in admin."""
    letters = re.sub(r"[^A-Za-z ]", "", name).split()
    if not letters:
        return name[:10].upper()
    if len(letters) == 1:
        return letters[0][:10].upper()
    return "".join(w[0] for w in letters)[:10].upper()


class Command(BaseCommand):
    help = (
        "Import upcoming fixtures and model predictions from the Bzzoiro API "
        "(sports.bzzoiro.com). Creates/updates League, Team, Match and "
        "Prediction rows keyed by external_id so repeated runs (e.g. via "
        "Vercel Cron) update in place instead of duplicating."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=3,
            help="How many days ahead (from today) to import fixtures for. Default 3.",
        )
        parser.add_argument(
            "--vip-threshold", type=int, default=60,
            help="Model confidence %% (0-100) at or above which a pick is tagged VIP "
                 "instead of Free. Default 60.",
        )

    def _get_or_link_team(self, external_id, name, league):
        """Same adopt-existing-row logic as leagues, above, applied to teams."""
        team = Team.objects.filter(external_id=str(external_id)).first()
        if team:
            return team
        team = Team.objects.filter(name__iexact=name, external_id__isnull=True).first()
        if team:
            team.external_id = str(external_id)
            team.save(update_fields=["external_id"])
            return team
        return Team.objects.create(
            external_id=str(external_id),
            name=name,
            short_name=_short_name(name),
            league=league,
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "BZZOIRO_API_KEY", "")
        if not api_key:
            self.stderr.write(self.style.ERROR(
                "BZZOIRO_API_KEY is not set -- add it as an environment variable."
            ))
            return

        date_from = timezone.localtime().date()
        date_to = date_from + timedelta(days=options["days"])
        vip_threshold = options["vip_threshold"]

        session = requests.Session()
        session.headers.update({"Authorization": f"Token {api_key}"})

        url = f"{API_BASE}/predictions/"
        params = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "limit": 100,
        }

        created_matches = 0
        updated_matches = 0
        created_predictions = 0
        updated_predictions = 0
        skipped = 0

        while url:
            resp = session.get(url, params=params, timeout=30)
            params = None  # only needed on the first request; "next" already has them
            if resp.status_code != 200:
                self.stderr.write(self.style.ERROR(
                    f"Bzzoiro API returned {resp.status_code}: {resp.text[:500]}"
                ))
                return
            payload = resp.json()

            for row in payload.get("results", []):
                event = row.get("event") or {}
                if event.get("status") in SKIP_STATUSES:
                    skipped += 1
                    continue

                match_result = (row.get("markets") or {}).get("match_result") or {}
                model_info = row.get("model") or {}
                predicted = match_result.get("predicted")
                if not predicted or model_info.get("confidence") is None:
                    skipped += 1
                    continue

                league = League.objects.filter(external_id=str(event["league_id"])).first()
                if not league:
                    # Reuse an existing hand-seeded league with the same name
                    # (no external_id yet) instead of creating a duplicate.
                    league = League.objects.filter(
                        name__iexact=event.get("league_name", ""), external_id__isnull=True
                    ).first()
                    if league:
                        league.external_id = str(event["league_id"])
                        league.save(update_fields=["external_id"])
                    else:
                        league = League.objects.create(
                            external_id=str(event["league_id"]),
                            name=event.get("league_name", "Unknown League"),
                            country="",
                        )
                # Keep the name current if Bzzoiro's league naming changes.
                if league.name != event.get("league_name", league.name):
                    league.name = event["league_name"]
                    league.save(update_fields=["name"])

                home_team = self._get_or_link_team(event["home_team_id"], event["home_team"], league)
                away_team = self._get_or_link_team(event["away_team_id"], event["away_team"], league)

                kickoff = parse_datetime(event["event_date"])
                match_status = STATUS_MAP.get(event.get("status"), "live")

                match, was_created = Match.objects.update_or_create(
                    external_id=str(event["id"]),
                    defaults={
                        "league": league,
                        "home_team": home_team,
                        "away_team": away_team,
                        "kickoff": kickoff,
                        "status": match_status,
                    },
                )
                created_matches += was_created
                updated_matches += not was_created

                confidence_pct = int(
                    (Decimal(str(model_info["confidence"])) * 100).to_integral_value(ROUND_HALF_UP)
                )
                # Bzzoiro doesn't return bookmaker odds on this endpoint --
                # this is the model's own implied odds (100 / probability%),
                # not a real market price.
                prob_for_pick = {"H": match_result.get("prob_home"),
                                  "D": match_result.get("prob_draw"),
                                  "A": match_result.get("prob_away")}.get(predicted)
                implied_odds = Decimal("1.01")
                if prob_for_pick:
                    implied_odds = (Decimal("100") / Decimal(str(prob_for_pick))).quantize(Decimal("0.01"))

                tip_type = "vip" if confidence_pct >= vip_threshold else "free"

                _, was_created = Prediction.objects.update_or_create(
                    match=match, source="bzzoiro",
                    defaults={
                        "tip_type": tip_type,
                        "prediction": PICK_LABELS.get(predicted, predicted),
                        "odds": implied_odds,
                        "confidence": confidence_pct,
                    },
                )
                created_predictions += was_created
                updated_predictions += not was_created

            url = payload.get("next")

        self.stdout.write(self.style.SUCCESS(
            f"Matches: {created_matches} created, {updated_matches} updated. "
            f"Predictions: {created_predictions} created, {updated_predictions} updated. "
            f"Skipped {skipped} (finished/cancelled/no-model-data)."
        ))

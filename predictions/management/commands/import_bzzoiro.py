import re
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import IntegrityError, transaction
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

# A "prediction" for a match that's already been decided or called off isn't
# useful to a customer, so we don't create/update the Prediction row for
# these -- but the Match itself (status, and later its score) still needs
# to stay in sync, for the results/accuracy history page.
SKIP_PREDICTION_STATUSES = {"finished", "cancelled"}

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
        "Vercel Cron) update in place instead of duplicating. Also refreshes "
        "scores for matches that have since finished, via a second pass over "
        "the /events/ endpoint."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=3,
            help="How many days ahead (from today) to import fixtures for. Default 3.",
        )
        parser.add_argument(
            "--results-days-back", type=int, default=3,
            help="How many days back to check for finished-match scores. Default 3.",
        )
        parser.add_argument(
            "--vip-threshold", type=int, default=60,
            help="Model confidence %% (0-100) at or above which a pick is tagged VIP "
                 "instead of Free. Default 60.",
        )

    def _get_or_link_league(self, external_id, name):
        league = League.objects.filter(external_id=str(external_id)).first()
        if league:
            if name and league.name != name:
                league.name = name
                league.save(update_fields=["name"])
            return league
        # Reuse an existing hand-seeded league with the same name (no
        # external_id yet) instead of creating a duplicate.
        league = League.objects.filter(name__iexact=name or "", external_id__isnull=True).first()
        if league:
            try:
                league.external_id = str(external_id)
                league.save(update_fields=["external_id"])
            except IntegrityError:
                # Another concurrent run (e.g. a manual trigger overlapping
                # the scheduled cron) already linked this external_id.
                return League.objects.get(external_id=str(external_id))
            return league
        try:
            with transaction.atomic():
                return League.objects.create(external_id=str(external_id), name=name or "Unknown League", country="")
        except IntegrityError:
            return League.objects.get(external_id=str(external_id))

    def _get_or_link_team(self, external_id, name, league):
        """Same adopt-existing-row logic as leagues, above, applied to teams."""
        team = Team.objects.filter(external_id=str(external_id)).first()
        if team:
            return team
        team = Team.objects.filter(name__iexact=name, external_id__isnull=True).first()
        if team:
            try:
                team.external_id = str(external_id)
                team.save(update_fields=["external_id"])
            except IntegrityError:
                return Team.objects.get(external_id=str(external_id))
            return team
        try:
            with transaction.atomic():
                return Team.objects.create(
                    external_id=str(external_id), name=name, short_name=_short_name(name), league=league,
                )
        except IntegrityError:
            # Another concurrent run created this exact team between our
            # lookup and our insert -- use what it created instead of
            # failing the whole import.
            return Team.objects.get(external_id=str(external_id))

    def _paginated_get(self, session, url, params):
        while url:
            resp = session.get(url, params=params, timeout=30)
            params = None  # only needed on the first request; "next" already has them
            if resp.status_code != 200:
                self.stderr.write(self.style.ERROR(
                    f"Bzzoiro API returned {resp.status_code} for {url}: {resp.text[:500]}"
                ))
                return
            payload = resp.json()
            yield from payload.get("results", [])
            url = payload.get("next")

    def handle(self, *args, **options):
        api_key = getattr(settings, "BZZOIRO_API_KEY", "")
        if not api_key:
            self.stderr.write(self.style.ERROR(
                "BZZOIRO_API_KEY is not set -- add it as an environment variable."
            ))
            return

        today = timezone.localtime().date()
        date_from = today
        date_to = today + timedelta(days=options["days"])
        vip_threshold = options["vip_threshold"]

        session = requests.Session()
        session.headers.update({"Authorization": f"Token {api_key}"})

        created_matches = updated_matches = 0
        created_predictions = updated_predictions = 0
        skipped = 0

        for row in self._paginated_get(
            session, f"{API_BASE}/predictions/",
            {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "limit": 100},
        ):
            event = row.get("event") or {}
            if not event.get("id"):
                skipped += 1
                continue

            league = self._get_or_link_league(event["league_id"], event.get("league_name"))
            home_team = self._get_or_link_team(event["home_team_id"], event["home_team"], league)
            away_team = self._get_or_link_team(event["away_team_id"], event["away_team"], league)

            match, was_created = Match.objects.update_or_create(
                external_id=str(event["id"]),
                defaults={
                    "league": league,
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff": parse_datetime(event["event_date"]),
                    "status": STATUS_MAP.get(event.get("status"), "live"),
                },
            )
            created_matches += was_created
            updated_matches += not was_created

            if event.get("status") in SKIP_PREDICTION_STATUSES:
                skipped += 1
                continue

            markets = row.get("markets") or {}
            match_result = markets.get("match_result") or {}
            model_info = row.get("model") or {}
            predicted = match_result.get("predicted")
            if not predicted or model_info.get("confidence") is None:
                skipped += 1
                continue

            confidence_pct = int(
                (Decimal(str(model_info["confidence"])) * 100).to_integral_value(ROUND_HALF_UP)
            )
            # Bzzoiro doesn't return bookmaker odds on this endpoint -- this
            # is the model's own implied odds (100 / probability%), not a
            # real market price.
            prob_for_pick = {"H": match_result.get("prob_home"),
                              "D": match_result.get("prob_draw"),
                              "A": match_result.get("prob_away")}.get(predicted)
            implied_odds = Decimal("1.01")
            if prob_for_pick:
                implied_odds = (Decimal("100") / Decimal(str(prob_for_pick))).quantize(Decimal("0.01"))

            _, was_created = Prediction.objects.update_or_create(
                match=match, source="bzzoiro",
                defaults={
                    "tip_type": "vip" if confidence_pct >= vip_threshold else "free",
                    "prediction": PICK_LABELS.get(predicted, predicted),
                    "odds": implied_odds,
                    "confidence": confidence_pct,
                    "markets": markets,
                },
            )
            created_predictions += was_created
            updated_predictions += not was_created

        # Second pass: refresh scores for matches that have finished, so the
        # results/accuracy page has something to compare picks against.
        # (The /predictions/ endpoint's embedded event doesn't include
        # scores; /events/ does.)
        score_date_from = today - timedelta(days=options["results_days_back"])
        updated_scores = 0
        for event in self._paginated_get(
            session, f"{API_BASE}/events/",
            {"date_from": score_date_from.isoformat(), "date_to": date_to.isoformat(), "limit": 100},
        ):
            if event.get("home_score") is None or event.get("away_score") is None:
                continue
            updated = Match.objects.filter(external_id=str(event["id"])).update(
                home_score=event["home_score"],
                away_score=event["away_score"],
                status=STATUS_MAP.get(event.get("status"), "finished"),
            )
            updated_scores += updated

        self.stdout.write(self.style.SUCCESS(
            f"Matches: {created_matches} created, {updated_matches} updated. "
            f"Predictions: {created_predictions} created, {updated_predictions} updated. "
            f"Scores refreshed for {updated_scores} finished match(es). "
            f"Skipped {skipped} (finished/cancelled/no-model-data)."
        ))

import re
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from predictions.models import League, Team, Match, Prediction
from predictions.market_picks import best_market_candidate

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
        "(sports.bzzoiro.com). Resolves League/Team/Match/Prediction rows in "
        "a handful of bulk queries (not one per row) to stay well under "
        "Vercel's serverless function timeout. Keyed by external_id so "
        "repeated runs (e.g. via Vercel Cron) update in place instead of "
        "duplicating. Also refreshes scores for matches that have since "
        "finished, via a second pass over the /events/ endpoint."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=3,
            help="How many days ahead (from today) to import fixtures for. Default 3.",
        )
        parser.add_argument(
            "--results-days-back", type=int, default=2,
            help="How many days back to check for finished-match scores. Default 2.",
        )

    def _paginated_get(self, session, url, params):
        while url:
            resp = session.get(url, params=params, timeout=20)
            params = None  # only needed on the first request; "next" already has them
            if resp.status_code != 200:
                self.stderr.write(self.style.ERROR(
                    f"Bzzoiro API returned {resp.status_code} for {url}: {resp.text[:500]}"
                ))
                return
            payload = resp.json()
            yield from payload.get("results", [])
            url = payload.get("next")

    def _resolve_leagues(self, wanted):
        """wanted: {external_id: name}. Returns {external_id: League},
        touching the DB with a small, fixed number of bulk queries
        regardless of how many leagues are involved."""
        result = {}
        ext_ids = [str(k) for k in wanted]

        existing = {l.external_id: l for l in League.objects.filter(external_id__in=ext_ids)}
        result.update(existing)
        to_rename = [l for ext_id, l in existing.items() if wanted.get(ext_id) and l.name != wanted[ext_id]]
        for l in to_rename:
            l.name = wanted[l.external_id]
        if to_rename:
            League.objects.bulk_update(to_rename, ["name"])

        missing_ids = [str(k) for k in wanted if str(k) not in result]
        if not missing_ids:
            return result

        # Adopt existing hand-seeded leagues that share a name but have no
        # external_id yet, instead of creating duplicates.
        names_needed = {wanted[mid] for mid in missing_ids if wanted.get(mid)}
        seeded = {l.name.lower(): l for l in League.objects.filter(name__in=names_needed, external_id__isnull=True)}
        adopted = []
        still_missing = []
        for ext_id in missing_ids:
            name = wanted.get(ext_id) or "Unknown League"
            seeded_league = seeded.pop(name.lower(), None)
            if seeded_league:
                seeded_league.external_id = ext_id
                adopted.append(seeded_league)
                result[ext_id] = seeded_league
            else:
                still_missing.append(ext_id)
        if adopted:
            League.objects.bulk_update(adopted, ["external_id"])

        if still_missing:
            new_objs = [League(external_id=eid, name=wanted.get(eid) or "Unknown League", country="") for eid in still_missing]
            League.objects.bulk_create(new_objs, ignore_conflicts=True)
            # Re-fetch rather than trust bulk_create's returned PKs, since a
            # concurrent run (e.g. a manual trigger overlapping the
            # scheduled cron) could have created the same external_id
            # between our lookup and our insert.
            for l in League.objects.filter(external_id__in=still_missing):
                result[l.external_id] = l

        return result

    def _resolve_teams(self, wanted, league_for_team):
        """wanted: {external_id: name}. league_for_team: {external_id: League}."""
        result = {}
        ext_ids = [str(k) for k in wanted]

        existing = {t.external_id: t for t in Team.objects.filter(external_id__in=ext_ids)}
        result.update(existing)

        missing_ids = [str(k) for k in wanted if str(k) not in result]
        if not missing_ids:
            return result

        names_needed = {wanted[mid] for mid in missing_ids if wanted.get(mid)}
        seeded = {t.name.lower(): t for t in Team.objects.filter(name__in=names_needed, external_id__isnull=True)}
        adopted = []
        still_missing = []
        for ext_id in missing_ids:
            name = wanted.get(ext_id) or "Unknown Team"
            seeded_team = seeded.pop(name.lower(), None)
            if seeded_team:
                seeded_team.external_id = ext_id
                adopted.append(seeded_team)
                result[ext_id] = seeded_team
            else:
                still_missing.append(ext_id)
        if adopted:
            Team.objects.bulk_update(adopted, ["external_id"])

        if still_missing:
            new_objs = [
                Team(external_id=eid, name=wanted.get(eid) or "Unknown Team",
                     short_name=_short_name(wanted.get(eid) or "?"), league=league_for_team[eid])
                for eid in still_missing if eid in league_for_team
            ]
            Team.objects.bulk_create(new_objs, ignore_conflicts=True)
            for t in Team.objects.filter(external_id__in=still_missing):
                result[t.external_id] = t

        return result

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

        session = requests.Session()
        session.headers.update({"Authorization": f"Token {api_key}"})

        rows = list(self._paginated_get(
            session, f"{API_BASE}/predictions/",
            {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "limit": 100},
        ))

        # ---- Pass 1: figure out every league/team this batch references ----
        leagues_wanted, teams_wanted, team_league = {}, {}, {}
        for row in rows:
            event = row.get("event") or {}
            if not event.get("id"):
                continue
            leagues_wanted[str(event["league_id"])] = event.get("league_name")
            teams_wanted[str(event["home_team_id"])] = event.get("home_team")
            teams_wanted[str(event["away_team_id"])] = event.get("away_team")
            team_league[str(event["home_team_id"])] = str(event["league_id"])
            team_league[str(event["away_team_id"])] = str(event["league_id"])

        leagues = self._resolve_leagues(leagues_wanted)
        league_for_team = {tid: leagues.get(lid) for tid, lid in team_league.items() if leagues.get(lid)}
        teams = self._resolve_teams(teams_wanted, league_for_team)

        # ---- Pass 2: resolve existing matches, split into create/update ----
        event_ids = [str((row.get("event") or {}).get("id")) for row in rows if (row.get("event") or {}).get("id")]
        existing_matches = {m.external_id: m for m in Match.objects.filter(external_id__in=event_ids)}

        matches_to_create, matches_to_update = [], []
        skipped = 0
        match_by_event_id = {}

        for row in rows:
            event = row.get("event") or {}
            eid = str(event.get("id") or "")
            if not eid:
                skipped += 1
                continue
            league = leagues.get(str(event["league_id"]))
            home_team = teams.get(str(event["home_team_id"]))
            away_team = teams.get(str(event["away_team_id"]))
            if not (league and home_team and away_team):
                skipped += 1
                continue

            kickoff = parse_datetime(event["event_date"])
            status = STATUS_MAP.get(event.get("status"), "live")

            existing = existing_matches.get(eid)
            if existing:
                existing.league = league
                existing.home_team = home_team
                existing.away_team = away_team
                existing.kickoff = kickoff
                existing.status = status
                matches_to_update.append(existing)
                match_by_event_id[eid] = existing
            else:
                new_match = Match(
                    external_id=eid, league=league, home_team=home_team,
                    away_team=away_team, kickoff=kickoff, status=status,
                )
                matches_to_create.append(new_match)
                match_by_event_id[eid] = new_match

        created_matches = len(matches_to_create)
        updated_matches = len(matches_to_update)
        if matches_to_create:
            Match.objects.bulk_create(matches_to_create, ignore_conflicts=True)
            new_ids = [m.external_id for m in matches_to_create]
            for m in Match.objects.filter(external_id__in=new_ids):
                match_by_event_id[m.external_id] = m
        if matches_to_update:
            Match.objects.bulk_update(matches_to_update, ["league", "home_team", "away_team", "kickoff", "status"])

        # ---- Pass 3: build predictions from the same rows ----
        match_ids = [m.id for m in match_by_event_id.values() if m.id]
        existing_predictions = {
            p.match_id: p for p in Prediction.objects.filter(match_id__in=match_ids, source="bzzoiro")
        }

        preds_to_create, preds_to_update = [], []
        for row in rows:
            event = row.get("event") or {}
            eid = str(event.get("id") or "")
            if not eid or eid not in match_by_event_id:
                continue
            if event.get("status") in SKIP_PREDICTION_STATUSES:
                continue

            markets = row.get("markets") or {}
            best = best_market_candidate(markets, event.get("home_team", ""), event.get("away_team", ""))
            if best is None:
                continue
            market_type, prediction_text, probability = best

            match = match_by_event_id[eid]
            if not match.id:
                continue

            # Market probabilities from Bzzoiro are already 0-100 (e.g.
            # prob_home: 65.0), unlike the old match_result-only code path
            # which multiplied a separate 0-1 "model.confidence" field by
            # 100. Using the winning candidate's own probability keeps the
            # displayed confidence and the free/VIP split consistent with
            # whichever market actually got picked.
            confidence_pct = int(Decimal(str(probability)).to_integral_value(ROUND_HALF_UP))
            implied_odds = (Decimal("100") / Decimal(str(probability))).quantize(Decimal("0.01")) if probability else Decimal("1.01")

            # All single-match tips are free now -- VIP is exclusively the
            # Accumulator feature, not a tier of individual picks.
            tip_type = "free"

            existing = existing_predictions.get(match.id)
            if existing:
                existing.tip_type = tip_type
                existing.prediction = prediction_text
                existing.odds = implied_odds
                existing.confidence = confidence_pct
                existing.markets = markets
                existing.market_type = market_type
                preds_to_update.append(existing)
            else:
                preds_to_create.append(Prediction(
                    match=match, source="bzzoiro", tip_type=tip_type, prediction=prediction_text,
                    odds=implied_odds, confidence=confidence_pct, markets=markets, market_type=market_type,
                ))

        created_predictions = len(preds_to_create)
        updated_predictions = len(preds_to_update)
        if preds_to_create:
            Prediction.objects.bulk_create(preds_to_create, ignore_conflicts=True)
        if preds_to_update:
            Prediction.objects.bulk_update(
                preds_to_update, ["tip_type", "prediction", "odds", "confidence", "markets", "market_type"]
            )

        # ---- Pass 4: refresh richer per-fixture detail + finished scores ----
        # (/predictions/'s embedded event object doesn't carry H2H, weather,
        # or scores; /events/ does.)
        score_date_from = today - timedelta(days=options["results_days_back"])
        events = list(self._paginated_get(
            session, f"{API_BASE}/events/",
            {"date_from": score_date_from.isoformat(), "date_to": date_to.isoformat(), "limit": 100},
        ))
        event_ids2 = [str(e["id"]) for e in events if e.get("id")]
        detail_matches = {m.external_id: m for m in Match.objects.filter(external_id__in=event_ids2)}

        to_update_detail = []
        updated_scores = 0
        for event in events:
            eid = str(event.get("id") or "")
            match = detail_matches.get(eid)
            if not match:
                continue
            match.head_to_head = event.get("head_to_head")
            match.weather = event.get("weather")
            match.round_label = event.get("round_label") or ""
            match.is_local_derby = bool(event.get("is_local_derby"))
            has_score = event.get("home_score") is not None and event.get("away_score") is not None
            if has_score:
                match.home_score = event["home_score"]
                match.away_score = event["away_score"]
                match.status = STATUS_MAP.get(event.get("status"), "finished")
                updated_scores += 1
            to_update_detail.append(match)

        if to_update_detail:
            Match.objects.bulk_update(
                to_update_detail,
                ["head_to_head", "weather", "round_label", "is_local_derby", "home_score", "away_score", "status"],
            )

        self.stdout.write(self.style.SUCCESS(
            f"Matches: {created_matches} created, {updated_matches} updated. "
            f"Predictions: {created_predictions} created, {updated_predictions} updated. "
            f"Detail refreshed for {len(to_update_detail)} match(es), "
            f"scores refreshed for {updated_scores} of those. "
            f"Skipped {skipped} rows with no model data."
        ))

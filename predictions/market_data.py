"""Pulls per-match market data from the Bzzoiro API (free tier) that the
multibet pages need beyond the predictions feed:

* final corner counts   -> GET /api/v2/events/{id}/stats/   (corners legs can be graded)
* consensus bookmaker odds -> GET /api/v2/events/{id}/odds/ (real prices for legs)

Everything here is best-effort: a failed or empty response just leaves the
field unset, and the callers fall back (corner legs stay "unverified", legs
are priced from the model probability instead of the market).
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Match, Prediction

API_BASE = "https://sports.bzzoiro.com/api/v2"
WORKERS = 8
REQUEST_TIMEOUT = 10

# Odds keys served by /events/{id}/odds/ (the documented full set of eleven).
ODDS_KEYS = (
    "home_win", "draw", "away_win",
    "over_15_goals", "over_25_goals", "over_35_goals",
    "under_15_goals", "under_25_goals", "under_35_goals",
    "btts_yes", "btts_no",
)


# --------------------------------------------------------------------------
# Parsing (pure)
# --------------------------------------------------------------------------

def _int_or_none(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_corners(stats_payload):
    """/events/{id}/stats/ payload -> (home_corners, away_corners) or None.

    `corner_kicks` is always present per side but is null when the match
    didn't report it -- None is returned unless BOTH sides are known."""
    stats = (stats_payload or {}).get("stats") or {}
    home = _int_or_none((stats.get("home") or {}).get("corner_kicks"))
    away = _int_or_none((stats.get("away") or {}).get("corner_kicks"))
    if home is None or away is None:
        return None
    return home, away


def extract_consensus_odds(odds_payload):
    """/events/{id}/odds/ payload -> {key: decimal odds} for quoted markets
    (null / non-positive prices are dropped), or None if nothing is quoted."""
    odds = (odds_payload or {}).get("odds") or {}
    out = {}
    for key in ODDS_KEYS:
        try:
            value = float(odds.get(key))
        except (TypeError, ValueError):
            continue
        if value > 1.0:
            out[key] = value
    return out or None


_OU_RE = re.compile(r"(Over|Under) (\d)\.(\d) Goals")


def odds_key_for_leg(market_type, label):
    """Our (market_type, label) -> the /odds/ key that prices it, or None
    when the free consensus feed doesn't quote that selection (draw no bet,
    corners, ...), in which case the leg is priced from the model."""
    if market_type == "match_result":
        return {"Home Win": "home_win", "Draw": "draw", "Away Win": "away_win"}.get(label)
    if market_type == "btts":
        return {"BTTS: Yes": "btts_yes", "BTTS: No": "btts_no"}.get(label)
    if market_type == "over_under":
        m = _OU_RE.fullmatch(label)
        if m:
            key = f"{m.group(1).lower()}_{m.group(2)}{m.group(3)}_goals"
            return key if key in ODDS_KEYS else None
    return None


def market_odds_for_leg(match_odds, market_type, label):
    """Consensus price for a selection from a Match.market_odds blob, or None."""
    key = odds_key_for_leg(market_type, label)
    if not key or not match_odds:
        return None
    try:
        value = float((match_odds.get("odds") or match_odds).get(key))
    except (TypeError, ValueError, AttributeError):
        return None
    return value if value > 1.0 else None


# --------------------------------------------------------------------------
# Network (best-effort)
# --------------------------------------------------------------------------

def _get_json(session, url):
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def _run_parallel(fetch, items, budget_seconds):
    """Run fetch(item) over items with a thread pool, stopping new work once
    the time budget is spent. Returns [(item, result), ...] for finished work."""
    deadline = time.monotonic() + budget_seconds
    results = []

    def guarded(item):
        if time.monotonic() > deadline:
            return item, None
        return item, fetch(item)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for item, result in pool.map(guarded, items):
            results.append((item, result))
    return results


def sync_corners(session, budget_seconds=20, limit=60):
    """Fill home/away corners for recently finished matches that sit in a
    saved corners multibet. Returns how many matches were updated."""
    since = timezone.now() - timedelta(days=14)
    matches = list(
        Match.objects.filter(
            status="finished", kickoff__gte=since, home_corners__isnull=True,
        ).filter(
            Q(multibet_legs__market_type="corners") | Q(predictions__market_type="corners")
        ).exclude(external_id__isnull=True).distinct().order_by("-kickoff")[:limit]
    )
    if not matches:
        return 0

    results = _run_parallel(
        lambda m: extract_corners(_get_json(session, f"{API_BASE}/events/{m.external_id}/stats/")),
        matches, budget_seconds,
    )
    updated = []
    for match, corners in results:
        if corners:
            match.home_corners, match.away_corners = corners
            updated.append(match)
    if updated:
        Match.objects.bulk_update(updated, ["home_corners", "away_corners"])
    return len(updated)


def sync_odds(session, budget_seconds=25, limit=120, horizon_hours=36):
    """Refresh consensus odds for upcoming matches that have a prediction.
    Returns how many matches got prices."""
    now = timezone.now()
    matches = list(
        Match.objects.filter(
            status="scheduled", kickoff__gte=now, kickoff__lt=now + timedelta(hours=horizon_hours),
            id__in=Prediction.objects.filter(source="bzzoiro").values("match_id"),
        ).exclude(external_id__isnull=True).order_by("kickoff")[:limit]
    )
    if not matches:
        return 0

    results = _run_parallel(
        lambda m: extract_consensus_odds(_get_json(session, f"{API_BASE}/events/{m.external_id}/odds/")),
        matches, budget_seconds,
    )
    stamp = now.isoformat()
    updated = []
    for match, odds in results:
        if odds:
            match.market_odds = {"odds": odds, "fetched_at": stamp}
            updated.append(match)
    if updated:
        Match.objects.bulk_update(updated, ["market_odds"])
    return len(updated)


# --------------------------------------------------------------------------
# Live scores (free tier: GET /events/live/, server-cached ~10-30s upstream)
# --------------------------------------------------------------------------

def parse_live_event(item):
    """One item of /events/live/ -> {"id", "home", "away", "minute", "period"}
    or None when it has no usable id / score. Scores are regulation time only
    (extra time and shoot-outs arrive in separate fields we ignore)."""
    if not isinstance(item, dict):
        return None
    event_id = item.get("id", item.get("event_id"))
    home = _int_or_none(item.get("home_score"))
    away = _int_or_none(item.get("away_score"))
    if event_id is None or home is None or away is None:
        return None
    return {
        "id": str(event_id),
        "home": home,
        "away": away,
        "minute": item.get("current_minute"),
        "period": item.get("period") or item.get("status"),
    }


def fetch_live_events(session, max_pages=3, stats=None, raw_sample=None):
    """All currently live events as parsed dicts keyed by event id.
    Returns None if the API could not be reached (callers keep what they had).

    Optional diagnostics: `stats` (dict) receives raw_count / parsed_count;
    `raw_sample` (list) receives the first raw item, so an admin can see the
    real field names when parsing doesn't match."""
    url = f"{API_BASE}/events/live/"
    out = {}
    raw_count = 0
    for _ in range(max_pages):
        payload = _get_json(session, url)
        if payload is None:
            if not out and not raw_count:
                return None
            break
        items = payload if isinstance(payload, list) else (payload.get("results") or [])
        for item in items:
            raw_count += 1
            if raw_sample is not None and not raw_sample:
                raw_sample.append(item)
            parsed = parse_live_event(item)
            if parsed:
                out[parsed["id"]] = parsed
        url = None if isinstance(payload, list) else payload.get("next")
        if not url:
            break
    if stats is not None:
        stats["raw_count"] = raw_count
        stats["parsed_count"] = len(out)
    return out


def fetch_recent_events(session, date_from, date_to, max_pages=5):
    """Events between two dates from /events/ (paginated via `next`), as raw
    dicts with status + scores. Returns [] on any failure."""
    url = f"{API_BASE}/events/"
    params = {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "limit": 100}
    out = []
    for _ in range(max_pages):
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                break
            payload = resp.json()
        except Exception:
            break
        params = None  # `next` already carries them
        out.extend(payload.get("results") or [] if isinstance(payload, dict) else payload or [])
        url = payload.get("next") if isinstance(payload, dict) else None
        if not url:
            break
    return out

"""Near-real-time scores and tip settlement.

Instead of waiting for the nightly import, pages that show tips poll
/api/live-tips.json. That endpoint calls refresh_if_due(), which (at most
once every REFRESH_SECONDS across all callers) pulls live scores plus the
last two days of /events/ from the Bzzoiro API and writes any changed
status / score to the Match rows. Every grade -- single tips, the Results
page, multibets -- reads those rows, so a game flips from live to settled
within about a minute of full time.
"""
import re
from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from . import market_data
from .models import Match
from . import multibet_service as mbs

REFRESH_SECONDS = 30
_LOCK_KEY = "scores-refresh-lock"
_MINUTES_KEY = "live-minutes"

# Same mapping the importer uses; anything else (1st_half, halftime, ...) is live.
STATUS_MAP = {
    "notstarted": "scheduled",
    "postponed": "postponed",
    "cancelled": "postponed",
    "finished": "finished",
}


def market_type_from_label(label):
    """Infer the market of a displayed pick from its text."""
    label = label or ""
    if label.startswith("Draw No Bet"):
        return "draw_no_bet"
    if label.startswith("Double Chance"):
        return "double_chance"
    if label.startswith("BTTS"):
        return "btts"
    if label.startswith("Corners"):
        return "corners"
    if re.match(r"(Over|Under) [\d.]+ Goals", label):
        return "over_under"
    return "match_result"


def _target_state(match, event, live):
    """What status/scores should `match` have, given the API's view of it?
    Returns (status, home, away) or None when there's nothing to apply."""
    live_row = live.get(str(match.external_id))
    if live_row:
        return "live", live_row["home"], live_row["away"]
    if not event:
        return None
    status = STATUS_MAP.get(event.get("status"), "live")
    home, away = event.get("home_score"), event.get("away_score")
    if status == "scheduled":
        return None
    if status in ("postponed",):
        return status, match.home_score, match.away_score
    if home is None or away is None:
        return None
    return status, home, away


def refresh_scores(session):
    """Pull live scores + recent events and write changes. Returns the number
    of matches updated."""
    live = market_data.fetch_live_events(session) or {}
    cache.set(_MINUTES_KEY, {k: v.get("minute") for k, v in live.items()}, 120)

    today = timezone.localdate()
    events = market_data.fetch_recent_events(session, today - timedelta(days=1), today)
    by_id = {str(e["id"]): e for e in events if e.get("id") is not None}

    ids = set(live) | set(by_id)
    if not ids:
        return 0
    now = timezone.now()
    matches = list(Match.objects.filter(
        external_id__in=ids, kickoff__gte=now - timedelta(hours=36), kickoff__lte=now + timedelta(hours=3),
    ))

    changed, newly_finished = [], False
    for m in matches:
        target = _target_state(m, by_id.get(str(m.external_id)), live)
        if not target:
            continue
        status, home, away = target
        if m.status == "finished" and status != "finished":
            continue  # never reopen a settled match from a stale feed
        if (m.status, m.home_score, m.away_score) != (status, home, away):
            if status == "finished" and m.status != "finished":
                newly_finished = True
            m.status, m.home_score, m.away_score = status, home, away
            changed.append(m)
    if changed:
        Match.objects.bulk_update(changed, ["status", "home_score", "away_score"])
    if newly_finished:
        try:
            market_data.sync_corners(session, budget_seconds=8, limit=15)
        except Exception:
            pass
    return len(changed)


def refresh_if_due():
    """Run refresh_scores() at most once per REFRESH_SECONDS (cache lock).
    Returns True if this call did the refresh."""
    api_key = getattr(settings, "BZZOIRO_API_KEY", "")
    if not api_key:
        return False
    if not cache.add(_LOCK_KEY, 1, REFRESH_SECONDS):
        return False
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {api_key}"})
    try:
        refresh_scores(session)
    except Exception:
        return False
    return True


def tip_state(match, label):
    """State of one displayed tip for the page:
    {"state", "score", "minute", "final"}.

    state: won / lost / void (final) | winning / losing / level (in play,
    provisional) | locked won/lost (in play, can't change) | unknown
    (corners without a count) | pending (not started)."""
    market = market_type_from_label(label)
    home_name, away_name = str(match.home_team), str(match.away_team)
    has_score = match.home_score is not None and match.away_score is not None
    score = f"{match.home_score}\u2013{match.away_score}" if has_score else ""

    if match.status == "postponed":
        return {"state": "void", "score": "", "minute": None, "final": True}
    if match.status == "finished" and has_score:
        corners = None
        if match.home_corners is not None and match.away_corners is not None:
            corners = match.home_corners + match.away_corners
        state = mbs.grade_selection(market, label, match.home_score, match.away_score,
                                    home_name, away_name, corners)
        return {"state": "unknown" if state == "unverified" else state,
                "score": score, "minute": None, "final": True}
    if match.status == "live" and has_score:
        minute = (cache.get(_MINUTES_KEY) or {}).get(str(match.external_id))
        return {"state": mbs.live_leg_state(market, label, match.home_score, match.away_score,
                                            home_name, away_name),
                "score": score, "minute": minute, "final": False}
    return {"state": "pending", "score": "", "minute": None, "final": False}

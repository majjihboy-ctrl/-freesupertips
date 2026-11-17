"""High-confidence "calls" page logic.

A *call* is one market selection (1X2, double chance, BTTS, over/under,
corners, draw-no-bet) whose model probability is at least the confidence
floor. Most matches have none -- that is intentional: the page only speaks
when the model is sure, and publishes its full hit/miss record.

Calls are derived on the fly from the Bzzoiro `markets` JSON already stored
on each match's Prediction row, so no schema change is needed.
"""
import re

from django.conf import settings

from .market_picks import extract_family_selections

DEFAULT_MIN_CONFIDENCE = 80
RECORD_DAYS = 45  # matches are kept 45 days (cleanup_old_matches), so the record can't go further back


def min_confidence():
    try:
        return float(getattr(settings, "CALLS_MIN_CONFIDENCE", DEFAULT_MIN_CONFIDENCE))
    except (TypeError, ValueError):
        return float(DEFAULT_MIN_CONFIDENCE)


def calls_for_markets(markets, home_name, away_name, floor=None):
    """[(market_type, label, pct_int)] at/above the floor, strongest first."""
    floor = min_confidence() if floor is None else floor
    seen, out = set(), []
    for market_type, label, prob in extract_family_selections(markets, home_name, away_name):
        if prob is None or prob < floor or label in seen:
            continue
        seen.add(label)
        out.append((market_type, label, int(round(prob))))
    out.sort(key=lambda c: -c[2])
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def grade_call(market_type, label, home_name, away_name, home_score, away_score, home_corners=None, away_corners=None):
    """True = hit, False = miss, None = cannot grade / push."""
    if home_score is None or away_score is None:
        return None
    total = home_score + away_score
    actual = "H" if home_score > away_score else "A" if home_score < away_score else "D"

    if market_type == "match_result":
        return {"Home Win": "H", "Draw": "D", "Away Win": "A"}.get(label) == actual

    if market_type == "double_chance":
        rest = label.split(":", 1)[-1].strip()
        if " or " not in rest:
            return None
        left, right = rest.rsplit(" or ", 1)
        sides = set()
        for token in (left, right):
            if _norm(token) == "draw":
                sides.add("D")
            elif _norm(token) == _norm(home_name):
                sides.add("H")
            elif _norm(token) == _norm(away_name):
                sides.add("A")
            else:
                return None
        return actual in sides

    if market_type == "btts":
        both = home_score > 0 and away_score > 0
        return both if label.endswith("Yes") else (not both if label.endswith("No") else None)

    if market_type == "over_under":
        m = re.search(r"(Over|Under) ([\d.]+) Goals", label)
        if not m:
            return None
        line = float(m.group(2))
        return total > line if m.group(1) == "Over" else total < line

    if market_type == "corners":
        m = re.search(r"Corners Over ([\d.]+)", label)
        if not m or home_corners is None or away_corners is None:
            return None
        return (home_corners + away_corners) > float(m.group(1))

    if market_type == "draw_no_bet":
        if actual == "D":
            return None  # stake returned: neither a hit nor a miss
        name = label.split(":", 1)[-1].strip()
        if _norm(name) == _norm(home_name):
            return actual == "H"
        if _norm(name) == _norm(away_name):
            return actual == "A"
        return None

    return None


def match_calls(match, predictions=None):
    """All calls for a match plus per-call grading (if finished).
    Returns a list of dicts: {market_type, label, pct, hit} strongest first."""
    preds = predictions if predictions is not None else list(match.predictions.all())
    markets = next((p.markets for p in preds if p.markets), None)
    if not markets:
        return []
    home, away = match.home_team.name, match.away_team.name
    finished = match.status == "finished" and match.home_score is not None and match.away_score is not None
    result = []
    for market_type, label, pct in calls_for_markets(markets, home, away):
        hit = grade_call(market_type, label, home, away, match.home_score, match.away_score,
                         match.home_corners, match.away_corners) if finished else None
        result.append({"market_type": market_type, "label": label, "pct": pct, "hit": hit})
    return result


def tally(rows):
    """rows: iterable of lists from match_calls -> (right, wrong)."""
    right = wrong = 0
    for calls in rows:
        for c in calls:
            if c["hit"] is True:
                right += 1
            elif c["hit"] is False:
                wrong += 1
    return right, wrong

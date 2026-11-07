"""Multibet building, saving, grading and history.

* build_multibets()   -> fresh multibets from the day's model picks
* get_multibets()     -> the saved multibets for a (day, tab), creating the
                          snapshot on first use; past days without a snapshot
                          are reconstructed from that day's pre-match data
* settle_*()          -> grade legs / multibets against final scores
* record_for_days()   -> won / lost tallies for the results summary
"""
import re
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .market_data import market_odds_for_leg
from .market_picks import extract_family_selections, extract_market_candidates
from .models import Multibet, MultibetLeg, Prediction
from .multibets import assemble_multibets

ACCA_MIN_CONFIDENCE = 55
HISTORY_DAYS = 14  # how far back the page lets people browse / reconstruct

# (slug, label, market_type or None for the mix)
TABS = [
    ("mix", "Mix", None),
    ("1x2", "1X2", "match_result"),
    ("gg", "GG (BTTS)", "btts"),
    ("goals", "Goals O/U", "over_under"),
    ("corners", "Corners", "corners"),
    ("dnb", "Draw No Bet", "draw_no_bet"),
]
TAB_MARKET = {slug: market for slug, _label, market in TABS}
TAB_LABEL = {slug: label for slug, label, _market in TABS}

_NOT_PLAYED = {"postponed", "cancelled", "canceled", "abandoned"}


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------

def grade_selection(market_type, label, home_score, away_score, home_name, away_name,
                    corners_total=None):
    """-> "won" | "lost" | "void" | "unverified" for a finished match.

    "void" is a Draw No Bet on a draw (stake returned); "unverified" is
    anything we hold no ground truth for (corners when the API never
    reported the match's corner count).
    """
    if market_type == "corners":
        m = re.search(r"Corners Over ([\d.]+)", label)
        if corners_total is None or not m:
            return "unverified"
        return "won" if corners_total > float(m.group(1)) else "lost"

    if market_type == "btts":
        both = home_score > 0 and away_score > 0
        return "won" if (label == "BTTS: Yes") == both else "lost"

    if market_type == "over_under":
        m = re.search(r"(Over|Under) ([\d.]+) Goals", label)
        if not m:
            return "unverified"
        total, line = home_score + away_score, float(m.group(2))
        if m.group(1) == "Over":
            return "won" if total > line else "lost"
        return "won" if total < line else "lost"

    if market_type == "draw_no_bet":
        if home_score == away_score:
            return "void"
        winner = home_name if home_score > away_score else away_name
        return "won" if label == f"Draw No Bet: {winner}" else "lost"

    # match_result (default)
    actual = "Home Win" if home_score > away_score else "Away Win" if home_score < away_score else "Draw"
    return "won" if label == actual else "lost"


def settle_leg(leg):
    """-> "won" | "lost" | "void" | "unverified" | "pending" for a saved leg."""
    match = leg.match
    if match.status in _NOT_PLAYED:
        return "void"
    if match.status != "finished" or match.home_score is None or match.away_score is None:
        return "pending"
    corners_total = None
    if match.home_corners is not None and match.away_corners is not None:
        corners_total = match.home_corners + match.away_corners
    return grade_selection(
        leg.market_type, leg.label, match.home_score, match.away_score,
        str(match.home_team), str(match.away_team), corners_total,
    )


def settle_multibet(leg_states):
    """Combine leg states -> "won" | "lost" | "pending" | "unverified" | "void".

    One lost leg loses the multibet immediately, even while other games are
    still to be played. Void legs drop out (like a bookmaker would)."""
    if "lost" in leg_states:
        return "lost"
    if "pending" in leg_states:
        return "pending"
    if "unverified" in leg_states:
        return "unverified"
    if "won" in leg_states:
        return "won"
    return "void"


# --------------------------------------------------------------------------
# Building
# --------------------------------------------------------------------------

def _day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
    return start, start + timedelta(days=1)


def build_multibets(market_type=None, day=None, upcoming_only=True):
    """Fresh multibets for `day` (default today). With upcoming_only=True only
    matches that are still "scheduled" are used (the live page); with False
    every match of the day that was actually due to be played is used (used to
    reconstruct past days)."""
    day = day or timezone.localdate()
    start, end = _day_bounds(day)
    qs = Prediction.objects.filter(
        source="bzzoiro", match__kickoff__gte=start, match__kickoff__lt=end,
    ).select_related("match", "match__home_team", "match__away_team")
    if upcoming_only:
        qs = qs.filter(match__status="scheduled")
    else:
        qs = qs.exclude(match__status__in=list(_NOT_PLAYED))

    seen_matches = set()
    options = []
    for prediction in qs:
        if prediction.match_id in seen_matches:
            continue  # one prediction row per match is enough
        seen_matches.add(prediction.match_id)
        home, away = prediction.match.home_team, prediction.match.away_team
        if market_type is None:
            candidates = [c for c in extract_market_candidates(prediction.markets, home, away)
                          if c[2] >= ACCA_MIN_CONFIDENCE]
        else:
            candidates = [c for c in extract_family_selections(prediction.markets, home, away)
                          if c[0] == market_type and c[2] >= ACCA_MIN_CONFIDENCE]
        for mtype, label, prob in candidates:
            option = {
                "match_id": prediction.match_id,
                "match": prediction.match,
                "market_type": mtype,
                "label": label,
                "probability": prob,
                "kickoff": prediction.match.kickoff,
            }
            # Real bookmaker consensus price where the free feed quotes this
            # selection (1X2, goals lines, BTTS); otherwise the model-implied
            # price is used by assemble_multibets.
            market_price = market_odds_for_leg(prediction.match.market_odds, mtype, label)
            if market_price:
                option["odds"] = market_price
                option["odds_source"] = "market"
            options.append(option)
    return assemble_multibets(options)


# --------------------------------------------------------------------------
# Saving / loading
# --------------------------------------------------------------------------

def _signature(multibets):
    return sorted(
        tuple(sorted((leg["match_id"], leg["label"], round(float(leg["odds"]), 2)) for leg in mb["legs"]))
        for mb in multibets
    )


def _saved_signature(rows):
    return sorted(
        tuple(sorted((leg.match_id, leg.label, round(float(leg.odds), 2)) for leg in mb.legs.all()))
        for mb in rows
    )


def _save(day, tab, built, source):
    with transaction.atomic():
        Multibet.objects.filter(day=day, tab=tab).delete()
        for mb in built:
            row = Multibet.objects.create(
                day=day, tab=tab, number=mb["number"], combined_odds=mb["combined_odds"],
                combined_probability=mb["combined_probability"], source=source,
            )
            MultibetLeg.objects.bulk_create([
                MultibetLeg(
                    multibet=row, match_id=leg["match_id"], market_type=leg["market_type"],
                    label=leg["label"], probability=leg["probability"],
                    odds=leg["odds"], odds_source=leg.get("odds_source", "model"), position=i,
                )
                for i, leg in enumerate(mb["legs"])
            ])


def _load(day, tab):
    return list(
        Multibet.objects.filter(day=day, tab=tab).prefetch_related(
            "legs", "legs__match", "legs__match__home_team", "legs__match__away_team",
            "legs__match__league",
        ).order_by("number")
    )


def get_multibets(day, tab):
    """Saved multibets for (day, tab) as rows.

    Today: the snapshot is refreshed while none of its games has started
    (so late fixture/probability updates are picked up) and frozen from the
    first kickoff on. Past days: whatever was saved; if nothing was, they are
    rebuilt once from that day's pre-match data and marked reconstructed.
    """
    market = TAB_MARKET[tab]
    today = timezone.localdate()
    rows = _load(day, tab)

    if day > today:
        return []

    if day < today:
        if not rows and (today - day).days <= HISTORY_DAYS:
            built = build_multibets(market, day=day, upcoming_only=False)
            if built:
                _save(day, tab, built, "reconstructed")
                rows = _load(day, tab)
        return rows

    # today
    now = timezone.now()
    started = any(leg.match.kickoff <= now for mb in rows for leg in mb.legs.all())
    if rows and started:
        return rows
    built = build_multibets(market, day=day, upcoming_only=True)
    if rows and _signature(built) == _saved_signature(rows):
        return rows
    if built or rows:
        _save(day, tab, built, "live")
        rows = _load(day, tab)
    return rows


def present(rows):
    """Turn saved rows into plain dicts with graded legs for the template."""
    out = []
    for mb in rows:
        legs = []
        for leg in mb.legs.all():
            state = settle_leg(leg)
            m = leg.match
            legs.append({
                "match": m,
                "match_id": leg.match_id,
                "market_type": leg.market_type,
                "label": leg.label,
                "probability": leg.probability,
                "odds": leg.odds,
                "odds_source": leg.odds_source,
                # Model probability minus what the market price implies;
                # only meaningful for real market prices.
                "edge": round(leg.probability - 100.0 / float(leg.odds), 1)
                        if leg.odds_source == "market" and float(leg.odds) > 1 else None,
                "state": state,
                "score": f"{m.home_score}–{m.away_score}"
                         if m.status == "finished" and m.home_score is not None else "",
            })
        status = settle_multibet([leg["state"] for leg in legs])
        out.append({
            "number": mb.number,
            "legs": legs,
            "combined_odds": mb.combined_odds,
            "combined_probability": mb.combined_probability,
            "status": status,
            "source": mb.source,
        })
    return out


def summarise(presented):
    counts = {"won": 0, "lost": 0, "pending": 0, "unverified": 0, "void": 0}
    for mb in presented:
        counts[mb["status"]] += 1
    settled = counts["won"] + counts["lost"]
    counts["total"] = len(presented)
    counts["settled"] = settled
    counts["win_rate"] = round(100 * counts["won"] / settled) if settled else None
    return counts


def day_options(today=None, days=7):
    """Date selector entries, newest first: Today, Yesterday, then dates."""
    today = today or timezone.localdate()
    out = []
    for i in range(days):
        d = today - timedelta(days=i)
        label = "Today" if i == 0 else "Yesterday" if i == 1 else d.strftime("%a %d %b")
        out.append({"day": d, "label": label, "is_today": i == 0})
    return out


def record_for_days(days=HISTORY_DAYS):
    """Won / lost tallies per tab over the last `days` finished days
    (today excluded) from saved multibets only -- nothing is rebuilt here."""
    today = timezone.localdate()
    since = today - timedelta(days=days)
    rows = list(
        Multibet.objects.filter(day__gte=since, day__lt=today).prefetch_related(
            "legs", "legs__match", "legs__match__home_team", "legs__match__away_team",
        )
    )
    stats = {slug: {"won": 0, "lost": 0, "other": 0} for slug, _l, _m in TABS}
    for mb in rows:
        status = settle_multibet([settle_leg(leg) for leg in mb.legs.all()])
        bucket = stats.get(mb.tab)
        if bucket is None:
            continue
        bucket[status if status in ("won", "lost") else "other"] += 1
    result = []
    for slug, label, _m in TABS:
        s = stats[slug]
        settled = s["won"] + s["lost"]
        if settled or s["other"]:
            result.append({
                "slug": slug, "label": label, "won": s["won"], "lost": s["lost"],
                "settled": settled,
                "win_rate": round(100 * s["won"] / settled) if settled else None,
            })
    return result


def parse_day(value):
    """?date=YYYY-MM-DD -> a date inside the browsable window, else today."""
    today = timezone.localdate()
    try:
        day = datetime.strptime(value or "", "%Y-%m-%d").date()
    except ValueError:
        return today
    if day > today or (today - day).days > HISTORY_DAYS:
        return today
    return day

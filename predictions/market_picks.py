"""Extracts every viable betting market from a Bzzoiro `markets` JSON blob,
as plain (market_type, label, probability) tuples. Shared by:

- import_bzzoiro: picks the single HIGHEST-probability candidate per match
  as that match's primary Prediction, instead of always defaulting to
  match_result (1X2) regardless of how confident that particular market is.
- views._build_accumulator: picks up to 5 candidates across different
  matches/market types, each independently at or above its own threshold.

No confidence filtering happens here -- callers decide their own threshold
(the accumulator wants >=55%, single tips want "just the best one, whatever
that best one turns out to be").
"""

PICK_LABELS = {"H": "Home Win", "D": "Draw", "A": "Away Win"}


def extract_market_candidates(markets, home_team_name, away_team_name):
    """markets: the raw `markets` dict from a Bzzoiro prediction row (or a
    Prediction.markets JSON field). home_team_name/away_team_name: plain
    strings, used only for the Draw No Bet label. Returns a list of
    (market_type, label, probability) tuples, one best pick per market
    family (e.g. only the single most confident Over/Under line, not all
    three)."""
    markets = markets or {}
    candidates = []

    mr = markets.get("match_result") or {}
    probs = {"H": mr.get("prob_home"), "D": mr.get("prob_draw"), "A": mr.get("prob_away")}
    probs = {k: v for k, v in probs.items() if v is not None}
    if probs:
        side, prob = max(probs.items(), key=lambda kv: kv[1])
        candidates.append(("match_result", PICK_LABELS[side], prob))

    btts = (markets.get("btts") or {}).get("prob_yes")
    if btts is not None:
        if btts >= 50:
            candidates.append(("btts", "BTTS: Yes", btts))
        else:
            candidates.append(("btts", "BTTS: No", 100 - btts))

    ou = markets.get("over_under") or {}
    best_ou = None
    for key, line in (("prob_over_15", "1.5"), ("prob_over_25", "2.5"), ("prob_over_35", "3.5")):
        prob = ou.get(key)
        if prob is not None and (best_ou is None or prob > best_ou[2]):
            best_ou = ("over_under", f"Over {line} Goals", prob)
    if best_ou:
        candidates.append(best_ou)

    corners = markets.get("corners") or {}
    best_corners = None
    for key, line in (("prob_over_85", "8.5"), ("prob_over_95", "9.5"), ("prob_over_105", "10.5")):
        prob = corners.get(key)
        if prob is not None and (best_corners is None or prob > best_corners[2]):
            best_corners = ("corners", f"Corners Over {line}", prob)
    if best_corners:
        candidates.append(best_corners)

    dnb = (markets.get("draw_no_bet") or {}).get("prob_home")
    if dnb is not None:
        if dnb >= 50:
            candidates.append(("draw_no_bet", f"Draw No Bet: {home_team_name}", dnb))
        else:
            candidates.append(("draw_no_bet", f"Draw No Bet: {away_team_name}", 100 - dnb))

    return candidates


def best_market_candidate(markets, home_team_name, away_team_name):
    """The single highest-probability candidate across every market family,
    or None if the markets blob has no usable data at all."""
    candidates = extract_market_candidates(markets, home_team_name, away_team_name)
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[2])

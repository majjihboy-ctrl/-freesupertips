"""Extracts every viable betting market from a Bzzoiro `markets` JSON blob.

Shared by:
- import_bzzoiro: picks the single HIGHEST-probability candidate per match
  as that match's primary Prediction.
- views._build_accumulator: picks up to 5 candidates across different
  matches/market types at or above a threshold.
- Match detail template: full probability board via board_rows().

Market probabilities from Bzzoiro are 0–100.
"""

PICK_LABELS = {"H": "Home Win", "D": "Draw", "A": "Away Win"}


def _f(v):
    """Coerce to float or None."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract_market_candidates(markets, home_team_name, away_team_name):
    """Return a list of (market_type, label, probability) for the best
    selection in each market family. Used for primary tip + accumulator.

    Includes Over and Under goal lines, both BTTS sides (picks the stronger),
    corners Over lines, DNB both sides (picks the stronger), and 1X2.
    """
    markets = markets or {}
    candidates = []

    # --- 1X2 ---
    mr = markets.get("match_result") or {}
    probs = {
        "H": _f(mr.get("prob_home")),
        "D": _f(mr.get("prob_draw")),
        "A": _f(mr.get("prob_away")),
    }
    probs = {k: v for k, v in probs.items() if v is not None}
    if probs:
        side, prob = max(probs.items(), key=lambda kv: kv[1])
        candidates.append(("match_result", PICK_LABELS[side], prob))

    # --- BTTS ---
    btts_yes = _f((markets.get("btts") or {}).get("prob_yes"))
    if btts_yes is not None:
        if btts_yes >= 50:
            candidates.append(("btts", "BTTS: Yes", btts_yes))
        else:
            candidates.append(("btts", "BTTS: No", 100.0 - btts_yes))

    # --- Over / Under goals (best line across Over and Under) ---
    ou = markets.get("over_under") or {}
    best_ou = None
    for key, label in (
        ("prob_over_15", "Over 1.5 Goals"),
        ("prob_over_25", "Over 2.5 Goals"),
        ("prob_over_35", "Over 3.5 Goals"),
        ("prob_under_15", "Under 1.5 Goals"),
        ("prob_under_25", "Under 2.5 Goals"),
        ("prob_under_35", "Under 3.5 Goals"),
    ):
        prob = _f(ou.get(key))
        # Derive under from over when API only sends over keys
        if prob is None and key.startswith("prob_under_"):
            over_key = key.replace("under", "over")
            over_prob = _f(ou.get(over_key))
            if over_prob is not None:
                prob = 100.0 - over_prob
        if prob is not None and (best_ou is None or prob > best_ou[2]):
            best_ou = ("over_under", label, prob)
    if best_ou:
        candidates.append(best_ou)

    # --- Corners ---
    corners = markets.get("corners") or {}
    best_corners = None
    for key, line in (
        ("prob_over_85", "8.5"),
        ("prob_over_95", "9.5"),
        ("prob_over_105", "10.5"),
    ):
        prob = _f(corners.get(key))
        if prob is not None and (best_corners is None or prob > best_corners[2]):
            best_corners = ("corners", f"Corners Over {line}", prob)
    if best_corners:
        candidates.append(best_corners)

    # --- Draw No Bet ---
    dnb_home = _f((markets.get("draw_no_bet") or {}).get("prob_home"))
    if dnb_home is not None:
        if dnb_home >= 50:
            candidates.append(("draw_no_bet", f"Draw No Bet: {home_team_name}", dnb_home))
        else:
            candidates.append(("draw_no_bet", f"Draw No Bet: {away_team_name}", 100.0 - dnb_home))

    return candidates


def best_market_candidate(markets, home_team_name, away_team_name):
    """Single highest-probability candidate across every market family."""
    candidates = extract_market_candidates(markets, home_team_name, away_team_name)
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[2])


def board_rows(markets, home_name="Home", away_name="Away"):
    """Structured rows for the Match Detail probability board.

    Returns a list of dicts:
      { "group": str, "rows": [ {"label", "pct", "bar"} ... ] }
    so the template can render grouped bars without logic.
    """
    markets = markets or {}
    groups = []

    # 1X2
    mr = markets.get("match_result") or {}
    home = _f(mr.get("prob_home"))
    draw = _f(mr.get("prob_draw"))
    away = _f(mr.get("prob_away"))
    if any(v is not None for v in (home, draw, away)):
        rows = []
        if home is not None:
            rows.append({"label": f"{home_name} Win", "pct": round(home), "bar": home})
        if draw is not None:
            rows.append({"label": "Draw", "pct": round(draw), "bar": draw})
        if away is not None:
            rows.append({"label": f"{away_name} Win", "pct": round(away), "bar": away})
        groups.append({"group": "Match Result", "rows": rows})

    # BTTS
    btts_yes = _f((markets.get("btts") or {}).get("prob_yes"))
    if btts_yes is not None:
        groups.append({
            "group": "Both Teams To Score",
            "rows": [
                {"label": "Yes", "pct": round(btts_yes), "bar": btts_yes},
                {"label": "No", "pct": round(100.0 - btts_yes), "bar": 100.0 - btts_yes},
            ],
        })

    # Over/Under
    ou = markets.get("over_under") or {}
    ou_rows = []
    for over_key, under_key, line in (
        ("prob_over_15", "prob_under_15", "1.5"),
        ("prob_over_25", "prob_under_25", "2.5"),
        ("prob_over_35", "prob_under_35", "3.5"),
    ):
        over = _f(ou.get(over_key))
        under = _f(ou.get(under_key))
        if under is None and over is not None:
            under = 100.0 - over
        if over is not None:
            ou_rows.append({"label": f"Over {line}", "pct": round(over), "bar": over})
        if under is not None:
            ou_rows.append({"label": f"Under {line}", "pct": round(under), "bar": under})
    if ou_rows:
        groups.append({"group": "Goals Over / Under", "rows": ou_rows})

    # Corners
    corners = markets.get("corners") or {}
    c_rows = []
    for key, line in (
        ("prob_over_85", "8.5"),
        ("prob_over_95", "9.5"),
        ("prob_over_105", "10.5"),
    ):
        p = _f(corners.get(key))
        if p is not None:
            c_rows.append({"label": f"Over {line}", "pct": round(p), "bar": p})
    if c_rows:
        groups.append({"group": "Corners", "rows": c_rows})

    # Draw No Bet
    dnb_home = _f((markets.get("draw_no_bet") or {}).get("prob_home"))
    if dnb_home is not None:
        groups.append({
            "group": "Draw No Bet",
            "rows": [
                {"label": home_name, "pct": round(dnb_home), "bar": dnb_home},
                {"label": away_name, "pct": round(100.0 - dnb_home), "bar": 100.0 - dnb_home},
            ],
        })

    # xG + correct score as a summary group
    xg = markets.get("expected_goals") or {}
    xg_home = _f(xg.get("home"))
    xg_away = _f(xg.get("away"))
    score = (markets.get("score") or {}).get("most_likely")
    summary_rows = []
    if xg_home is not None and xg_away is not None:
        summary_rows.append({
            "label": "Expected Goals (xG)",
            "pct": None,
            "bar": None,
            "text": f"{xg_home:.2f} – {xg_away:.2f}",
        })
    if score:
        summary_rows.append({
            "label": "Most Likely Score",
            "pct": None,
            "bar": None,
            "text": str(score),
        })
    if summary_rows:
        groups.append({"group": "Model Extras", "rows": summary_rows})

    return groups


# ---- Model vs market / value helpers ----

def model_implied_odds(probability):
    """probability is 0-100. Returns decimal odds or None."""
    p = _f(probability)
    if p is None or p <= 0:
        return None
    return round(100.0 / p, 2)


def is_value_pick(confidence, min_conf=70):
    """Simple value flag until book odds are compared."""
    c = _f(confidence)
    return c is not None and c >= min_conf


def map_pick_to_odds_query(market_type, prediction_label, home_name, away_name):
    """Map our tip to Bzzoiro /odds/ market + outcome params.
    Returns (market, outcome) or (None, None).
    """
    label = (prediction_label or "").lower()
    mt = (market_type or "").lower()

    if mt == "match_result" or label in ("home win", "away win", "draw"):
        if "home" in label:
            return "1x2", "HOME"
        if "away" in label:
            return "1x2", "AWAY"
        if "draw" in label:
            return "1x2", "DRAW"
        return "1x2", None

    if mt == "btts" or "btts" in label:
        if "no" in label:
            return "btts", "no"
        return "btts", "yes"

    if mt == "over_under" or "goals" in label:
        if "1.5" in label:
            return "over_under_15", "over" if "over" in label else "under"
        if "3.5" in label:
            return "over_under_35", "over" if "over" in label else "under"
        return "over_under_25", "over" if "over" in label else "under"

    if mt == "draw_no_bet" or "draw no bet" in label:
        # outcome is home/away relative — API uses HOME/AWAY for DNB
        if home_name and home_name.lower() in label:
            return "draw_no_bet", "HOME"
        if away_name and away_name.lower() in label:
            return "draw_no_bet", "AWAY"
        return "draw_no_bet", "HOME"

    if mt == "corners" or "corners" in label:
        return "total_corners", "over"

    return None, None

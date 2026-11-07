"""Builds several distinct multibets (accumulators) from a pool of legs.

Rules enforced here:
  * every multibet has MIN_LEGS..MAX_LEGS selections (default 2..5)
  * combined odds of every multibet fall inside MIN_ODDS..MAX_ODDS (4.0..5.0)
  * a match is used at most ONCE in the whole set -- never twice in one
    multibet and never repeated across different multibets
  * multibets are built strongest-first: each one maximises combined model
    probability among the combinations that satisfy the odds window

Pure Python, no Django imports. `options` is a list of dicts:
    {"match_id", "market_type", "label", "probability"}  # prob 0-100
    optional: "odds" (a real market price), "odds_source", "kickoff"
Every returned leg gets "odds" (the supplied market price, else implied by the
model: 100 / probability) and "odds_source" ("market" or "model").
"""

MIN_ODDS = 4.0
MAX_ODDS = 5.0
MIN_LEGS = 2
MAX_LEGS = 5
COUNT = 10

# Candidate pool per multibet, stratified by odds so the search always has
# both short-priced "glue" legs and longer-priced legs to reach the window.
# (upper odds bound of bucket, how many options to keep from that bucket)
_BUCKETS = ((1.25, 6), (1.5, 9), (float("inf"), 9))


def _with_odds(options):
    out = []
    for o in options:
        p = float(o["probability"])
        if p <= 0:
            continue
        row = dict(o)
        row["probability"] = p
        supplied = o.get("odds")
        if supplied and float(supplied) > 1.0:
            row["odds"] = float(supplied)           # real market price
            row["odds_source"] = o.get("odds_source", "market")
        else:
            row["odds"] = 100.0 / p                 # model-implied price
            row["odds_source"] = "model"
        out.append(row)
    return out


def _pool(available):
    buckets = [[] for _ in _BUCKETS]
    for o in sorted(available, key=lambda r: (-r["probability"], r["match_id"], r["label"])):
        for i, (upper, _quota) in enumerate(_BUCKETS):
            if o["odds"] < upper:
                buckets[i].append(o)
                break
    pool = []
    for bucket, (_upper, quota) in zip(buckets, _BUCKETS):
        pool.extend(bucket[:quota])
    pool.sort(key=lambda r: (-r["probability"], r["match_id"], r["label"]))
    return pool


def _best_combo(pool, min_odds, max_odds, min_legs, max_legs, prefer_short=False):
    """Best combination with odds in [min_odds, max_odds]. Normally the one
    with the highest joint probability; with prefer_short, the one using the
    FEWEST selections first (probability breaks ties), which conserves
    matches so more distinct multibets can be built from a small slate."""
    best = [None, None]  # [score, legs]
    n = len(pool)

    def dfs(start, combo, used, odds, prob):
        if len(combo) >= min_legs and min_odds <= odds <= max_odds:
            score = (-len(combo), prob) if prefer_short else (prob,)
            if best[0] is None or score > best[0]:
                best[0], best[1] = score, list(combo)
        if len(combo) == max_legs:
            return
        for i in range(start, n):
            opt = pool[i]
            if opt["match_id"] in used:
                continue
            new_odds = odds * opt["odds"]
            if new_odds > max_odds:
                continue
            used.add(opt["match_id"])
            combo.append(opt)
            dfs(i + 1, combo, used, new_odds, prob * opt["probability"] / 100.0)
            combo.pop()
            used.discard(opt["match_id"])

    dfs(0, [], set(), 1.0, 1.0)
    return best[1]


def _assemble(options, count, min_odds, max_odds, min_legs, max_legs, prefer_short):
    remaining = _with_odds(options)
    used_matches = set()
    multibets = []
    span = max_odds - min_odds

    while len(multibets) < count:
        available = [o for o in remaining if o["match_id"] not in used_matches]
        if not available:
            break
        pool = _pool(available)
        # Spread the multibets across the odds window (4.0, 4.2, 4.4 ...)
        # instead of every one sitting on the lower edge; fall back to the
        # full window if nothing fits the tighter target.
        target = min_odds + span * ((len(multibets) % 5) / 5.0)
        combo = (_best_combo(pool, target, max_odds, min_legs, max_legs, prefer_short)
                 or _best_combo(pool, min_odds, max_odds, min_legs, max_legs, prefer_short))
        if not combo:
            break
        combined_odds = 1.0
        combined_prob = 1.0
        for leg in combo:
            used_matches.add(leg["match_id"])
            combined_odds *= leg["odds"]
            combined_prob *= leg["probability"] / 100.0
            leg["odds"] = round(leg["odds"], 2)
        combo.sort(key=lambda leg: (leg.get("kickoff") is None, leg.get("kickoff") or 0, leg["match_id"]))
        multibets.append({
            "number": len(multibets) + 1,
            "legs": combo,
            "combined_odds": round(combined_odds, 2),
            "combined_probability": round(combined_prob * 100),
        })
    return multibets


def assemble_multibets(options, count=COUNT, min_odds=MIN_ODDS, max_odds=MAX_ODDS,
                       min_legs=MIN_LEGS, max_legs=MAX_LEGS):
    """Return up to `count` multibets as a list of dicts:
        {"number", "legs", "combined_odds", "combined_probability"}
    Tries the strongest-first strategy, and if that can't reach `count`
    retries preferring shorter multibets (fewer matches each); the run that
    yields more multibets wins. Fewer than `count` come back only when the
    slate genuinely lacks enough distinct matches."""
    best = _assemble(options, count, min_odds, max_odds, min_legs, max_legs, False)
    if len(best) < count:
        short = _assemble(options, count, min_odds, max_odds, min_legs, max_legs, True)
        if len(short) > len(best):
            best = short
    return best

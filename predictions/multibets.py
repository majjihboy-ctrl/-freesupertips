"""Builds distinct multibets (accumulators) from a pool of legs.

Rules enforced here:
  * no leg is priced above LEG_MAX_ODDS (1.4): short-priced legs only, so a
    market is never forced onto a risky long-priced selection just to reach
    the window
  * a multibet has between 1 and MAX_LEGS (20) selections; the combined odds
    must fall inside MIN_ODDS..MAX_ODDS (4.0..5.0)
  * nothing is forced: COUNT is only an upper bound. If the safe legs of a
    market can't make a multibet, it gets none (an empty tab is fine) -- there
    is no spreading across the odds window and no "fewest legs" retry to
    squeeze out more multibets
  * a match is used at most ONCE in the whole set -- never twice in one
    multibet and never repeated across different multibets
  * multibets are built strongest-first: each one maximises combined model
    probability among the combinations that satisfy the rules

Pure Python, no Django imports. `options` is a list of dicts:
    {"match_id", "market_type", "label", "probability"}  # prob 0-100
    optional: "odds" (a real market price), "odds_source", "kickoff"
Every returned leg gets "odds" (the supplied market price, else implied by the
model: 100 / probability) and "odds_source" ("market" or "model").
"""
import math

MIN_ODDS = 4.0
MAX_ODDS = 5.0
MIN_LEGS = 1             # no minimum number of selections (a multibet just can't be empty)
MAX_LEGS = 20            # a multibet can use up to 20 selections
LEG_MAX_ODDS = 1.4       # the largest price allowed for any single selection
COUNT = 10              # an upper bound, never a target
_NODE_BUDGET = 150_000  # safety valve on the exhaustive search

# Candidate pool per multibet, stratified by odds so the search always has
# both short-priced "glue" legs and longer-priced legs to reach the window.
# (upper odds bound of bucket, how many options to keep from that bucket)
# Short-priced buckets are generous so a low-odds market can stack enough
# safe legs to reach the window without needing a long-priced one.
_BUCKETS = ((1.25, 16), (1.5, 14), (float("inf"), 9))


def _with_odds(options, max_leg_odds=None):
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
        if max_leg_odds is not None and row["odds"] > max_leg_odds:
            continue                                # too risky for a single leg
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
    nodes = [0]

    def dfs(start, combo, used, odds, prob):
        nodes[0] += 1
        if nodes[0] > _NODE_BUDGET:
            return
        if len(combo) >= min_legs and min_odds <= odds <= max_odds:
            score = (-len(combo), prob) if prefer_short else (prob,)
            if best[0] is None or score > best[0]:
                best[0], best[1] = score, list(combo)
        if max_legs is not None and len(combo) == max_legs:
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


def _greedy_combo(available, min_odds, max_odds, min_legs, max_legs=None):
    """Uncapped fallback. Take the strongest (shortest-priced) legs one match
    at a time and, after each, look for ONE closing leg that lands the product
    inside the window; the first prefix that can be closed wins, so the
    multibet is as compact as the strongest-first order allows."""
    ordered = sorted(available, key=lambda r: (-r["probability"], r["match_id"], r["label"]))
    prefix, used, product = [], set(), 1.0
    for opt in ordered:
        if opt["match_id"] in used:
            continue
        # can the current prefix already be closed (or is it itself in range)?
        if len(prefix) >= min_legs and min_odds <= product <= max_odds:
            return list(prefix)
        closers = [
            o for o in ordered
            if o["match_id"] not in used and min_odds <= product * o["odds"] <= max_odds
        ]
        if closers and len(prefix) + 1 >= min_legs and (max_legs is None or len(prefix) + 1 <= max_legs):
            # the strongest closer = lowest odds that still reaches the window
            return list(prefix) + [closers[0]]
        if max_legs is not None and len(prefix) + 1 >= max_legs:
            return None
        prefix.append(opt)
        used.add(opt["match_id"])
        product *= opt["odds"]
        if product > max_odds:
            return None
    if len(prefix) >= min_legs and min_odds <= product <= max_odds:
        return list(prefix)
    return None


def _find_combo(available, min_odds, max_odds, min_legs, max_legs):
    """Best-probability combination over the pool within [min_odds, max_odds]
    and min_legs..max_legs selections, then the greedy fallback over every
    available option. None when the legs can't make a multibet."""
    pool = _pool(available)
    combo = _best_combo(pool, min_odds, max_odds, min_legs, max_legs)
    if combo:
        return combo
    return _greedy_combo(available, min_odds, max_odds, min_legs, max_legs)


def _assemble(options, count, min_odds, max_odds, min_legs, max_legs, max_leg_odds):
    remaining = _with_odds(options, max_leg_odds)
    used_matches = set()
    multibets = []

    while len(multibets) < count:
        available = [o for o in remaining if o["match_id"] not in used_matches]
        if not available:
            break
        combo = _find_combo(available, min_odds, max_odds, min_legs, max_legs)
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
            "combined_probability": round(combined_prob * 100, 1),
        })
    return multibets


def assemble_multibets(options, count=COUNT, min_odds=MIN_ODDS, max_odds=MAX_ODDS,
                       min_legs=MIN_LEGS, max_legs=MAX_LEGS, max_leg_odds=LEG_MAX_ODDS):
    """Return up to `count` multibets as a list of dicts:
        {"number", "legs", "combined_odds", "combined_probability"}
    Only legs priced at or below `max_leg_odds` are used, each multibet has
    min_legs..max_legs selections, and fewer than `count` (even none) come
    back when the safe legs can't make more -- nothing is forced."""
    return _assemble(options, count, min_odds, max_odds, min_legs, max_legs, max_leg_odds)


# Targeted "mega" multibets: a long accumulator aimed at a specific price
# (e.g. ~222 on a 12-leg 1X2 slip) instead of the 4-5 window.
# --------------------------------------------------------------------------

def _targeted_combo(available, min_odds, max_odds, target_odds, legs, min_legs, max_legs=None):
    """Aim for `legs` selections of roughly equal price (target ** 1/legs each):
    take the options closest to that ideal price first, skip any that would
    overshoot the window, and close with the one leg whose price lands the
    product nearest the target."""
    ideal = target_odds ** (1.0 / legs)
    ordered = sorted(
        available,
        key=lambda o: (abs(math.log(o["odds"] / ideal)), -o["probability"], o["match_id"], o["label"]),
    )
    prefix, used, product = [], set(), 1.0
    for opt in ordered:
        if opt["match_id"] in used:
            continue
        if len(prefix) >= min_legs and min_odds <= product <= max_odds:
            return list(prefix)
        closers = [
            o for o in available
            if o["match_id"] not in used and min_odds <= product * o["odds"] <= max_odds
        ]
        if closers and len(prefix) + 1 >= min_legs and (max_legs is None or len(prefix) + 1 <= max_legs):
            need = target_odds / product
            best = min(closers, key=lambda o: (abs(math.log(o["odds"] / need)), -o["probability"]))
            return list(prefix) + [best]
        if product * opt["odds"] > max_odds:
            continue
        if max_legs is not None and len(prefix) + 1 >= max_legs:
            continue
        prefix.append(opt)
        used.add(opt["match_id"])
        product *= opt["odds"]
    if len(prefix) >= min_legs and min_odds <= product <= max_odds:
        return list(prefix)
    return None


def assemble_targeted(options, count, min_odds, max_odds, target_odds, target_legs=18, min_legs=1,
                      max_legs=MAX_LEGS, max_leg_odds=LEG_MAX_ODDS):
    """Up to `count` distinct multibets whose combined odds fall in
    [min_odds, max_odds], built around `target_legs` selections each (the
    number of legs flexes when the slate can't give that many). No match is
    used twice across the set. Same output shape as assemble_multibets."""
    remaining = _with_odds(options, max_leg_odds)
    used_matches = set()
    multibets = []
    tries = [target_legs]
    for d in range(1, 10):
        tries += [target_legs + d, target_legs - d]
    tries = [n for n in tries if n >= max(min_legs, 1) and (max_legs is None or n <= max_legs)]

    while len(multibets) < count:
        available = [o for o in remaining if o["match_id"] not in used_matches]
        combo = None
        for legs in tries:
            combo = _targeted_combo(available, min_odds, max_odds, target_odds, legs, min_legs, max_legs)
            if combo:
                break
        if not combo:
            break
        combined_odds, combined_prob = 1.0, 1.0
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
            "combined_probability": round(combined_prob * 100, 2),
        })
    return multibets

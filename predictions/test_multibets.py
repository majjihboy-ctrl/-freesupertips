"""Tests for predictions.multibets (pure Python, no database needed)."""
import random
import unittest

from .multibets import (
    assemble_multibets, assemble_targeted, COUNT, LEG_MAX_ODDS, MAX_LEGS, MAX_ODDS, MIN_LEGS, MIN_ODDS,
)


def _pool(seed, matches):
    rng = random.Random(seed)
    options = []
    for match_id in range(matches):
        for market in rng.sample(["1x2", "btts", "ou", "corners", "dnb"], rng.randint(1, 4)):
            options.append({
                "match_id": match_id,
                "prediction": None,
                "market_type": market,
                "label": f"{market}-{match_id}",
                "probability": rng.uniform(55, 92),
            })
    return options


class MultibetRulesTests(unittest.TestCase):
    def test_rules_hold_for_many_slates(self):
        for seed in range(12):
            for matches in (20, 40, 60):
                result = assemble_multibets(_pool(seed, matches))
                self.assertLessEqual(len(result), COUNT)
                seen = set()
                for mb in result:
                    ids = [leg["match_id"] for leg in mb["legs"]]
                    self.assertEqual(len(ids), len(set(ids)), "match repeated inside a multibet")
                    picks = {(leg["match_id"], leg["market_type"], leg["label"]) for leg in mb["legs"]}
                    self.assertFalse(seen & picks, "same pick used in two multibets")
                    seen |= picks
                    self.assertTrue(MIN_LEGS <= len(ids) <= MAX_LEGS)
                    self.assertTrue(all(leg["odds"] <= LEG_MAX_ODDS for leg in mb["legs"]))
                    self.assertTrue(MIN_ODDS <= mb["combined_odds"] <= MAX_ODDS)

    def test_builds_up_to_ten_from_a_big_safe_slate(self):
        rng = random.Random(21)
        options = [{"match_id": i, "market_type": "1x2", "label": f"x{i}",
                    "probability": rng.uniform(78, 90)} for i in range(160)]
        self.assertEqual(len(assemble_multibets(options)), COUNT)

    def test_count_is_never_forced(self):
        # only long-priced legs (55-65% -> odds 1.5-1.8): nothing is safe enough,
        # so there are no multibets rather than forced risky ones
        rng = random.Random(22)
        options = [{"match_id": i, "market_type": "ou", "label": f"o{i}",
                    "probability": rng.uniform(55, 65)} for i in range(80)]
        self.assertEqual(assemble_multibets(options), [])
        # a thin safe slate gives fewer than ten, however many matches exist
        thin = [{"match_id": i, "market_type": "dc", "label": f"d{i}", "probability": 85.0}
                for i in range(30)]
        result = assemble_multibets(thin)
        self.assertTrue(0 < len(result) < COUNT)

    def test_no_leg_is_priced_above_the_ceiling(self):
        mixed = [{"match_id": i, "market_type": "dc", "label": f"d{i}", "probability": 80.0, "odds": 1.25}
                 for i in range(40)]
        mixed += [{"match_id": 100 + i, "market_type": "dc", "label": f"e{i}", "probability": 80.0, "odds": 1.9}
                  for i in range(10)]
        for mb in assemble_multibets(mixed):
            self.assertTrue(all(leg["odds"] <= 1.4 for leg in mb["legs"]))
            self.assertTrue(all(leg["match_id"] < 100 for leg in mb["legs"]))

    def test_a_multibet_never_exceeds_twenty_selections(self):
        # 1.05-priced legs would need ~29 selections to reach 4.0, so no multibet
        options = [{"match_id": i, "market_type": "dc", "label": f"d{i}", "probability": 95.0}
                   for i in range(200)]
        self.assertEqual(assemble_multibets(options), [])
        near = [{"match_id": i, "market_type": "dc", "label": f"d{i}", "probability": 93.0}
                for i in range(200)]   # 1.075 each -> 20 legs = 4.2
        for mb in assemble_multibets(near):
            self.assertLessEqual(len(mb["legs"]), 20)

    def test_multibets_are_distinct(self):
        result = assemble_multibets(_pool(3, 60))
        keys = [tuple(sorted(leg["match_id"] for leg in mb["legs"])) for mb in result]
        self.assertEqual(len(keys), len(set(keys)))

    def test_a_match_can_be_reused_with_a_different_pick(self):
        # every match has two safe picks (1X2 favourite and Double Chance);
        # a match may appear in several multibets, but with a different pick
        # each time and never twice in the same multibet
        rng = random.Random(31)
        options = []
        for m in range(14):
            options.append({"match_id": m, "market_type": "match_result", "label": f"Home {m}",
                            "probability": rng.uniform(76, 82)})
            options.append({"match_id": m, "market_type": "double_chance", "label": f"1X {m}",
                            "probability": rng.uniform(88, 94)})
        result = assemble_multibets(options)
        appearances, picks_seen = {}, set()
        for mb in result:
            ids = [leg["match_id"] for leg in mb["legs"]]
            self.assertEqual(len(ids), len(set(ids)), "match twice in one multibet")
            for leg in mb["legs"]:
                pick = (leg["match_id"], leg["market_type"], leg["label"])
                self.assertNotIn(pick, picks_seen, "same pick used twice")
                picks_seen.add(pick)
                appearances[leg["match_id"]] = appearances.get(leg["match_id"], 0) + 1
        self.assertTrue(any(n > 1 for n in appearances.values()), appearances)

    def test_selection_and_price_limits(self):
        self.assertEqual(MAX_LEGS, 20)
        self.assertEqual(MIN_LEGS, 1)
        self.assertEqual(LEG_MAX_ODDS, 1.4)

    def test_short_priced_legs_still_reach_the_odds_window(self):
        # every leg ~1.11 odds (90%): 5 legs can only reach ~1.7, so the
        # window is only reachable by adding more selections -- previously
        # impossible under the 5-leg cap.
        rng = random.Random(4)
        options = [{"match_id": i, "market_type": "draw_no_bet", "label": f"dnb-{i}",
                    "probability": rng.uniform(86, 93)} for i in range(120)]
        result = assemble_multibets(options)
        self.assertGreaterEqual(len(result), 5)
        seen = set()
        for mb in result:
            ids = [leg["match_id"] for leg in mb["legs"]]
            self.assertGreater(len(ids), 5)
            self.assertEqual(len(ids), len(set(ids)))
            picks = {(leg["match_id"], leg["market_type"], leg["label"]) for leg in mb["legs"]}
            self.assertFalse(seen & picks, "same pick used in two multibets")
            seen |= picks
            self.assertTrue(MIN_ODDS <= mb["combined_odds"] <= MAX_ODDS)

    def test_short_priced_tab_is_not_forced_into_risky_long_priced_legs(self):
        # Double Chance style slate: plenty of safe ~1.2 legs plus a few
        # long-priced, poor-value ones. With a "max legs per fold" cap the
        # builder had to reach 4-5 combined odds with one of the long-priced
        # legs; with no cap it simply stacks the safe ones.
        rng = random.Random(11)
        options = []
        for i in range(60):
            prob = rng.uniform(80, 86)
            options.append({"match_id": i, "market_type": "double_chance", "label": f"dc-{i}",
                            "probability": prob, "odds": round(100 / prob, 2)})
        for i in range(60, 75):
            options.append({"match_id": i, "market_type": "double_chance", "label": f"dc-{i}",
                            "probability": 40.0, "odds": 2.2})
        result = assemble_multibets(options, count=4)
        self.assertEqual(len(result), 4)
        for mb in result:
            self.assertTrue(MIN_ODDS <= mb["combined_odds"] <= MAX_ODDS)
            self.assertTrue(all(leg["odds"] <= 1.3 for leg in mb["legs"]), mb)
        self.assertTrue(any(len(mb["legs"]) > 5 for mb in result))

    def test_explicit_cap_is_still_respected_when_asked_for(self):
        options = [{"match_id": i, "market_type": "dnb", "label": f"x{i}", "probability": 90.0}
                   for i in range(80)]
        self.assertEqual(assemble_multibets(options, max_legs=4), [])
        capped = assemble_multibets(_pool(2, 60), max_legs=4)
        self.assertTrue(all(len(mb["legs"]) <= 4 for mb in capped))

    def test_large_pools_stay_fast(self):
        import time
        options = _pool(9, 200) + [dict(o, match_id=o["match_id"] + 1000) for o in _pool(10, 200)]
        t = time.time()
        assemble_multibets(options)
        self.assertLess(time.time() - t, 8)

    def test_empty_and_tiny_pools_do_not_crash(self):
        self.assertEqual(assemble_multibets([]), [])
        self.assertEqual(assemble_multibets(_pool(0, 1)), [])


if __name__ == "__main__":
    unittest.main()


class TargetedMegaTests(unittest.TestCase):
    def _slate(self, seed, matches=60):
        rng = random.Random(seed)
        options = []
        for m in range(matches):
            for label, p in (("Home Win", rng.uniform(25, 80)), ("Away Win", rng.uniform(10, 45))):
                if p >= 50:
                    options.append({"match_id": m, "market_type": "match_result", "label": label, "probability": p})
        return options

    def test_builds_long_multibets_near_the_target_price(self):
        for seed in range(8):
            result = assemble_targeted(self._slate(seed), 3, 200, 250, 222.64, 12, max_leg_odds=None)
            self.assertGreaterEqual(len(result), 2, f"seed {seed}")
            seen = set()
            for mb in result:
                ids = [leg["match_id"] for leg in mb["legs"]]
                self.assertEqual(len(ids), len(set(ids)))
                picks = {(leg["match_id"], leg["market_type"], leg["label"]) for leg in mb["legs"]}
                self.assertFalse(seen & picks, "same pick used in two multibets")
                seen |= picks
                self.assertTrue(200 <= mb["combined_odds"] <= 250)
                self.assertTrue(8 <= len(ids) <= 18, len(ids))
                self.assertTrue(all(leg["label"] != "Draw" for leg in mb["legs"]))

    def test_first_multibet_aims_for_about_twelve_legs(self):
        sizes = [len(assemble_targeted(self._slate(s), 3, 200, 250, 222.64, 12, max_leg_odds=None)[0]["legs"]) for s in range(8)]
        self.assertTrue(all(10 <= n <= 14 for n in sizes), sizes)

    def test_capped_mega_uses_only_short_legs_and_at_most_twenty(self):
        rng = random.Random(5)
        options = [{"match_id": m, "market_type": "match_result", "label": "Home Win",
                    "probability": rng.uniform(72, 76)} for m in range(60)]
        result = assemble_targeted(options, 3, 200, 250, 222.64)
        self.assertTrue(result)
        for mb in result:
            self.assertTrue(200 <= mb["combined_odds"] <= 250)
            self.assertTrue(len(mb["legs"]) <= 20)
            self.assertTrue(all(leg["odds"] <= 1.4 for leg in mb["legs"]))

    def test_mega_can_use_up_to_thirty_selections_across_markets(self):
        rng = random.Random(8)
        markets = ("match_result", "btts", "over_under", "corners", "draw_no_bet", "double_chance")
        options = [{"match_id": m, "market_type": markets[m % len(markets)], "label": f"sel{m}",
                    "probability": rng.uniform(80, 88)} for m in range(120)]
        result = assemble_targeted(options, 3, 200, 250, 222.64, 24, max_legs=30)
        self.assertTrue(result)
        sizes = [len(mb["legs"]) for mb in result]
        self.assertTrue(max(sizes) <= 30, sizes)
        self.assertTrue(max(sizes) > 20, sizes)       # genuinely uses more than the normal 20
        for mb in result:
            self.assertTrue(200 <= mb["combined_odds"] <= 250)
            self.assertTrue(all(leg["odds"] <= 1.4 for leg in mb["legs"]))
            self.assertGreater(len({leg["market_type"] for leg in mb["legs"]}), 1)  # combines markets

    def test_mega_is_empty_when_there_are_no_safe_legs(self):
        rng = random.Random(6)
        options = [{"match_id": m, "market_type": "match_result", "label": "Home Win",
                    "probability": rng.uniform(50, 60)} for m in range(60)]
        self.assertEqual(assemble_targeted(options, 3, 200, 250, 222.64), [])

    def test_small_or_empty_slates_do_not_crash(self):
        self.assertEqual(assemble_targeted([], 3, 200, 250, 222.64), [])
        self.assertEqual(assemble_targeted(self._slate(1, matches=4), 3, 200, 250, 222.64), [])

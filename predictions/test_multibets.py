"""Tests for predictions.multibets (pure Python, no database needed)."""
import random
import unittest

from .multibets import (
    assemble_multibets, assemble_targeted, COUNT, MAX_LEGS, MAX_ODDS, MIN_LEGS, MIN_ODDS, PREFERRED_LEGS,
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
                    self.assertFalse(seen & set(ids), "match repeated across multibets")
                    seen |= set(ids)
                    self.assertGreaterEqual(len(ids), MIN_LEGS)
                    self.assertTrue(MIN_ODDS <= mb["combined_odds"] <= MAX_ODDS)

    def test_builds_ten_from_a_full_slate(self):
        self.assertEqual(len(assemble_multibets(_pool(1, 60))), COUNT)

    def test_multibets_are_distinct(self):
        result = assemble_multibets(_pool(3, 60))
        keys = [tuple(sorted(leg["match_id"] for leg in mb["legs"])) for mb in result]
        self.assertEqual(len(keys), len(set(keys)))

    def test_no_cap_on_selections_by_default(self):
        self.assertIsNone(MAX_LEGS)

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
            self.assertGreater(len(ids), PREFERRED_LEGS)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertFalse(seen & set(ids))
            seen |= set(ids)
            self.assertTrue(MIN_ODDS <= mb["combined_odds"] <= MAX_ODDS)

    def test_compact_multibets_are_preferred_when_possible(self):
        result = assemble_multibets(_pool(1, 60))
        self.assertEqual(len(result), COUNT)
        self.assertTrue(all(len(mb["legs"]) <= PREFERRED_LEGS for mb in result))

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
            result = assemble_targeted(self._slate(seed), 3, 200, 250, 222.64, 12)
            self.assertGreaterEqual(len(result), 2, f"seed {seed}")
            seen = set()
            for mb in result:
                ids = [leg["match_id"] for leg in mb["legs"]]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertFalse(seen & set(ids), "match reused across mega multibets")
                seen |= set(ids)
                self.assertTrue(200 <= mb["combined_odds"] <= 250)
                self.assertTrue(8 <= len(ids) <= 18, len(ids))
                self.assertTrue(all(leg["label"] != "Draw" for leg in mb["legs"]))

    def test_first_multibet_aims_for_about_twelve_legs(self):
        sizes = [len(assemble_targeted(self._slate(s), 3, 200, 250, 222.64, 12)[0]["legs"]) for s in range(8)]
        self.assertTrue(all(10 <= n <= 14 for n in sizes), sizes)

    def test_small_or_empty_slates_do_not_crash(self):
        self.assertEqual(assemble_targeted([], 3, 200, 250, 222.64), [])
        self.assertEqual(assemble_targeted(self._slate(1, matches=4), 3, 200, 250, 222.64), [])

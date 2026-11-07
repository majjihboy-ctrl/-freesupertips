"""Tests for predictions.multibets (pure Python, no database needed)."""
import random
import unittest

from .multibets import (
    assemble_multibets, COUNT, MAX_LEGS, MAX_ODDS, MIN_LEGS, MIN_ODDS,
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
                    self.assertTrue(MIN_LEGS <= len(ids) <= MAX_LEGS)
                    self.assertTrue(MIN_ODDS <= mb["combined_odds"] <= MAX_ODDS)

    def test_builds_ten_from_a_full_slate(self):
        self.assertEqual(len(assemble_multibets(_pool(1, 60))), COUNT)

    def test_multibets_are_distinct(self):
        result = assemble_multibets(_pool(3, 60))
        keys = [tuple(sorted(leg["match_id"] for leg in mb["legs"])) for mb in result]
        self.assertEqual(len(keys), len(set(keys)))

    def test_empty_and_tiny_pools_do_not_crash(self):
        self.assertEqual(assemble_multibets([]), [])
        self.assertEqual(assemble_multibets(_pool(0, 1)), [])


if __name__ == "__main__":
    unittest.main()

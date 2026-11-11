"""Check integration with upstream BIRD reward and result semantics."""

import importlib.util
import math
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_bird_rves import load_bird, measure

ROOT = Path(__file__).resolve().parents[2]
AVAILABLE = (ROOT / "BIRD-mini-dev/evaluation/evaluation_ves.py").is_file() and all(
    importlib.util.find_spec(name)
    for name in ("numpy", "func_timeout", "psycopg2", "pymysql")
)


@unittest.skipUnless(AVAILABLE, "Clone BIRD-mini-dev and install the bird extra")
class BirdRvesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bird = load_bird(ROOT / "BIRD-mini-dev")

    def timed_queries(self, ratio, pred_rows, gold_rows):
        # Nonconstant samples avoid upstream's strict 3-sigma std=0 edge case.
        samples = iter([1, ratio * 0.9, 1, ratio * 1.1] * 2)

        def execute(sql, database, dialect, return_time=False):
            if return_time:
                return next(samples)
            return pred_rows if sql == "pred" else gold_rows

        return execute

    def test_upstream_reward_bands_and_square_root_average(self):
        for ratio, reward in [
            (0.1, 0.25),
            (0.3, 0.5),
            (0.75, 0.75),
            (1.5, 1),
            (3, 1.25),
        ]:
            with (
                self.subTest(ratio=ratio),
                patch.object(
                    self.bird, "execute_sql", self.timed_queries(ratio, [(1,)], [(1,)])
                ),
            ):
                self.assertEqual(
                    self.bird.iterated_execute_sql(
                        "pred", "gold", "unused", 4, "SQLite"
                    ),
                    reward,
                )
        self.assertAlmostEqual(
            self.bird.compute_ves([{"reward": 1.25}, {"reward": 0}]),
            math.sqrt(1.25) * 50,
        )

    def test_row_order_and_duplicate_counts_ignored(self):
        with patch.object(
            self.bird,
            "execute_sql",
            self.timed_queries(1.5, [(1,), (1,), (2,)], [(2,), (1,)]),
        ):
            self.assertEqual(
                self.bird.iterated_execute_sql("pred", "gold", "unused", 4, "SQLite"), 1
            )

    def test_column_order_and_values_must_match(self):
        for rows in [[(2, 1)], [(1, 3)]]:
            with patch.object(
                self.bird, "execute_sql", self.timed_queries(1.5, rows, [(1, 2)])
            ):
                self.assertEqual(
                    self.bird.iterated_execute_sql(
                        "pred", "gold", "unused", 4, "SQLite"
                    ),
                    0,
                )

    def test_measure_keeps_original_rewards_and_records_timings(self):
        with patch.object(
            self.bird, "execute_sql", self.timed_queries(1.5, [(1,)], [(1,)])
        ):
            result = measure(self.bird, "pred", "gold", Path("unused"), 0, 4, 1)
        self.assertEqual(result["reward"], 1)
        self.assertTrue(result["valid_set_match"])
        self.assertEqual(result["measured_pairs"], 4)
        self.assertEqual(result["status"], "reward_positive")

    def test_upstream_query_errors_get_zero_and_are_visible(self):
        with patch.object(
            self.bird, "execute_sql", side_effect=sqlite3.OperationalError("bad SQL")
        ):
            result = measure(self.bird, "pred", "gold", Path("unused"), 0, 4, 1)
        self.assertEqual(result["reward"], 0)
        self.assertEqual(result["status"], "query_error")
        self.assertIn("bad SQL", result["errors"][0])

    def test_upstream_constant_samples_filter_to_empty(self):
        self.assertEqual(self.bird.clean_abnormal([1, 1, 1, 1]), [])


if __name__ == "__main__":
    unittest.main()

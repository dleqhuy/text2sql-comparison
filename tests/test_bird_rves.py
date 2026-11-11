"""Check integration with upstream BIRD reward and result semantics."""

import importlib.util
import math
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_bird_rves import compute_original_ves, load_bird, measure
from score_bird_efficiency import recompute_timing

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

    def test_ves_takes_square_root_after_averaging_filtered_ratios(self):
        result = {
            "status": "reward_positive",
            "valid_set_match": True,
            "reward": 1,
            "predicted_times_seconds": [1, 1, 1, 1],
            "gold_times_seconds": [0.5, 1.5, 0.5, 1.5],
            "mean_filtered_time_ratio": 1,
            "measured_pairs": 4,
            "filtered_pairs": 4,
        }
        recompute_timing(self.bird, result, 4)
        self.assertEqual(compute_original_ves([result]), 100)
        result["mean_filtered_time_ratio"] = 2
        with self.assertRaisesRegex(ValueError, "Saved mean ratio"):
            recompute_timing(self.bird, result, 4)

    @unittest.skipUnless(
        (ROOT / "MAC-SQL/evaluation/evaluation_bird_ves.py").is_file(),
        "Legacy VES source unavailable",
    )
    def test_ves_matches_legacy_aggregator(self):
        spec = importlib.util.spec_from_file_location(
            "legacy_ves", ROOT / "MAC-SQL/evaluation/evaluation_bird_ves.py"
        )
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        ratios = [0.1, 0.3, 0.75, 1.5, 3, 100, 0]
        records = [
            {
                "status": "reward_positive" if r else "result_mismatch",
                "valid_set_match": bool(r),
                "mean_filtered_time_ratio": r,
            }
            for r in ratios
        ]
        self.assertEqual(
            compute_original_ves(records),
            legacy.compute_ves([{"time_ratio": r} for r in ratios]),
        )


class OriginalVesTest(unittest.TestCase):
    def test_failures_stay_in_denominator_and_have_zero_contribution(self):
        records = [
            {
                "status": "reward_positive",
                "valid_set_match": True,
                "mean_filtered_time_ratio": 4,
            }
        ]
        records += [
            {"status": status, "valid_set_match": True, "mean_filtered_time_ratio": 100}
            for status in (
                "result_mismatch",
                "query_error",
                "timeout",
                "empty_outlier_filter",
            )
        ]
        self.assertEqual(compute_original_ves(records), 40)

    def test_continuous_ves_has_no_reward_cap(self):
        self.assertEqual(
            compute_original_ves(
                [
                    {
                        "status": "reward_positive",
                        "valid_set_match": True,
                        "mean_filtered_time_ratio": 100,
                    }
                ]
            ),
            1000,
        )

    def test_invalid_successful_ratio_is_rejected(self):
        for value in (None, 0, -1, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compute_original_ves(
                    [
                        {
                            "status": "reward_positive",
                            "valid_set_match": True,
                            "mean_filtered_time_ratio": value,
                        }
                    ]
                )

    def test_empty_dataset(self):
        self.assertEqual(compute_original_ves([]), 0)


if __name__ == "__main__":
    unittest.main()

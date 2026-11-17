"""Demo metrics must preserve Spider structure and execution semantics."""

import math
import os
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("NLTK_DATA", str(ROOT / ".cache/nltk_data"))
sys.path.insert(0, str(ROOT / "scripts"))
from live_metrics import score

DATABASE = ROOT / "downloads/spider_data/database/concert_singer/concert_singer.sqlite"


@unittest.skipUnless(DATABASE.exists(), "Spider database is not installed")
class LiveMetricsTests(unittest.TestCase):
    def score(self, predicted, gold="SELECT count(*) FROM singer"):
        return score(
            {
                "database": str(DATABASE),
                "predicted": predicted,
                "gold": gold,
                "db_id": "concert_singer",
                "tables": str(ROOT / "downloads/spider_data/tables.json"),
            }
        )

    def test_case_and_format_are_not_string_comparison(self):
        result = self.score("select COUNT(*) from SINGER;")
        self.assertEqual((result["em"], result["ex"]), (1, 1))
        self.assertIsNone(result["em_error"])
        self.assertTrue(result["ves_valid_match"])
        self.assertEqual(result["iterations"], 10)
        self.assertGreater(result["ves"], 0)

    def test_cm_identical_sql_and_unused_components(self):
        result = self.score("SELECT COUNT(*) FROM singer")
        self.assertEqual(result["cm"]["select"]["f1"], 1)
        self.assertEqual(result["cm"]["select"]["pred_total"], 1)
        self.assertEqual(result["cm"]["select"]["label_total"], 1)
        self.assertEqual(result["cm"]["where"]["pred_total"], 0)
        self.assertEqual(result["cm"]["where"]["label_total"], 0)
        self.assertIsNone(result["cm_error"])

    def test_cm_localizes_a_wrong_where_clause(self):
        result = self.score(
            "SELECT name FROM singer WHERE country = 'France'",
            "SELECT name FROM singer WHERE age > 20",
        )
        self.assertEqual(result["em"], 0)
        self.assertEqual(result["cm"]["select"]["f1"], 1)
        self.assertEqual(result["cm"]["where"]["f1"], 0)
        self.assertEqual(result["cm"]["where"]["pred_total"], 1)
        self.assertEqual(result["cm"]["where"]["label_total"], 1)

    def test_cm_missing_clause_is_not_marked_unused(self):
        result = self.score(
            "SELECT name FROM singer", "SELECT name FROM singer WHERE age > 20"
        )
        self.assertEqual(result["cm"]["where"]["f1"], 0)
        self.assertEqual(result["cm"]["where"]["pred_total"], 0)
        self.assertEqual(result["cm"]["where"]["label_total"], 1)

    def test_parser_rejection_scores_em_zero_without_losing_ex(self):
        result = self.score("SELECT COUNT(*) AS singer_count FROM singer")
        self.assertEqual((result["em"], result["ex"]), (0, 1))
        self.assertIsNotNone(result["em_error"])
        self.assertIsNotNone(result["cm_error"])
        self.assertEqual(result["cm"]["select"]["f1"], 0)
        self.assertEqual(result["cm"]["select"]["pred_total"], 0)

    def test_different_structure_can_have_equal_execution(self):
        result = self.score("SELECT COUNT(Singer_ID) FROM singer")
        self.assertEqual((result["em"], result["ex"]), (0, 1))

    def test_spider_ignores_values_but_ex_does_not(self):
        result = self.score(
            "SELECT name FROM singer WHERE age > 100",
            "SELECT name FROM singer WHERE age > 0",
        )
        self.assertEqual((result["em"], result["ex"]), (1, 0))
        self.assertEqual(result["ves"], 0)
        self.assertEqual(result["iterations"], 0)

    def test_ves_set_semantics_are_distinct_from_ex_bags(self):
        result = self.score(
            "SELECT name FROM singer UNION ALL SELECT name FROM singer",
            "SELECT name FROM singer",
        )
        self.assertEqual(result["ex"], 0)
        self.assertTrue(result["ves_valid_match"])
        self.assertGreater(result["ves"], 0)

    def test_ves_uses_square_root_of_mean_filtered_ratio(self):
        ratios = [0.24, 0.25, 0.26, 0.27, 0.25, 0.24, 0.26, 0.25, 0.24, 0.25]
        timings = [value for ratio in ratios for value in (0.004, 0.004 * ratio)]
        with patch("live_metrics.timed_query", side_effect=timings):
            result = self.score("SELECT count(*) FROM singer")
        self.assertAlmostEqual(
            result["ves"], 100 * math.sqrt(sum(ratios) / len(ratios))
        )

    def test_invalid_reference_is_unavailable_instead_of_model_failure(self):
        result = self.score(
            "SELECT COUNT(*) FROM singer", "SELECT missing FROM missing_table"
        )
        self.assertIsNone(result["ex"])
        self.assertIsNone(result["ves"])
        self.assertIn("SQL tham chiếu", result["ex_error"])
        self.assertIsNone(result["cm"])
        self.assertIsNotNone(result["cm_error"])

    def test_writes_are_rejected_without_changing_database(self):
        with sqlite3.connect(DATABASE) as connection:
            before = connection.execute("SELECT count(*) FROM singer").fetchone()
        result = self.score("DELETE FROM singer")
        self.assertEqual(result["ex"], 0)
        self.assertIsNotNone(result["ex_error"])
        self.assertEqual(result["ves"], 0)
        with sqlite3.connect(DATABASE) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM singer").fetchone(), before
            )


if __name__ == "__main__":
    unittest.main()

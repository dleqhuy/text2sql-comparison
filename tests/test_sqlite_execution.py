"""Regression cases for SQLite execution scoring and result comparison."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import write_json, write_predictions
from evaluate import evaluate
from sqlite_eval import execute, order_matters, result_eq


class ResultComparisonTest(unittest.TestCase):
    def test_unordered_rows_keep_duplicate_counts(self):
        self.assertTrue(result_eq([(1,), (2,), (1,)], [(2,), (1,), (1,)]))
        self.assertFalse(result_eq([(1,), (1,), (2,)], [(1,), (2,), (2,)]))
        self.assertFalse(result_eq([(1,), (1,)], [(1,)]))

    def test_ordered_rows_and_column_permutations(self):
        gold = [(1, "a"), (2, "b")]
        self.assertTrue(result_eq(gold, [("a", 1), ("b", 2)], ordered=True))
        self.assertFalse(result_eq(gold, [("b", 2), ("a", 1)], ordered=True))
        self.assertTrue(result_eq(gold, [("b", 2), ("a", 1)]))

    def test_permutation_must_be_global_and_bijective(self):
        self.assertFalse(result_eq([(1, 2), (3, 4)], [(2, 1), (3, 4)]))
        self.assertFalse(result_eq([(1, 1), (2, 2)], [(1, 9), (2, 8)]))
        # Identical column marginals must not hide different row associations.
        self.assertFalse(
            result_eq(
                [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)],
                [(1, 1, 1), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
            )
        )

    def test_nulls_empty_and_numeric_results(self):
        self.assertTrue(result_eq([(None, 1)], [(1.0, None)]))
        self.assertTrue(result_eq([], []))
        self.assertFalse(result_eq([], [(None,)]))
        self.assertFalse(result_eq([(1,)], [(1, 2)]))
        self.assertFalse(result_eq([("1",)], [(1,)]))

    def test_only_outer_order_by_counts(self):
        for query in [
            "SELECT x FROM t ORDER /* comment */ BY x",
            "WITH q AS (SELECT x FROM t) SELECT * FROM q ORDER\nBY x",
            "SELECT x FROM t UNION SELECT x FROM u ORDER BY x",
        ]:
            self.assertTrue(order_matters(query), query)
        for query in [
            "SELECT 'order by', \"order by\", `order by`, [order by] FROM t",
            "SELECT x FROM (SELECT x FROM t ORDER BY x)",
            "SELECT ROW_NUMBER() OVER (ORDER BY x) FROM t",
            "-- order by\nSELECT x FROM t /* order by */",
        ]:
            self.assertFalse(order_matters(query), query)


class SQLiteExecutionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "demo" / "demo.sqlite"
        self.db.parent.mkdir()
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
            conn.executemany("INSERT INTO items VALUES (?, ?)", [(1, "a"), (2, "b")])

    def tearDown(self):
        self.temp.cleanup()

    def test_full_sqlite_syntax_count_equivalence_and_read_only(self):
        gold, _ = execute(self.db, "SELECT COUNT(*) FROM items", 1)
        pred, _ = execute(
            self.db, "WITH q AS (SELECT id FROM items) SELECT COUNT(id) FROM q", 1
        )
        self.assertTrue(result_eq(gold, pred))
        with self.assertRaises(sqlite3.Error):
            execute(self.db, "DELETE FROM items", 1)
        self.assertEqual(execute(self.db, "SELECT COUNT(*) FROM items", 1)[0], [(2,)])
        with self.assertRaises((sqlite3.Error, sqlite3.Warning)):
            execute(self.db, "SELECT 1; SELECT 2", 1)

    def test_timeout_interrupts_recursive_query(self):
        with self.assertRaisesRegex(sqlite3.OperationalError, "interrupted"):
            execute(
                self.db,
                "WITH RECURSIVE q(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM q) SELECT SUM(x) FROM q",
                0.01,
            )

    def test_cli_backend_preserves_empty_predictions_and_records_policy(self):
        queries = [
            "SELECT name FROM items",
            "SELECT count(*) FROM items",
            "SELECT name FROM items",
            "SELECT name FROM items",
        ]
        rows = [
            dict(example_id=f"dev_{i:04d}", db_id="demo", question=f"Q{i}", query=q)
            for i, q in enumerate(queries)
        ]
        write_json(self.root / "examples.json", rows)
        write_json(self.root / "subset.json", [r["example_id"] for r in rows])
        write_json(self.root / "tables.json", [{"db_id": "demo"}])
        pred = self.root / "pred.jsonl"
        write_predictions(
            rows,
            [
                "WITH q AS (SELECT name FROM items) SELECT * FROM q",
                "SELECT COUNT(id) FROM items",
                "SELECT i.name FROM items i LEFT JOIN items j ON i.id=j.id WHERE EXISTS (SELECT 1 FROM items k WHERE k.id=i.id)",
                "",
            ],
            pred,
        )
        args = argparse.Namespace(
            examples=self.root / "examples.json",
            subset=self.root / "subset.json",
            spider_root=Path(__file__).resolve().parents[2] / "spider",
            db=self.root,
            table=self.root / "tables.json",
            prediction=[f"fixture={pred}"],
            work_dir=self.root / "eval",
            summary=self.root / "summary.csv",
            difficulty_summary=None,
            report=None,
            python=sys.executable,
            timeout=30,
            execution_backend="sqlite",
            query_timeout=1,
        )
        evaluate(args)
        self.assertIn("fixture,0.75,4,1", args.summary.read_text())
        details = json.loads((args.work_dir / "fixture.details.json").read_text())
        self.assertEqual(details["correct"], 3)
        self.assertEqual(details["metric"], "single_database_execution_accuracy")
        self.assertEqual(
            [x["correct"] for x in details["examples"]], [True, True, True, False]
        )
        self.assertIn(
            "không phải test-suite accuracy", (self.root / "report.md").read_text()
        )
        # An invalid gold is a dataset/run failure, never another model error.
        previous_summary = args.summary.read_text()
        rows[0]["query"] = "SELECT missing_column FROM items"
        write_json(self.root / "examples.json", rows)
        with self.assertRaisesRegex(RuntimeError, "sqlite evaluator failed"):
            evaluate(args)
        self.assertEqual(args.summary.read_text(), previous_summary)

    def test_empty_results_still_require_matching_column_count(self):
        gold, gold_width = execute(self.db, "SELECT name FROM items WHERE 0", 1)
        pred, pred_width = execute(self.db, "SELECT name, id FROM items WHERE 0", 1)
        self.assertEqual(gold, pred)
        self.assertNotEqual(gold_width, pred_width)


if __name__ == "__main__":
    unittest.main()

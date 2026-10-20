import contextlib
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_data import prepare
from run_comparison import Comparison, parser


class ComparisonRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        self.rows = [
            dict(db_id="demo", question=f"Question {i}", query="SELECT name FROM items")
            for i in range(25)
        ]
        (self.source / "dev.json").write_text(json.dumps(self.rows))
        self.data = self.root / "data"
        self.output = self.root / "output"

    def args(self, *extra):
        return parser().parse_args(
            [
                "--spider-data",
                str(self.source),
                "--data-dir",
                str(self.data),
                "--output",
                str(self.output),
                *extra,
            ]
        )

    def test_dry_run_is_read_only_and_uses_requested_subset_everywhere(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            Comparison(self.args("--count", "20", "--dry-run")).run()
        plan = output.getvalue()
        self.assertIn("--count 20", plan)
        self.assertEqual(plan.count("--end_index 20"), 2)
        self.assertEqual(plan.count("scripts/evaluate.py"), 1)
        self.assertNotIn("--execution-backend", plan)
        self.assertIn(str(self.output / "dail_work/dataset/spider"), plan)
        self.assertIn(
            "--pre_test_result " + str(self.output / "raw/dail_preliminary.txt"), plan
        )
        self.assertFalse(self.data.exists())
        self.assertFalse(self.output.exists())

    def test_default_is_all_examples_and_invalid_counts_fail(self):
        self.assertEqual(Comparison(self.args("--dry-run")).count, 25)
        for count in ("0", "-1", "26"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                Comparison(self.args("--count", count, "--dry-run"))

    def test_existing_inference_is_not_overwritten(self):
        raw = self.output / "raw/mac_sql.jsonl"
        raw.parent.mkdir(parents=True)
        raw.write_text("keep me\n")
        with self.assertRaises(FileExistsError):
            Comparison(self.args("--methods", "mac_sql")).run()
        self.assertEqual(raw.read_text(), "keep me\n")

    def test_existing_selection_cannot_silently_override_count(self):
        self.data.mkdir()
        (self.data / "subset.json").write_text(json.dumps(["dev_0000"]))
        with self.assertRaisesRegex(ValueError, "Dataset selection"):
            Comparison(self.args("--count", "20", "--dry-run")).run()
        self.assertFalse(self.output.exists())

    def test_evaluate_only_scores_selected_raw_without_llm_credentials(self):
        database = self.source / "database/demo/demo.sqlite"
        database.parent.mkdir(parents=True)
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE items (name TEXT)")
            connection.execute("INSERT INTO items VALUES ('one')")
        schema = dict(
            db_id="demo",
            table_names_original=["items"],
            table_names=["items"],
            column_names_original=[[-1, "*"], [0, "name"]],
            column_names=[[-1, "*"], [0, "name"]],
            column_types=["text", "text"],
            primary_keys=[],
            foreign_keys=[],
        )
        (self.source / "tables.json").write_text(json.dumps([schema]))
        prepare(self.source, self.data, count=20)
        raw = self.output / "raw/mac_sql.jsonl"
        raw.parent.mkdir(parents=True)
        records = [
            dict(
                idx=i,
                db_id="demo",
                query=row["question"],
                pred=row["query"]
                if i < 19
                else "SELECT name FROM items WHERE name = 'absent'",
            )
            for i, row in enumerate(self.rows[:20])
        ]
        raw.write_text("".join(json.dumps(record) + "\n" for record in records))
        before = raw.read_bytes()
        with (
            patch.dict(
                os.environ, {"LLM_API_KEY": "", "LLM_MODEL": "", "LLM_BASE_URL": ""}
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            Comparison(
                self.args("--count", "20", "--methods", "mac_sql", "--evaluate-only")
            ).run()
        details = json.loads(
            (self.output / "evaluation/mac_sql.details.json").read_text()
        )
        self.assertEqual(details["evaluated_examples"], 20)
        self.assertEqual(details["correct"], 19)
        self.assertEqual(raw.read_bytes(), before)
        self.assertFalse((self.output / "dail_work").exists())
        self.assertFalse((self.output / "sqlite").exists())
        with (self.output / "summary.csv").open() as stream:
            score = next(csv.DictReader(stream))
        self.assertEqual(float(score["EX"]), 0.95)


if __name__ == "__main__":
    unittest.main()

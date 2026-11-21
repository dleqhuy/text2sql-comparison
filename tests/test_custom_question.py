import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from custom_question import preview, run
from run_comparison import Comparison, parser


class CustomQuestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source"
        self.database = self.source / "database/demo/demo.sqlite"
        self.database.parent.mkdir(parents=True)
        with sqlite3.connect(self.database) as conn:
            conn.executescript(
                "CREATE TABLE items(name TEXT); INSERT INTO items VALUES ('one'), ('two');"
            )
        (self.source / "tables.json").write_text(json.dumps([{"db_id": "demo"}]))
        self.output = Path(self.temp.name) / "output"

    def args(self, *extra):
        return parser().parse_args(
            [
                "--spider-data",
                str(self.source),
                "--output",
                str(self.output),
                "--question",
                "How many items?",
                "--db-id",
                "demo",
                *extra,
            ]
        )

    def test_dry_run_plans_all_methods_without_dev_data_or_writes(self):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            run(
                self.args(
                    "--dry-run",
                    "--methods",
                    "few_shot",
                    "mac_sql",
                    "dail_sql",
                    "codex_mcp",
                )
            )
        plan = stream.getvalue()
        for method in ("din_sql", "mac_sql", "dail_sql", "codex_mcp"):
            self.assertIn("--method " + method, plan)
        self.assertNotIn("scripts/evaluate.py", plan)
        self.assertFalse(self.output.exists())

    def test_invalid_options_do_not_write(self):
        for options in (
            ("--count", "1"),
            ("--count", "0"),
            ("--resume",),
            ("--evaluate-only",),
            ("--data-dir", "/tmp/data"),
            ("--question", " "),
            ("--db-id", "../demo"),
            ("--db-id", "missing"),
            ("--workers", "2"),
        ):
            with (
                self.subTest(options=options),
                self.assertRaises((ValueError, FileNotFoundError)),
            ):
                run(self.args("--dry-run", *options))
        for options in (("--question", "test"), ("--db-id", "demo")):
            with self.assertRaises(ValueError):
                run(parser().parse_args(options))
        self.assertFalse(self.output.exists())

    def test_inference_result_is_executed_and_persisted_without_gold(self):
        def worker(comparison, argv, **kwargs):
            request_path = Path(argv[argv.index("--request") + 1])
            request = json.loads(request_path.read_text())
            self.assertEqual(request["question"], "How many items?")
            self.assertEqual(request["spider_data"], str(self.source))
            self.assertNotIn("query", request)
            self.assertEqual(comparison.env["CODEX_MODEL"], "test-model")
            event = {"kind": "result", "output": "SELECT COUNT(*) FROM items"}
            request_path.with_name("events.jsonl").write_text(json.dumps(event) + "\n")

        with (
            patch.object(Comparison, "command", worker),
            patch.object(Path, "is_file", return_value=True),
            patch.dict(
                os.environ,
                {
                    "LLM_MODEL": "test",
                    "LLM_API_KEY": "test",
                    "LLM_BASE_URL": "http://test",
                },
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            run(
                self.args(
                    "--methods",
                    "few_shot",
                    "mac_sql",
                    "dail_sql",
                    "codex_mcp",
                    "--codex-model",
                    "test-model",
                )
            )
        results = json.loads((self.output / "results.json").read_text())
        self.assertEqual(len(results), 4)
        for result in results.values():
            self.assertEqual(result["rows"], [[2]])
            self.assertNotIn("EX", result)
        with self.assertRaises(FileExistsError):
            run(self.args("--dry-run"))

    def test_preview_is_read_only_and_bounded(self):
        with self.assertRaises(sqlite3.OperationalError):
            preview(self.database, "DELETE FROM items RETURNING name")
        self.assertEqual(
            preview(self.database, "SELECT COUNT(*) FROM items")["rows"], [(2,)]
        )
        result = preview(
            self.database,
            "WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<200) SELECT x FROM n",
        )
        self.assertEqual(len(result["rows"]), 100)
        self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()

"""Exercise the shared pipeline with a fake Codex runner and real SQLite scoring."""

import contextlib
import csv
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
from run_comparison import Comparison, parser

FAKE_RUNNER = """
import argparse, json, os, sys
from pathlib import Path
if os.environ.get('CODEX_TEST_CRASH') == '1':
    sys.exit(2)
assert sys.argv[1:3] == ['-m', 'codex_mcp_sql.runner']
p = argparse.ArgumentParser()
p.add_argument('--examples', type=Path)
p.add_argument('--db-root', type=Path)
p.add_argument('--output', type=Path)
p.add_argument('--model')
p.add_argument('--reasoning-effort')
p.add_argument('--resume', action='store_true')
p.add_argument('--workers', type=int, default=1)
a = p.parse_args(sys.argv[3:])
assert a.model == 'test-codex'
assert a.reasoning_effort == 'low'
assert (a.db_root / 'demo/demo.sqlite').is_file()
rows = json.loads(a.examples.read_text())
if a.resume:
    assert (a.output / 'metadata.json').exists()
a.output.mkdir(parents=True, exist_ok=True)
(a.output / 'metadata.json').write_text(json.dumps({'model': a.model}))
pending = os.environ.get('CODEX_TEST_PENDING') == '1'
failed = 1 if pending or os.environ.get('CODEX_TEST_FAILURE') == '1' else 0
records = [dict(example_id=r['example_id'], db_id=r['db_id'], question=r['question'],
                predicted_sql='' if (pending and i > 0) or (failed and i == len(rows)-1)
                else 'SELECT name FROM items') for i,r in enumerate(rows)]
(a.output / 'predictions.jsonl').write_text(''.join(json.dumps(r)+'\\n' for r in records))
(a.output / 'summary.json').write_text(json.dumps({
    'examples':len(rows), 'completed':1 if pending else len(rows)-failed,
    'failed':failed, 'pending':len(rows)-2 if pending else 0, 'planned':0,
    'stop_reason':'usage_limit' if pending else None}))
print('mock-codex', 'resume' if a.resume else 'new')
sys.exit(1 if failed else 0)
"""


class CodexComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source, self.data, self.output = [
            self.root / n for n in ("source", "data", "output")
        ]
        database = self.source / "database/demo/demo.sqlite"
        database.parent.mkdir(parents=True)
        with sqlite3.connect(database) as db:
            db.execute("CREATE TABLE items(name TEXT)")
            db.execute("INSERT INTO items VALUES ('one')")
        rows = [
            {
                "db_id": "demo",
                "question": f"Question {i}",
                "query": "SELECT name FROM items",
            }
            for i in range(3)
        ]
        (self.source / "dev.json").write_text(json.dumps(rows))
        schema = {
            "db_id": "demo",
            "table_names_original": ["items"],
            "table_names": ["items"],
            "column_names_original": [[-1, "*"], [0, "name"]],
            "column_names": [[-1, "*"], [0, "name"]],
            "column_types": ["text", "text"],
            "primary_keys": [],
            "foreign_keys": [],
        }
        (self.source / "tables.json").write_text(json.dumps([schema]))
        self.repo = self.root / "codex-mcp-sql"
        python = self.repo / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text("#!" + sys.executable + "\n" + FAKE_RUNNER)
        python.chmod(0o700)
        self.patch = patch.dict("run_comparison.REPOS", {"codex_mcp": str(self.repo)})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.environment = patch.dict(
            os.environ,
            {
                "LLM_MODEL": "",
                "LLM_API_KEY": "",
                "LLM_BASE_URL": "",
                "CODEX_MODEL": "",
                "CODEX_TEST_PENDING": "",
                "CODEX_TEST_FAILURE": "",
                "CODEX_TEST_CRASH": "",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def args(self, *extra):
        return parser().parse_args(
            [
                "--methods",
                "codex_mcp",
                "--count",
                "3",
                "--codex-model",
                "test-codex",
                "--spider-data",
                str(self.source),
                "--data-dir",
                str(self.data),
                "--output",
                str(self.output),
                *extra,
            ]
        )

    def run_comparison(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            Comparison(self.args(*extra)).run()

    def test_codex_only_runs_and_scores_without_llm_credentials(self):
        os.environ["CODEX_TEST_FAILURE"] = "1"
        self.run_comparison()
        details = json.loads(
            (self.output / "evaluation/codex_mcp.details.json").read_text()
        )
        self.assertEqual((details["evaluated_examples"], details["correct"]), (3, 2))
        self.assertTrue((self.output / "raw/codex_mcp/metadata.json").is_file())
        self.assertIn("mock-codex new", (self.output / "raw/codex_mcp.log").read_text())
        records = (self.output / "predictions/codex_mcp.jsonl").read_text().splitlines()
        self.assertEqual(len(records), 3)
        self.assertEqual(json.loads(records[-1])["predicted_sql"], "")
        self.assertFalse((self.output / "dail_work").exists())

    def test_usage_limit_stops_scoring_then_resume_appends_log_and_scores(self):
        os.environ["CODEX_TEST_PENDING"] = "1"
        with self.assertRaisesRegex(RuntimeError, "incomplete.*--resume"):
            self.run_comparison()
        self.assertFalse((self.output / "summary.csv").exists())
        self.assertFalse((self.output / "predictions").exists())
        os.environ["CODEX_TEST_PENDING"] = ""
        self.run_comparison("--resume")
        details = json.loads(
            (self.output / "evaluation/codex_mcp.details.json").read_text()
        )
        self.assertEqual(details["correct"], 3)
        self.assertEqual(
            (self.output / "raw/codex_mcp.log").read_text().count("mock-codex"), 2
        )

    def test_evaluate_only_uses_saved_predictions_without_model(self):
        self.run_comparison()
        log = self.output / "raw/codex_mcp.log"
        before = log.read_bytes()
        self.run_comparison("--evaluate-only", "--codex-model", "")
        self.assertEqual(log.read_bytes(), before)
        self.assertTrue((self.output / "summary.csv").is_file())

    def test_evaluate_only_refuses_incomplete_run(self):
        os.environ["CODEX_TEST_PENDING"] = "1"
        with self.assertRaises(RuntimeError):
            self.run_comparison()
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.run_comparison("--evaluate-only")
        self.assertFalse((self.output / "summary.csv").exists())

    def test_evaluate_only_combines_all_four_without_repeating_inference(self):
        self.run_comparison()
        raw = self.output / "raw"
        for method in ("few_shot", "dail_sql"):
            (raw / f"{method}.txt").write_text("SELECT name FROM items\n" * 3)
        rows = json.loads((self.data / "examples.json").read_text())
        records = [
            {
                "idx": i,
                "db_id": r["db_id"],
                "query": r["question"],
                "pred": "SELECT name FROM items",
            }
            for i, r in enumerate(rows)
        ]
        (raw / "mac_sql.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in records)
        )
        before = (raw / "codex_mcp.log").read_bytes()
        self.run_comparison(
            "--methods",
            "few_shot",
            "mac_sql",
            "dail_sql",
            "codex_mcp",
            "--evaluate-only",
        )
        with (self.output / "summary.csv").open() as stream:
            scores = list(csv.DictReader(stream))
        self.assertEqual(
            [r["method"] for r in scores],
            ["few_shot", "mac_sql", "dail_sql", "codex_mcp"],
        )
        self.assertTrue(all(float(r["EX"]) == 1 for r in scores))
        self.assertEqual((raw / "codex_mcp.log").read_bytes(), before)
        self.assertFalse((self.output / "dail_work").exists())

    def test_dry_run_prints_sdk_and_normalization_without_writes(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            Comparison(self.args("--dry-run")).run()
        plan = output.getvalue()
        self.assertIn("-m codex_mcp_sql.runner", plan)
        self.assertIn("--examples " + str(self.data / "examples.json"), plan)
        self.assertIn("--db-root " + str(self.source / "database"), plan)
        self.assertIn("--model test-codex --reasoning-effort low", plan)
        self.assertIn("normalize_codex_mcp.py", plan)
        self.assertIn("--prediction codex_mcp=", plan)
        self.assertFalse(self.data.exists())
        self.assertFalse(self.output.exists())

    def test_worker_count_is_forwarded_to_codex(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            Comparison(self.args("--workers", "4", "--dry-run")).run()
        self.assertIn("--workers 4", output.getvalue())
        with self.assertRaisesRegex(ValueError, "--workers must be positive"):
            Comparison(self.args("--workers", "0"))
        with self.assertRaisesRegex(ValueError, "codex_mcp only"):
            Comparison(self.args("--methods", "mac_sql", "--workers", "4"))

    def test_resume_is_explicit_and_codex_only(self):
        for extra in [
            ("--resume", "--methods", "mac_sql"),
            ("--resume", "--methods", "mac_sql", "codex_mcp"),
            ("--resume", "--evaluate-only"),
        ]:
            with (
                self.subTest(extra=extra),
                self.assertRaisesRegex(ValueError, "--resume requires"),
            ):
                Comparison(self.args(*extra))
        with self.assertRaises(FileNotFoundError):
            Comparison(self.args("--resume")).validate()

    def test_model_configuration_and_existing_run_guard(self):
        args = self.args("--codex-model", "")
        with self.assertRaisesRegex(ValueError, "--codex-model"):
            Comparison(args).validate()
        os.environ["CODEX_MODEL"] = "test-codex"
        self.assertEqual(Comparison(args).codex_model, "test-codex")
        path = self.output / "raw/codex_mcp"
        path.mkdir(parents=True)
        with self.assertRaisesRegex(FileExistsError, "Existing Codex run"):
            Comparison(self.args()).validate()

    def test_runner_configuration_failure_does_not_score_stale_output(self):
        self.run_comparison()
        score = self.output / "summary.csv"
        before = score.read_bytes()
        os.environ["CODEX_TEST_CRASH"] = "1"
        with self.assertRaisesRegex(RuntimeError, "exit 2"):
            self.run_comparison("--resume")
        self.assertEqual(score.read_bytes(), before)

    def test_mixed_methods_still_require_llm_credentials(self):
        with self.assertRaisesRegex(ValueError, "LLM_MODEL"):
            Comparison(self.args("--methods", "mac_sql", "codex_mcp")).validate()


if __name__ == "__main__":
    unittest.main()

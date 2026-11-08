"""Live adapters: read-only results, trace integrity and lifecycle semantics."""

import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import live_server as server
import live_worker as worker


class LivePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.db = self.data / "database/demo/demo.sqlite"
        self.db.parent.mkdir(parents=True)
        with sqlite3.connect(self.db) as connection:
            connection.executescript(
                "CREATE TABLE items (name TEXT); INSERT INTO items VALUES ('a'), ('b'), ('b');"
            )
        (self.data / "dev.json").write_text(
            json.dumps(
                [
                    {
                        "question": "Count items",
                        "db_id": "demo",
                        "query": "SELECT COUNT(*) FROM items",
                    }
                ]
            )
        )
        self.addCleanup(patch.stopall)
        patch.object(server, "DATA", self.data).start()
        patch.object(server, "ACTIVE", {}).start()

    def test_result_execution_is_read_only(self):
        self.assertEqual(
            server.query_result(self.db, "SELECT COUNT(*) FROM items")["rows"], [(3,)]
        )
        with self.assertRaises(sqlite3.OperationalError):
            server.query_result(self.db, "DELETE FROM items")
        self.assertEqual(
            server.query_result(self.db, "SELECT COUNT(*) FROM items")["rows"], [(3,)]
        )

    def test_result_preview_is_bounded(self):
        result = server.query_result(
            self.db,
            "WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<200) SELECT x FROM n",
        )
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["rows"]), 100)

    def test_scoring_preserves_duplicate_and_order_semantics(self):
        self.assertTrue(
            server.score_sql(
                self.db,
                "SELECT name FROM items ORDER BY name DESC",
                "SELECT name FROM items",
            )["correct"]
        )
        self.assertFalse(
            server.score_sql(
                self.db, "SELECT DISTINCT name FROM items", "SELECT name FROM items"
            )["correct"]
        )
        self.assertFalse(
            server.score_sql(
                self.db,
                "SELECT name FROM items ORDER BY name DESC",
                "SELECT name FROM items ORDER BY name ASC",
            )["correct"]
        )

    def test_invalid_database_paths_are_rejected(self):
        self.assertEqual(server.database("demo"), self.db.resolve())
        for value in ("../demo", "a/b", "", None, "missing"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                server.database(value)

    def test_trace_reader_tolerates_partial_lines_and_orders_methods(self):
        for method, time_value in [("mac_sql", 2), ("din_sql", 1)]:
            path = self.root / method
            path.mkdir()
            (path / "events.jsonl").write_text(
                json.dumps({"time": time_value, "method": method}) + '\n{"time":'
            )
        self.assertEqual([e["time"] for e in server.events(self.root)], [1, 2])

    def test_worker_redacts_provider_keys_in_events(self):
        patch.object(worker, "OUTPUT", self.root).start()
        patch.object(worker, "METHOD", "din_sql").start()
        with patch.dict(os.environ, LLM_API_KEY="secret-for-test"):
            worker.emit("error", "Provider", output="Failed with secret-for-test")
        text = (self.root / "events.jsonl").read_text()
        self.assertNotIn("secret-for-test", text)
        self.assertIn("[REDACTED]", text)

    def run_fake(self, index=None, cancel=None, returncode=0):
        path = self.root / "runs/abcdef123456"
        path.mkdir(parents=True)
        request = {
            "question": "Count items",
            "db_id": "demo",
            "methods": ["din_sql"],
            "example_index": index,
        }
        server.save(path / "run.json", {"id": path.name, "status": "running"})
        server.ACTIVE[path.name] = {
            "process": None,
            "cancel": cancel or threading.Event(),
        }

        def popen(argv, **kwargs):
            self.assertNotIn(
                "ground_truth", json.loads((path / "din_sql/request.json").read_text())
            )
            if not returncode:
                server.append(
                    path,
                    "din_sql",
                    "result",
                    "Final SQL",
                    output="SELECT COUNT(*) FROM items",
                )
            return SimpleNamespace(
                poll=lambda: returncode,
                wait=lambda *args: returncode,
                returncode=returncode,
            )

        with patch.object(server.subprocess, "Popen", side_effect=popen):
            server.execute_run(path, request, cancel or threading.Event())
        return path

    def test_custom_input_is_never_scored_against_gold(self):
        path = self.run_fake()
        output = next(
            e["output"]
            for e in server.events(path)
            if e["stage"] == "SQLite execution" and e["kind"] == "finish"
        )
        self.assertNotIn("evaluation", output)
        self.assertEqual(
            json.loads((path / "run.json").read_text())["status"], "completed"
        )

    def test_selected_example_is_scored_with_original_ex_rules(self):
        path = self.run_fake(index=0)
        output = next(
            e["output"]
            for e in server.events(path)
            if e["stage"] == "SQLite execution" and e["kind"] == "finish"
        )
        self.assertTrue(output["evaluation"]["correct"])

    def test_worker_crash_becomes_visible_failure(self):
        path = self.run_fake(returncode=1)
        self.assertEqual(
            json.loads((path / "run.json").read_text())["status"], "partial_failure"
        )
        self.assertTrue(any(e["kind"] == "failed" for e in server.events(path)))
        self.assertNotIn(path.name, server.ACTIVE)

    def test_cancel_before_start_does_not_spawn_worker(self):
        cancel = threading.Event()
        cancel.set()
        path = self.run_fake(cancel=cancel)
        self.assertEqual(
            json.loads((path / "run.json").read_text())["status"], "cancelled"
        )
        self.assertEqual(server.events(path), [])

    def test_persistence_failure_releases_active_slot(self):
        with patch.object(
            server, "ON_UPDATE", side_effect=RuntimeError("DB unavailable")
        ):
            with self.assertRaisesRegex(RuntimeError, "DB unavailable"):
                self.run_fake()
        self.assertFalse(server.ACTIVE)


if __name__ == "__main__":
    unittest.main()

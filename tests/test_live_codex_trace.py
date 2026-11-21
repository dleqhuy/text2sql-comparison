"""Codex trace lifecycle and public payloads, without a model or MCP process."""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import live_worker as worker


class CodexTraceTests(unittest.TestCase):
    def exercise(self, *, accepted=True, crash=False):
        def original_write(path, value):
            path.write_text(json.dumps(value))

        runner = SimpleNamespace(write_json=original_write)

        async def run(args):
            trace = args.output / "traces/0000"
            trace.mkdir(parents=True)
            runner.write_json(
                trace / "request.json",
                {
                    "prompt": {"db_id": "demo", "question": "Count items"},
                    "instructions": "Inspect schema, test SQL, return JSON.",
                    "output_schema": {"required": ["sql"]},
                    "config_overrides": {},
                },
            )
            if crash:
                raise RuntimeError("runner crashed")
            calls = [
                {
                    "tool": "search_objects",
                    "arguments": {"query": "items"},
                    "result": {"objects": []},
                },
                {
                    "tool": "execute_sql",
                    "arguments": {"sql": "SELECT 1", "max_rows": 0},
                    "error": "invalid max_rows",
                },
                {
                    "tool": "execute_sql",
                    "arguments": {"sql": "SELECT 1", "max_rows": 1},
                    "result": {"columns": ["1"], "rows": [[1]]},
                },
            ]
            (trace / "tools.jsonl").write_text(
                "".join(json.dumps(call) + "\n" for call in calls)
            )
            runner.write_json(
                trace / "turn.json",
                {
                    "status": "completed",
                    "final_response": '{"sql":"SELECT 1"}',
                    "usage": {"tokens": 10},
                    "error": None,
                    "items": [{"reasoning": "PRIVATE_REASONING_SENTINEL"}],
                },
            )
            # An SDK completion must not close the visible agent before validation.
            events = [
                json.loads(line)
                for line in (worker.OUTPUT / "events.jsonl").read_text().splitlines()
            ]
            self.assertFalse(
                any(
                    e["stage"] == "Codex turn" and e["kind"] == "finish" for e in events
                )
            )
            result = {
                "status": "completed" if accepted else "failed",
                "predicted_sql": "SELECT 1" if accepted else "",
                "elapsed_seconds": 0.25,
            }
            if accepted:
                result["tool_calls"] = len(calls)
            else:
                result["error"] = (
                    "Final SQL requires successful schema discovery and a matching SQL test"
                )
            runner.write_json(trace / "result.json", result)

        runner.run = run
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch.dict(
                    sys.modules, {"codex_mcp_sql": SimpleNamespace(runner=runner)}
                ),
                patch.object(worker, "OUTPUT", root),
                patch.object(worker, "METHOD", "codex_mcp"),
            ):
                coroutine = worker.codex(
                    {"db_id": "demo", "question": "Count items"}, root / "source"
                )
                if crash or not accepted:
                    with self.assertRaises(RuntimeError):
                        asyncio.run(coroutine)
                else:
                    self.assertEqual(asyncio.run(coroutine), "SELECT 1")
                text = (root / "events.jsonl").read_text()
            self.assertIs(runner.write_json, original_write)
        self.assertNotIn("PRIVATE_REASONING_SENTINEL", text)
        return [json.loads(line) for line in text.splitlines()]

    def test_agent_finishes_after_tool_drain_and_audit_acceptance(self):
        events = self.exercise()
        self.assertEqual(
            [(e["stage"], e["kind"]) for e in events],
            [
                ("Codex turn", "start"),
                ("search_objects", "tool"),
                ("execute_sql", "error"),
                ("execute_sql", "tool"),
                ("Codex turn", "finish"),
            ],
        )
        self.assertEqual(events[0]["input"]["runtime"]["max_tool_calls"], 20)
        self.assertEqual(events[0]["input"]["runtime"]["query_timeout_seconds"], 5)
        self.assertEqual(events[2]["output"], "invalid max_rows")
        self.assertTrue(events[-1]["output"]["audit_verified"])
        self.assertEqual(events[-1]["output"]["tool_calls"], 3)
        self.assertEqual(events[-1]["output"]["sql"], "SELECT 1")

    def test_sdk_completed_but_audit_rejected_is_an_agent_error(self):
        events = self.exercise(accepted=False)
        self.assertEqual(events[-1]["kind"], "error")
        self.assertEqual(events[-1]["output"]["status"], "completed")
        self.assertEqual(events[-1]["output"]["runner_status"], "failed")
        self.assertIsNone(events[-1]["output"]["audit_verified"])
        self.assertEqual(events[-1]["output"]["sql"], "")

    def test_runner_hook_is_restored_after_an_unexpected_crash(self):
        self.assertEqual(len(self.exercise(crash=True)), 1)

"""Run DIN's real single-question control flow with deterministic LLM responses."""

import ast
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import live_worker as worker


class DinTraceTests(unittest.TestCase):
    def exercise(self, classification, retry=False):
        repo = worker.WORKSPACE / "Few-shot-NL2SQL-with-prompting"
        module = ModuleType("din_trace_test")
        # Keep the actual parsing, branching and self-correction behavior, without
        # importing the model SDK or loading the Spider schema into pandas.
        module.__dict__.update(runpy.run_path(str(repo / "response_utils.py")))
        module.LLM_CONFIG = {}
        module.time = SimpleNamespace(sleep=lambda _: None)
        module.generate = Mock(
            side_effect=[
                "Schema_links: [items.id]",
                classification,
                *([RuntimeError("provider unavailable")] if retry else []),
                "SQL: `SELECT COUNT(*) FROM items`",
                "COUNT(*) FROM items",
            ]
        )
        provider = module.generate
        module.creatiing_schema = lambda path: (None, None, None)
        for name in (
            "schema_linking_prompt_maker",
            "classification_prompt_maker",
            "easy_prompt_maker",
            "medium_prompt_maker",
            "hard_prompt_maker",
            "debuger",
        ):
            setattr(module, name, lambda *args, _name=name: f"{_name}: {args}")
        source = ast.parse((repo / "DIN-SQL.py").read_text())
        functions = ast.Module(
            body=[
                node
                for node in source.body
                if isinstance(node, ast.FunctionDef)
                and node.name
                in ("GPT4_generation", "GPT4_debug", "retry_call", "predict_one")
            ],
            type_ignores=[],
        )
        exec(compile(functions, str(repo / "DIN-SQL.py"), "exec"), module.__dict__)  # noqa: S102 - fixed local function definitions
        spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))
        import_path, argv = sys.path[:], sys.argv[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), import_path))
        self.addCleanup(lambda: sys.argv.__setitem__(slice(None), argv))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch.object(
                    worker.importlib.util, "spec_from_file_location", return_value=spec
                ),
                patch.object(
                    worker.importlib.util, "module_from_spec", return_value=module
                ),
                patch.object(worker, "OUTPUT", root),
                patch.object(worker, "METHOD", "din_sql"),
            ):
                result = worker.din({"question": "Count items", "db_id": "demo"}, root)
                events = [
                    json.loads(line)
                    for line in (root / "events.jsonl").read_text().splitlines()
                ]
        return result, events, provider

    def test_prompts_inputs_parsed_outputs_and_raw_responses_agree(self):
        result, events, generate = self.exercise('Label: "EASY"')
        self.assertEqual(result, "SELECT COUNT(*) FROM items")
        starts = {e["stage"]: e["input"] for e in events if e["kind"] == "start"}
        finishes = {e["stage"]: e["output"] for e in events if e["kind"] == "finish"}
        self.assertEqual(starts["Schema linking"]["question"], "Count items")
        self.assertEqual(finishes["Schema linking"]["schema_links"], "[items.id]")
        self.assertEqual(finishes["Classification"]["label"], "EASY")
        self.assertEqual(starts["SQL generation"]["branch"], "EASY")
        self.assertIn("easy_prompt_maker", starts["SQL generation"]["prompt"])
        self.assertEqual(
            finishes["SQL generation"]["sql"], starts["Self-correction"]["sql"]
        )
        self.assertEqual(finishes["Self-correction"]["response"], "COUNT(*) FROM items")
        self.assertEqual(finishes["Self-correction"]["sql"], result)
        self.assertEqual(generate.call_count, 4)
        self.assertEqual(
            generate.call_args_list[-1].args[1], starts["Self-correction"]["prompt"]
        )

    def test_recorded_branch_includes_the_runners_parser_fallback(self):
        _, events, _ = self.exercise("No recognized label")
        classification = next(
            e["output"]
            for e in events
            if e["stage"] == "Classification" and e["kind"] == "finish"
        )
        generation = next(
            e["input"]
            for e in events
            if e["stage"] == "SQL generation" and e["kind"] == "start"
        )
        self.assertEqual(classification["label"], "NESTED")
        self.assertEqual(generation["branch"], "NESTED")
        self.assertIn("hard_prompt_maker", generation["prompt"])

    def test_provider_error_retries_the_same_prompt_without_sqlite_feedback(self):
        result, events, provider = self.exercise('Label: "EASY"', retry=True)
        calls = [e for e in events if e["stage"] == "SQL generation"]
        self.assertEqual(
            [e["kind"] for e in calls], ["start", "error", "start", "finish"]
        )
        self.assertEqual(calls[0]["input"]["prompt"], calls[2]["input"]["prompt"])
        self.assertEqual(provider.call_count, 5)
        self.assertEqual(result, "SELECT COUNT(*) FROM items")
        self.assertFalse(any(e["stage"] == "SQLite execution" for e in events))

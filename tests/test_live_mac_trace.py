"""MAC trace instrumentation without a provider call or external database."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import live_worker as worker


class MacTraceTests(unittest.TestCase):
    def exercise(self, scenario="success"):
        agents = SimpleNamespace()

        class Selector:
            name = "Selector"

            def talk(self, message):
                message.update(desc_str="items(id)", pruned=False)

        class Decomposer:
            name = "Decomposer"

            def talk(self, message):
                agents.LLM_API_FUC("real decomposer prompt")
                message["final_sql"] = "SELECT 1"

        class Refiner:
            name = "Refiner"

            def _execute_sql(self, sql, db_id):
                if scenario in ("repair_success", "exhausted") and sql != "SELECT 2":
                    return {"sql": sql, "sqlite_error": "missing column"}
                if scenario == "exhausted":
                    return {"sql": sql, "sqlite_error": "still invalid"}
                return {"sql": sql, "data": [[1]], "sqlite_error": ""}

            def talk(self, message):
                if scenario == "no_check":
                    message.update(pred=message["final_sql"], send_to="System")
                    return
                sql = message.get("pred", message["final_sql"])
                result = self._execute_sql(sql, message["db_id"])
                if result.get("sqlite_error"):
                    agents.LLM_API_FUC("Fix SQL using this SQLite error")
                    message.update(pred="SELECT 2", send_to="Refiner", fixed=True)
                else:
                    message.update(pred=sql, send_to="System")

        agents.Selector, agents.Decomposer, agents.Refiner = (
            Selector,
            Decomposer,
            Refiner,
        )

        class Manager:
            def __init__(self, **kwargs):
                pass

            def start(self, message):
                for agent in (Selector(), Decomposer(), Refiner()):
                    agent.talk(message)
                for _ in range(2):
                    if message.get("send_to") == "Refiner":
                        Refiner().talk(message)

        modules = {
            "core": SimpleNamespace(
                agents=agents,
                llm=SimpleNamespace(safe_call_llm=lambda prompt: "SELECT 1"),
            ),
            "core.chat_manager": SimpleNamespace(ChatManager=Manager),
            "core.const": SimpleNamespace(SYSTEM_NAME="System"),
        }
        cwd, import_path = os.getcwd(), sys.path[:]
        self.addCleanup(os.chdir, cwd)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), import_path))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "MAC-SQL").mkdir()
            with (
                patch.dict(sys.modules, modules),
                patch.dict(os.environ, LLM_MODEL="test-model"),
                patch.object(worker, "WORKSPACE", root),
                patch.object(worker, "OUTPUT", root),
                patch.object(worker, "METHOD", "mac_sql"),
            ):
                if scenario in ("exhausted", "no_check"):
                    with self.assertRaisesRegex(
                        RuntimeError, "without a successful execution"
                    ):
                        worker.mac({"db_id": "demo", "question": "test"}, root / "data")
                else:
                    result = worker.mac(
                        {"db_id": "demo", "question": "test"}, root / "data"
                    )
                    self.assertEqual(
                        result,
                        "SELECT 2" if scenario == "repair_success" else "SELECT 1",
                    )
                events = [
                    json.loads(line)
                    for line in (root / "events.jsonl").read_text().splitlines()
                ]
            os.chdir(cwd)
        return events

    def test_agent_state_encloses_prompt_and_refiner_execution(self):
        events = self.exercise()
        self.assertEqual(
            [(e["stage"], e["kind"]) for e in events],
            [
                ("Selector · state", "start"),
                ("Selector · state", "finish"),
                ("Decomposer · state", "start"),
                ("Decomposer", "start"),
                ("Decomposer", "finish"),
                ("Decomposer · state", "finish"),
                ("Refiner · state", "start"),
                ("Refiner · execution", "start"),
                ("Refiner · execution", "finish"),
                ("Refiner · state", "finish"),
            ],
        )
        self.assertNotIn("final_sql", events[2]["input"])
        self.assertEqual(events[3]["input"], "real decomposer prompt")
        self.assertEqual(events[7]["input"], {"sql": "SELECT 1", "db_id": "demo"})
        self.assertEqual(events[8]["output"]["data"], [[1]])
        self.assertIn("elapsed", events[-1])
        self.assertTrue(events[-1]["output"]["execution_verified"])

    def test_error_is_repaired_and_reexecuted_before_returning_sql(self):
        events = self.exercise("repair_success")
        checks = [
            e
            for e in events
            if e["stage"] == "Refiner · execution" and e["kind"] == "finish"
        ]
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[0]["output"]["sqlite_error"], "missing column")
        self.assertEqual(checks[1]["output"]["sql"], "SELECT 2")
        rounds = [
            e["output"]
            for e in events
            if e["stage"] == "Refiner · state" and e["kind"] == "finish"
        ]
        self.assertFalse(rounds[0]["execution_verified"])
        self.assertTrue(rounds[1]["execution_verified"])

    def test_unexecuted_sql_is_not_returned_for_gold_evaluation(self):
        events = self.exercise("no_check")
        self.assertFalse(events[-1]["output"]["execution_verified"])

    def test_repair_limit_does_not_accept_an_unverified_candidate(self):
        events = self.exercise("exhausted")
        rounds = [
            e
            for e in events
            if e["stage"] == "Refiner · state" and e["kind"] == "finish"
        ]
        self.assertEqual(len(rounds), 3)
        self.assertTrue(all(not e["output"]["execution_verified"] for e in rounds))

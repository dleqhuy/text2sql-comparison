"""Gold-free live DAIL staging and trace hooks, without downloading models."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import live_dail


class LiveDailTests(unittest.TestCase):
    def exercise(self, fail=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "source", root / "output"
            source.mkdir()
            output.mkdir()
            (source / "database").mkdir()
            for name in ["tables.json", "train_spider.json", "train_others.json"]:
                (source / name).write_text("[]")
            (source / "train_gold.sql").write_text("SELECT 7\n")
            events, scripts, prompts = [], [], []

            class Prompt:
                def record_example_quality(self, examples, target):
                    pass

                def format(self, target, **kwargs):
                    self.record_example_quality(
                        [
                            {
                                "db_id": "train",
                                "question": "Train question",
                                "query": "SELECT 7",
                            }
                        ],
                        target,
                    )
                    return {
                        "prompt": target["question"]
                        + " schema + train example SELECT 7",
                        "n_examples": 1,
                        "db_id": target["db_id"],
                    }

            prompt_module = ModuleType("prompt.PromptICLTemplate")
            prompt_module.BasicICLPrompt = Prompt
            chat = ModuleType("llm.chatgpt")
            chat.LLM = SimpleNamespace(TASK_COMPLETIONS=[])
            chat.ask_chat = lambda *args: {"response": "SELECT 2", "total_tokens": 3}
            chat.ask_llm = lambda *args: {"response": ["SELECT 2"], "total_tokens": 3}
            llm = ModuleType("llm")
            llm.chatgpt = chat
            tokenize = ModuleType("nltk.tokenize")
            tokenize.TreebankWordTokenizer = lambda: type(
                "Tokenizer", (), {"tokenize": lambda _, q: q.split()}
            )()

            def execute(script, run_name):
                scripts.append(Path(script).name)
                if Path(script).name == "data_preprocess.py":
                    staged = json.loads(Path("dataset/spider/dev.json").read_text())[0]
                    self.assertEqual(staged["query"], "SELECT 1")
                    self.assertNotIn("gold-secret", json.dumps(staged))
                elif Path(script).name == "generate_question.py":
                    if fail:
                        raise RuntimeError("selection failed")
                    selector = sys.argv[sys.argv.index("--selector_type") + 1]
                    self.assertEqual(sys.argv[sys.argv.index("--k_shot") + 1], "9")
                    if "--pre_test_result" in sys.argv:
                        self.assertEqual(
                            Path(sys.argv[-1]).read_text().strip(), "SELECT 2"
                        )
                    target = json.loads(Path("dataset/spider/dev.json").read_text())[0]
                    result = Prompt().format(target)
                    folder = Path(
                        f"dataset/process/SPIDER-TEST_SQL_9-SHOT_{selector}_QA-EXAMPLE_CTX-200_ANS-4096"
                    )
                    folder.mkdir(parents=True)
                    (folder / "questions.json").write_text(
                        json.dumps({"questions": [result]})
                    )
                else:
                    folder = Path(sys.argv[-1])
                    prompt = json.loads((folder / "questions.json").read_text())[
                        "questions"
                    ][0]["prompt"]
                    prompts.append(prompt)
                    result = chat.ask_llm("test/model", [prompt], 0, 1)
                    (folder / "RESULTS_MODEL-test_model.txt").write_text(
                        result["response"][0] + "\n"
                    )

            old_cwd, old_argv = Path.cwd(), sys.argv[:]
            original_format = Prompt.format
            with (
                patch.dict(
                    sys.modules,
                    {
                        "prompt.PromptICLTemplate": prompt_module,
                        "llm": llm,
                        "llm.chatgpt": chat,
                        "nltk.tokenize": tokenize,
                    },
                ),
                patch.dict(os.environ, {"LLM_MODEL": "test/model"}),
                patch.object(live_dail.runpy, "run_path", side_effect=execute),
            ):
                row = {
                    "db_id": "demo",
                    "question": "Count items",
                    "query": "gold-secret",
                }
                if fail:
                    with self.assertRaisesRegex(RuntimeError, "selection failed"):
                        live_dail.run(
                            row,
                            source,
                            output,
                            lambda kind, stage, **data: events.append(
                                dict(kind=kind, stage=stage, **data)
                            ),
                        )
                else:
                    self.assertEqual(
                        live_dail.run(
                            row,
                            source,
                            output,
                            lambda kind, stage, **data: events.append(
                                dict(kind=kind, stage=stage, **data)
                            ),
                        ),
                        "SELECT 2",
                    )
            self.assertEqual(Path.cwd(), old_cwd)
            self.assertEqual(sys.argv, old_argv)
            self.assertIs(Prompt.format, original_format)
            return events, scripts, prompts

    def test_two_pass_trace_uses_actual_selected_examples_and_preliminary_sql(self):
        events, scripts, prompts = self.exercise()
        self.assertEqual(
            scripts,
            [
                "data_preprocess.py",
                "generate_question.py",
                "ask_llm.py",
                "generate_question.py",
                "ask_llm.py",
            ],
        )
        self.assertEqual(len(prompts), 2)
        selected = [
            e
            for e in events
            if e["kind"] == "finish" and e["stage"].startswith("Example selection")
        ]
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["output"]["examples"][0]["query"], "SELECT 7")
        self.assertNotIn("gold-secret", json.dumps(events))

    def test_failure_is_recorded_and_instrumentation_restored(self):
        events, _, _ = self.exercise(fail=True)
        self.assertTrue(
            any(
                e["kind"] == "error" and e["stage"] == "Example selection · pass 1"
                for e in events
            )
        )


if __name__ == "__main__":
    unittest.main()


class RetryTests(unittest.TestCase):
    def test_provider_failure_stops_after_three_attempts(self):
        from unittest.mock import Mock

        chat = SimpleNamespace(
            LLM=SimpleNamespace(TASK_COMPLETIONS=[]),
            ask_chat=Mock(side_effect=RuntimeError("provider unavailable")),
        )
        with (
            patch.object(live_dail.time, "sleep"),
            self.assertRaisesRegex(RuntimeError, "provider unavailable"),
        ):
            live_dail.ask_bounded(chat, "model", ["prompt"], 0, 1)
        self.assertEqual(chat.ask_chat.call_count, 3)


class TrainingCacheTests(unittest.TestCase):
    def test_cached_train_keeps_new_question_linking_and_skips_train_work(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output, cache = root / "source", root / "output", root / "cache"
            source.mkdir()
            cache.mkdir()
            stage = output / "dail_work/dataset/spider"
            stage.mkdir(parents=True)
            (source / "train_spider.json").write_text('[{"question":"train one"}]')
            (source / "train_others.json").write_text('[{"question":"train two"}]')
            (cache / "train_schema-linking.jsonl").write_text('{"cached":"train"}\n')
            module = ModuleType("data_preprocess")
            calls = []

            def linking(test, train, table, db, dataset, **kwargs):
                calls.append((test, train, kwargs))
                self.assertEqual(json.loads((stage / train).read_text()), [])
                enc = stage / "enc"
                enc.mkdir()
                (enc / "test_schema-linking.jsonl").write_text('{"new":"question"}\n')

            module.schema_linking_producer = linking
            with (
                patch.object(live_dail, "training_cache", return_value=cache),
                patch.dict(sys.modules, {"data_preprocess": module}),
                patch.object(live_dail.runpy, "run_path") as script,
            ):
                self.assertTrue(live_dail.preprocess("script.py", source, root, output))
                script.assert_not_called()
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0][2]["tokenize_only"])
            self.assertEqual(
                (stage / "enc/test_schema-linking.jsonl").read_text(),
                '{"new":"question"}\n',
            )
            self.assertEqual(
                (stage / "enc/train_schema-linking.jsonl").read_text(),
                '{"cached":"train"}\n',
            )
            self.assertEqual(
                len(json.loads((stage / "train_spider_and_others.json").read_text())), 2
            )

    def test_training_or_database_changes_invalidate_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "data"
            repo = root / "repo"
            source.mkdir()
            (repo / "utils").mkdir(parents=True)
            for name in ["train_spider.json", "train_others.json", "tables.json"]:
                (source / name).write_text("[]")
            (repo / "data_preprocess.py").write_text("# implementation")
            (source / "database").mkdir()
            db = source / "database/demo.sqlite"
            db.write_bytes(b"initial")
            first = live_dail.training_cache(source, repo)
            (source / "train_spider.json").write_text("[{}]")
            second = live_dail.training_cache(source, repo)
            db.write_bytes(b"changed database")
            third = live_dail.training_cache(source, repo)
            self.assertNotEqual(first, second)
            self.assertNotEqual(second, third)

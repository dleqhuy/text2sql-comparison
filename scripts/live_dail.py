"""Observe the existing two-pass DAIL runner on one gold-free live input."""

import argparse
import hashlib
import json
import os
import runpy
import shutil
import sys
import time
from pathlib import Path

from run_comparison import Comparison


def ask_bounded(chatgpt, model, batch, temperature, n, attempts=3):
    """Use DAIL's provider calls and response shape with a finite live retry budget."""
    for attempt in range(attempts):
        try:
            if model in chatgpt.LLM.TASK_COMPLETIONS:
                return chatgpt.ask_completion(model, batch, temperature)
            response = chatgpt.ask_chat(
                model, [{"role": "user", "content": batch[0]}], temperature, n
            )
            response["response"] = [response["response"]]
            return response
        except Exception:
            if attempt + 1 == attempts:
                raise
            time.sleep(1)


def training_cache(source, repo):
    """Invalidate cached train linking when data, database files or code changes."""
    digest = hashlib.sha256(b"live-dail-train-linking-v1")
    for name in ("train_spider.json", "train_others.json", "tables.json"):
        digest.update((source / name).read_bytes())
    for path in sorted((repo / "utils").rglob("*.py")) + [repo / "data_preprocess.py"]:
        digest.update(path.read_bytes())
    for path in sorted((source / "database").rglob("*.sqlite")):
        stat = path.stat()
        digest.update(
            str((str(path.resolve()), stat.st_size, stat.st_mtime_ns)).encode()
        )
    return Path(__file__).resolve().parents[1] / ".cache/dail-live" / digest.hexdigest()


def preprocess(script, source, repo, output):
    cache = training_cache(source, repo)
    stage = output / "dail_work/dataset/spider"
    cached = cache / "train_schema-linking.jsonl"
    if cached.is_file():
        from data_preprocess import schema_linking_producer

        train = json.loads((source / "train_spider.json").read_text())
        train += json.loads((source / "train_others.json").read_text())
        (stage / "train_spider_and_others.json").write_text(json.dumps(train))
        (stage / "empty_train.json").write_text("[]")
        # Always compute linking for the new question; only train is reused.
        schema_linking_producer(
            "dev.json",
            "empty_train.json",
            "tables.json",
            "database",
            str(stage),
            tokenize_only=True,
        )
        shutil.copy2(cached, stage / "enc/train_schema-linking.jsonl")
        return True
    runpy.run_path(script, run_name="__main__")
    linked = stage / "enc/train_schema-linking.jsonl"
    if linked.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        temp = cache / "train_schema-linking.tmp"
        shutil.copy2(linked, temp)
        temp.replace(cached)
    return False


def run(row, source, output, emit):
    repo = Path(__file__).resolve().parents[2] / "DAIL-SQL"
    sys.path.insert(0, str(repo))
    from nltk.tokenize import TreebankWordTokenizer

    data = output / "input"
    data.mkdir()
    # DAIL expects query metadata even for inference. A constant placeholder
    # supports its dataset API; never copy a selected example's gold SQL here.
    target = {
        "db_id": row["db_id"],
        "question": row["question"],
        "question_toks": TreebankWordTokenizer().tokenize(row["question"]),
        "query": "SELECT 1",
    }
    (data / "dev.json").write_text(json.dumps([target]))
    (data / "tables.json").symlink_to(source / "tables.json")
    (data / "gold.txt").write_text("SELECT 1\t" + row["db_id"] + "\n")
    (output / "raw").mkdir()

    comparison = Comparison.__new__(Comparison)
    comparison.args = argparse.Namespace(dry_run=False)
    comparison.output, comparison.data = output, data
    comparison.source, comparison.count = source, 1
    comparison.env = dict(os.environ)
    original_cwd, original_argv = Path.cwd(), sys.argv[:]

    def command(argv, cwd, log):
        from time import monotonic

        # Reuse the CLI's paths, selectors, settings and staging. Execute its
        # scripts inside this isolated worker so actual calls can be observed.
        argv = list(map(str, argv))
        script = Path(argv[1]).name
        phase = "1" if "EUCDISQUESTIONMASK" in argv else "2"
        if script == "data_preprocess.py":
            stage = "Preprocessing"
        elif script == "generate_question.py":
            stage = "Example selection · pass " + phase
        else:
            phase = "1" if "EUCDISQUESTIONMASK_QA" in argv[-1] else "2"
            stage = "SQL generation · pass " + phase
        os.environ.update(comparison.env)
        os.chdir(cwd)
        sys.argv = argv[1:]
        started = monotonic()
        emit("start", stage, input={"script": script, "arguments": argv[2:]})
        try:
            if script == "generate_question.py":
                from prompt.PromptICLTemplate import BasicICLPrompt

                original_format = BasicICLPrompt.format
                original_quality = BasicICLPrompt.record_example_quality
                selected = []

                def quality(self, examples, target):
                    selected[:] = [
                        {k: e[k] for k in ("db_id", "question", "query")}
                        for e in examples
                    ]
                    return original_quality(self, examples, target)

                def format_prompt(self, *args, **kwargs):
                    result = original_format(self, *args, **kwargs)
                    emit(
                        "finish",
                        stage,
                        output={
                            "examples": selected,
                            "n_examples": result["n_examples"],
                            "prompt": result["prompt"],
                            "db_id": result["db_id"],
                        },
                        elapsed=monotonic() - started,
                    )
                    return result

                BasicICLPrompt.format = format_prompt
                BasicICLPrompt.record_example_quality = quality
                try:
                    runpy.run_path(argv[1], run_name="__main__")
                finally:
                    BasicICLPrompt.format = original_format
                    BasicICLPrompt.record_example_quality = original_quality
            elif script == "ask_llm.py":
                from llm import chatgpt

                original_ask = chatgpt.ask_llm

                def ask(model, batch, temperature, n):
                    emit(
                        "start",
                        "LLM response · pass " + phase,
                        input={
                            "model": model,
                            "prompt": batch[0],
                            "temperature": temperature,
                            "n": n,
                        },
                    )
                    try:
                        response = ask_bounded(chatgpt, model, batch, temperature, n)
                    except Exception as error:
                        emit(
                            "error",
                            "LLM response · pass " + phase,
                            output=str(error),
                            elapsed=monotonic() - started,
                        )
                        raise
                    emit(
                        "finish",
                        "LLM response · pass " + phase,
                        output=response,
                        elapsed=monotonic() - started,
                    )
                    return response

                chatgpt.ask_llm = ask
                try:
                    runpy.run_path(argv[1], run_name="__main__")
                finally:
                    chatgpt.ask_llm = original_ask
                model = os.environ["LLM_MODEL"].replace("/", "_").replace("\\", "_")
                sql = (
                    (Path(argv[-1]) / f"RESULTS_MODEL-{model}.txt").read_text().strip()
                )
                emit("finish", stage, output=sql, elapsed=monotonic() - started)
            else:
                reused = preprocess(argv[1], source, repo, output)
                emit(
                    "finish",
                    stage,
                    output={
                        "examples": 1,
                        "training_cache_reused": reused,
                        "training_data": "Spider train + train_others",
                    },
                    elapsed=monotonic() - started,
                )
        except Exception as error:
            emit("error", stage, output=str(error), elapsed=monotonic() - started)
            raise

    comparison.command = command
    try:
        comparison.dail()
        lines = comparison.raw("dail_sql").read_text().splitlines()
        if len(lines) != 1 or not lines[0].strip():
            raise ValueError("DAIL returned no SQL for the live input")
        return lines[0]
    finally:
        os.chdir(original_cwd)
        sys.argv = original_argv

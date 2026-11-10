"""Local dashboard API: original runners, persisted traces and resumable SSE."""

import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "downloads/spider_data"
RUNS = Path(os.environ.get("SQL_LAB_RUNS_DIR", str(ROOT / "results/live")))
REPOS = {
    "din_sql": "Few-shot-NL2SQL-with-prompting",
    "mac_sql": "MAC-SQL",
    "dail_sql": "DAIL-SQL",
    "codex_mcp": "codex-mcp-sql",
}
LOCK = threading.RLock()
ACTIVE = {}
ON_UPDATE = None


def environment():
    env = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env.setdefault(key.strip(), value.strip().strip("\"'"))
    env.setdefault("LLM_MODEL", "cx/gpt-6-luna")
    env.setdefault("CODEX_MODEL", "gpt-6-luna")
    env.setdefault("NLTK_DATA", "/private/tmp/text2sql-nltk")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def dail_missing_resources(env):
    """Report required local resources without importing the heavyweight runtime."""
    repo = ROOT.parent / REPOS["dail_sql"]
    java_candidates = sorted((repo / "third_party/java11").glob("jdk*/Contents/Home"))
    java = Path(
        env.get("JAVA_HOME")
        or (
            str(java_candidates[-1])
            if java_candidates
            else str(repo / "third_party/java11/missing")
        )
    )
    core = Path(
        env.get("CORENLP_HOME")
        or str(repo / "third_party/stanford-corenlp-full-2018-10-05")
    )
    missing = []
    if not (java / "bin/java").is_file():
        missing.append("Java 11 (JAVA_HOME)")
    if not list(core.glob("stanford-corenlp-*.jar")) or not list(
        core.glob("stanford-corenlp-*-models.jar")
    ):
        missing.append("Stanford CoreNLP (CORENLP_HOME)")
    for name in (
        "train_spider.json",
        "train_others.json",
        "train_gold.sql",
        "tables.json",
    ):
        if not (DATA / name).is_file():
            missing.append(name)
    return missing


def redact(value):
    text = json.dumps(value, ensure_ascii=False, default=str)
    for name in ("LLM_API_KEY", "OPENAI_API_KEY", "CODEX_API_KEY"):
        secret = environment().get(name)
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return json.loads(text)


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def database(db_id):
    if not isinstance(db_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", db_id):
        raise ValueError("Invalid database ID")
    path = (DATA / "database" / db_id / (db_id + ".sqlite")).resolve()
    if not path.is_relative_to((DATA / "database").resolve()) or not path.is_file():
        raise ValueError("Database not installed")
    return path


def query_result(path, sql):
    """Bounded, read-only execution for the result inspector."""
    start = time.monotonic()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        connection.set_progress_handler(lambda: int(time.monotonic() - start > 5), 1000)
        cursor = connection.execute(sql)
        rows = cursor.fetchmany(101)
        return {
            "columns": [c[0] for c in cursor.description or []],
            "rows": rows[:100],
            "truncated": len(rows) > 100,
        }


def schema(db_id):
    with sqlite3.connect(database(db_id).as_uri() + "?mode=ro", uri=True) as connection:
        return [
            {"name": name, "ddl": ddl}
            for name, ddl in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]


def run_path(run_id):
    if not re.fullmatch(r"[a-f0-9]{12}", run_id):
        raise ValueError("Invalid run ID")
    path = RUNS / run_id
    if not (path / "run.json").exists():
        raise ValueError("Run not found")
    return path


def events(path):
    found = []
    for file in path.glob("*/events.jsonl"):
        for line in file.read_text().splitlines():
            try:
                found.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # Writer may currently be appending the final line.
    return sorted(found, key=lambda event: event["time"])


def append(path, method, kind, stage, **data):
    with (path / method / "events.jsonl").open("a") as stream:
        stream.write(
            json.dumps(
                redact(
                    dict(
                        time=time.time(), method=method, kind=kind, stage=stage, **data
                    )
                )
            )
            + "\n"
        )


def execute_run(path, request, cancel):
    meta = json.loads((path / "run.json").read_text())
    env = environment()
    terminal = "completed"
    try:
        for method in request["methods"]:
            if cancel.is_set():
                terminal = "cancelled"
                break
            directory = path / method
            directory.mkdir()
            save(directory / "request.json", request)
            python = ROOT.parent / REPOS[method] / ".venv/bin/python"
            append(
                path,
                method,
                "queued",
                "Starting runner",
                input={
                    "model": env[
                        "CODEX_MODEL" if method == "codex_mcp" else "LLM_MODEL"
                    ]
                },
            )
            with (directory / "process.log").open("w") as log:
                process = subprocess.Popen(
                    [
                        str(python),
                        str(ROOT / "scripts/live_worker.py"),
                        "--request",
                        str(directory / "request.json"),
                        "--method",
                        method,
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                with LOCK:
                    ACTIVE[path.name]["process"] = process
                deadline = time.monotonic() + (1800 if method == "dail_sql" else 600)
                timed_out = False
                while process.poll() is None:
                    if cancel.wait(0.15) or time.monotonic() > deadline:
                        timed_out = not cancel.is_set()
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        try:
                            process.wait(5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                        break
                process.wait()
                with LOCK:
                    ACTIVE[path.name]["process"] = None
            # Original runners own stdout; sanitize their local diagnostic log
            # as well as the structured events returned to the browser.
            process_log = directory / "process.log"
            process_log.write_text(redact(process_log.read_text(errors="replace")))
            method_events = [e for e in events(path) if e["method"] == method]
            results = [e for e in method_events if e["kind"] == "result"]
            if cancel.is_set():
                append(
                    path, method, "failed", "Cancelled", output="Run cancelled by user"
                )
                terminal = "cancelled"
                break
            if process.returncode or not results:
                terminal = "partial_failure"
                if not any(e["kind"] == "failed" for e in method_events):
                    append(
                        path,
                        method,
                        "failed",
                        "Runner failed",
                        output="Runner timed out"
                        if timed_out
                        else "Runner exited before returning SQL. Check local process.log and setup instructions.",
                    )
                continue
            sql = results[-1]["output"]
            append(path, method, "start", "SQLite execution", input=sql)
            try:
                output = query_result(database(request["db_id"]), sql)
                # Score only an unchanged, selected Spider example. Custom input
                # has no reference answer and is never labelled correct.
                index = request.get("example_index")
                if index is not None:
                    gold = json.loads((DATA / "dev.json").read_text())[index]
                    # Use the same SQLite EX rules as the comparison CLI.
                    output["evaluation"] = score_sql(
                        database(request["db_id"]), sql, gold["query"]
                    )
                append(path, method, "finish", "SQLite execution", output=output)
            except Exception as error:  # noqa: BLE001 - surface adapter/SQLite failures to UI
                append(path, method, "error", "SQLite execution", output=str(error))
                terminal = "partial_failure"
    except Exception as error:  # noqa: BLE001 - terminate saved run on any worker failure
        terminal = "failed"
        meta["error"] = redact(str(error))
    finally:
        meta.update(status=terminal, finished_at=time.time())
        try:
            save_meta(path, meta)
        finally:
            # A PostgreSQL outage must not permanently occupy the runner slot.
            with LOCK:
                ACTIVE.pop(path.name, None)


def score_sql(path, predicted, gold):
    sys.path.insert(0, str(ROOT / "scripts"))
    from sqlite_eval import execute, order_matters, result_eq

    gold_rows, gold_width = execute(path, gold, 5)
    predicted_rows, predicted_width = execute(path, predicted, 5)
    return {
        "correct": gold_width == predicted_width
        and result_eq(gold_rows, predicted_rows, order_matters(gold)),
        "metric": "SQLite EX",
        "gold_sql": gold,
    }


def save_meta(path, meta):
    save(path / "run.json", meta)
    if ON_UPDATE is not None:
        ON_UPDATE(meta)


def shutdown():
    with LOCK:
        states = list(ACTIVE.values())
        for state in states:
            state["cancel"].set()
    for state in states:
        thread = state.get("thread")
        if thread is not None:
            thread.join(timeout=10)

"""Run a gold-free question through the original methods without an app server."""

import json
import os
import re
import sqlite3
import time
from contextlib import closing
from datetime import datetime
from uuid import uuid4

from common import ROOT, read_json
from run_comparison import REPOS, Comparison


def preview(database, sql):
    deadline = time.monotonic() + 5
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.text_factory = lambda raw: raw.decode("utf-8", errors="replace")
        conn.execute("PRAGMA query_only = ON")
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        cursor = conn.execute(sql)
        if cursor.description is None:
            raise ValueError("SQL must return a result set")
        rows = cursor.fetchmany(101)
        return {
            "columns": [column[0] for column in cursor.description],
            "rows": rows[:100],
            "truncated": len(rows) > 100,
        }


def run(args):
    if args.question is None or args.db_id is None or not args.question.strip():
        raise ValueError("Provide a nonempty --question together with --db-id")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.db_id):
        raise ValueError("Invalid --db-id")
    for name in ("data_dir", "evaluate_only", "resume"):
        if getattr(args, name):
            raise ValueError(
                f"--question cannot be combined with --{name.replace('_', '-')}"
            )
    if args.count is not None:
        raise ValueError("--question cannot be combined with --count")
    if args.workers != 1:
        raise ValueError("--question runs one question; --workers must be 1")
    if len(set(args.methods)) != len(args.methods):
        raise ValueError("--methods must not contain duplicates")
    source = args.spider_data.resolve()
    database = source / "database" / args.db_id / (args.db_id + ".sqlite")
    if not database.is_file():
        raise FileNotFoundError(database)
    if not any(row["db_id"] == args.db_id for row in read_json(source / "tables.json")):
        raise ValueError(f"Database missing from tables.json: {args.db_id}")
    output = (
        args.output
        or ROOT
        / "results"
        / ("custom-" + datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8])
    ).resolve()
    if output.exists():
        raise FileExistsError(f"Existing output: {output}; choose another --output")
    env = dict(os.environ)
    if args.codex_model:
        env["CODEX_MODEL"] = args.codex_model
    if not args.dry_run:
        if "codex_mcp" in args.methods and not env.get("CODEX_MODEL"):
            raise ValueError("Set --codex-model or CODEX_MODEL for codex_mcp")
        if any(method != "codex_mcp" for method in args.methods):
            for key in ("LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL"):
                if not env.get(key):
                    raise ValueError(f"Set {key} by sourcing .env first")
        for method in args.methods:
            python = ROOT.parent / REPOS[method] / ".venv/bin/python"
            if not python.is_file():
                raise FileNotFoundError(python)
    request = {
        "question": args.question,
        "db_id": args.db_id,
        "spider_data": str(source),
        "reasoning_effort": args.codex_reasoning_effort,
    }
    print(
        f"Question: {args.question}\nDatabase: {args.db_id}\nOutput: {output}",
        flush=True,
    )
    print("Custom question: reference scores are unavailable.", flush=True)
    comparison = Comparison.__new__(Comparison)
    comparison.args, comparison.env = args, env
    results = {}
    for method in args.methods:
        directory = output / method
        if not args.dry_run:
            directory.mkdir(parents=True)
            (directory / "request.json").write_text(
                json.dumps(request, ensure_ascii=False)
            )
        comparison.command(
            [
                ROOT.parent / REPOS[method] / ".venv/bin/python",
                ROOT / "scripts/live_worker.py",
                "--request",
                directory / "request.json",
                "--method",
                "din_sql" if method == "few_shot" else method,
            ],
            log=directory / "process.log",
        )
        if args.dry_run:
            continue
        events = [
            json.loads(line)
            for line in (directory / "events.jsonl").read_text().splitlines()
        ]
        sql = next(
            (
                event["output"]
                for event in reversed(events)
                if event["kind"] == "result"
            ),
            None,
        )
        if not sql:
            raise RuntimeError(f"No SQL returned; see {directory / 'process.log'}")
        result = {"sql": sql}
        try:
            result.update(preview(database, sql))
        except (sqlite3.Error, ValueError) as error:
            result["execution_error"] = str(error)
        results[method] = result
        (directory / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, default=str, indent=2)
        )
        (output / "results.json").write_text(
            json.dumps(results, ensure_ascii=False, default=str, indent=2)
        )
        print(
            f"{method}: {sql}\n{json.dumps(result, ensure_ascii=False, default=str)}",
            flush=True,
        )

"""Apply unmodified BIRD mini-dev R-VES functions to saved Spider predictions."""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from common import ROOT, examples, read_json, sql_line, write_json
from evaluate import validate_predictions, write_csv

METHODS = ("few_shot", "mac_sql", "dail_sql", "codex_mcp")


def load_bird(bird_root):
    source = bird_root.resolve() / "evaluation/evaluation_ves.py"
    sys.path.insert(0, str(source.parent))
    spec = importlib.util.spec_from_file_location("bird_mini_dev_rves", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def measure(bird, prediction, gold, database, index, iterations, timeout):
    """Observe upstream calls without changing results, timings or reward logic."""
    execute_sql = bird.execute_sql
    checks, timings, errors = [], [], []

    def record_sql(*args, **kwargs):
        try:
            result = execute_sql(*args, **kwargs)
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
            raise
        if kwargs.get("return_time", False):
            timings.append(result)
        else:
            checks.append(set(result))
        return result

    bird.execute_sql = record_sql
    started = time.monotonic()
    try:
        result = bird.execute_model(
            prediction, gold, str(database), index, iterations, timeout, "SQLite"
        )
    finally:
        bird.execute_sql = execute_sql
    elapsed = time.monotonic() - started
    valid = len(checks) == 2 and checks[0] == checks[1]
    ratios = [g / p for p, g in zip(timings[::2], timings[1::2]) if p > 0]
    filtered = bird.clean_abnormal(ratios) if ratios else []
    if result["reward"] > 0:
        status = "reward_positive"
    elif errors:
        status = "query_error"
    elif elapsed >= timeout * iterations:
        status = "timeout"
    elif not valid:
        status = "result_mismatch"
    elif not filtered:
        status = "empty_outlier_filter"
    else:
        status = "upstream_zero_reward"
    return dict(
        **result,
        valid_set_match=valid,
        status=status,
        errors=errors,
        elapsed_seconds=elapsed,
        measured_pairs=len(ratios),
        filtered_pairs=len(filtered),
        mean_filtered_time_ratio=sum(filtered) / len(filtered) if filtered else None,
        predicted_times_seconds=timings[::2],
        gold_times_seconds=timings[1::2],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bird-root", type=Path, default=ROOT.parent / "BIRD-mini-dev")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/bird_rves_full_dev"
    )
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--meta-timeout", type=float, default=3.0)
    parser.add_argument("--count", type=int)
    args = parser.parse_args()
    if (
        args.iterations < 2
        or args.meta_timeout <= 0
        or (args.count is not None and args.count < 1)
    ):
        parser.error("Need iterations >= 2, positive timeout/count")
    # Keep timing single-worker and avoid unrelated BLAS threads.
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    bird = load_bird(args.bird_root)
    rows = examples(ROOT / "data/dev_full/examples.json")
    if read_json(ROOT / "data/dev_full/subset.json") != [r["example_id"] for r in rows]:
        raise ValueError("Subset order differs from examples")
    rows = rows[: args.count] if args.count else rows
    sources = {m: ROOT / f"results/full_dev/predictions/{m}.jsonl" for m in METHODS}
    sources["codex_mcp"] = ROOT / "results/codex_full_dev/predictions/codex_mcp.jsonl"
    all_rows = examples(ROOT / "data/dev_full/examples.json")
    predictions = {
        m: validate_predictions(sources[m], all_rows)[: len(rows)] for m in args.methods
    }
    db_root = ROOT / "downloads/spider_data/database"
    metadata = read_json(ROOT / "data/dev_full/source.json")
    for db in {r["db_id"] for r in rows}:
        path = db_root / db / f"{db}.sqlite"
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != metadata["databases_sha256"][db]
        ):
            raise ValueError(f"Database checksum differs: {db}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset": "Spider 1.0 dev",
        "examples": len(rows),
        "metric": "BIRD mini-dev R-VES",
        "bird_commit": subprocess.check_output(
            ["git", "-C", str(args.bird_root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_sha256": hashlib.sha256(
            (args.bird_root / "evaluation/evaluation_ves.py").read_bytes()
        ).hexdigest(),
        "iterations": args.iterations,
        "meta_timeout": args.meta_timeout,
        "per_query_budget_seconds": args.meta_timeout * args.iterations,
        "workers": 1,
        "full_passes": 1,
        "method_order": args.methods,
        "python": sys.version,
        "sqlite": sqlite3.sqlite_version,
        "platform": platform.platform(),
        "load_average_start": os.getloadavg(),
        "dependencies": {
            name: version(name)
            for name in ("numpy", "func-timeout", "psycopg2-binary", "PyMySQL")
        },
        "sources": {
            m: {
                "path": str(sources[m]),
                "sha256": hashlib.sha256(sources[m].read_bytes()).hexdigest(),
            }
            for m in args.methods
        },
        "source_json_sha256": hashlib.sha256(
            (ROOT / "data/dev_full/source.json").read_bytes()
        ).hexdigest(),
    }
    write_json(output / "manifest.json", manifest)
    (output / "gold.txt").write_text(
        "".join(sql_line(r["query"]) + "\t" + r["db_id"] + "\n" for r in rows),
        encoding="utf-8",
    )
    # Keep Spider's four difficulty labels, never relabel them as BIRD levels.
    sys.path.insert(0, str(ROOT.parent / "spider"))
    from evaluation import Evaluator, Schema, get_schema, get_sql

    schemas = {
        db: Schema(get_schema(str(db_root / db / f"{db}.sqlite")))
        for db in {row["db_id"] for row in rows}
    }
    difficulty = {
        row["example_id"]: Evaluator().eval_hardness(
            get_sql(schemas[row["db_id"]], row["query"])
        )
        for row in rows
    }
    summary, breakdown = [], []
    for method in args.methods:
        write_json(
            output / f"{method}.bird_input.json",
            {
                str(i): record["predicted_sql"]
                + "\t----- bird -----\t"
                + record["db_id"]
                for i, record in enumerate(predictions[method])
            },
        )
        details = []
        with (output / f"{method}.details.jsonl").open("w", encoding="utf-8") as stream:
            for i, (row, pred) in enumerate(zip(rows, predictions[method])):
                result = measure(
                    bird,
                    pred["predicted_sql"],
                    row["query"],
                    db_root / row["db_id"] / f"{row['db_id']}.sqlite",
                    i,
                    args.iterations,
                    args.meta_timeout,
                )
                result.update(
                    example_id=row["example_id"],
                    db_id=row["db_id"],
                    difficulty=difficulty[row["example_id"]],
                )
                details.append(result)
                stream.write(json.dumps(result) + "\n")
                stream.flush()
                if (i + 1) % 100 == 0 or i + 1 == len(rows):
                    print(
                        f"{method}: {i + 1}/{len(rows)}, R-VES={bird.compute_ves(details):.4f}",
                        flush=True,
                    )
        write_json(output / f"{method}.details.json", details)
        for level in ("all", "easy", "medium", "hard", "extra"):
            subset = [d for d in details if level == "all" or d["difficulty"] == level]
            if not subset:
                continue
            counts = Counter(d["status"] for d in subset)
            score = {
                "method": method,
                "difficulty": level,
                "R_VES": bird.compute_ves(subset),
                "evaluated_examples": len(subset),
                "valid_set_matches": sum(d["valid_set_match"] for d in subset),
                "reward_positive": counts["reward_positive"],
                "query_errors": counts["query_error"],
                "timeouts": counts["timeout"],
                "empty_filters": counts["empty_outlier_filter"],
            }
            breakdown.append(score)
            if level == "all":
                summary.append({k: v for k, v in score.items() if k != "difficulty"})
        write_csv(output / "summary.csv", list(summary[0]), summary)
        write_csv(output / "by_difficulty.csv", list(breakdown[0]), breakdown)
    manifest["load_average_end"] = os.getloadavg()
    write_json(output / "manifest.json", manifest)


if __name__ == "__main__":
    main()

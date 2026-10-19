"""Validate alignment and invoke the unchanged official Spider EX evaluator."""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from common import ROOT, examples, read_json, sql_line

# Spider drops empty lines, so use invalid SQL to preserve the denominator.
INVALID_SQL = "__MISSING_PREDICTION__"


def validate_predictions(path, rows):
    records = [
        json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
    ]
    if len(records) != len(rows):
        raise ValueError(
            f"{path}: expected {len(rows)} predictions, got {len(records)}"
        )
    for index, (prediction, row) in enumerate(zip(records, rows)):
        for key in ("example_id", "db_id", "question"):
            if prediction.get(key) != row[key]:
                raise ValueError(f"{path}: {key} mismatch at position {index}")
        if not isinstance(prediction.get("predicted_sql"), str):
            raise ValueError(
                f"{path}: predicted_sql must be a string at position {index}"
            )
    return records


def parse_scores(stdout, expected_count):
    count = re.search(
        r"^count\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", stdout, re.M
    )
    score = re.search(
        r"^execution\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$",
        stdout,
        re.M,
    )
    if not count or int(count.group(5)) != expected_count or not score:
        raise ValueError(
            "Spider did not report the expected overall execution score/count; inspect evaluator log"
        )
    value = float(score.group(5))
    if not 0 <= value <= 1:
        raise ValueError("Invalid Spider EX score")
    return value


def evaluate(args):
    rows = examples(args.examples)
    if read_json(args.subset) != [r["example_id"] for r in rows]:
        raise ValueError("Subset IDs/order do not match examples.json")
    evaluator = args.spider_root.resolve() / "evaluation.py"
    if not evaluator.is_file() or not args.table.is_file():
        raise FileNotFoundError("Missing official evaluator or tables.json")
    schemas = {r["db_id"] for r in read_json(args.table)}
    for row in rows:
        database = args.db / row["db_id"] / (row["db_id"] + ".sqlite")
        if not database.is_file() or row["db_id"] not in schemas:
            raise FileNotFoundError(f"Missing schema/database: {database}")
    metadata_path = args.examples.parent / "source.json"
    if metadata_path.is_file():
        metadata = read_json(metadata_path)
        if (
            hashlib.sha256(args.table.read_bytes()).hexdigest()
            != metadata["tables_sha256"]
        ):
            raise ValueError("Evaluation tables.json differs from the prepared dataset")
        for db in {row["db_id"] for row in rows}:
            database = args.db / db / (db + ".sqlite")
            if (
                hashlib.sha256(database.read_bytes()).hexdigest()
                != metadata["databases_sha256"][db]
            ):
                raise ValueError(
                    f"Evaluation database differs from the prepared dataset: {db}"
                )
    inputs = []
    methods = set()
    for specification in args.prediction:
        method, separator, path = specification.partition("=")
        if (
            not separator
            or not re.fullmatch(r"[a-zA-Z0-9_-]+", method)
            or method in methods
        ):
            raise ValueError("Use unique --prediction method=/path/to/file.jsonl")
        methods.add(method)
        inputs.append((method, validate_predictions(path, rows)))
    args.work_dir.mkdir(parents=True, exist_ok=True)
    gold = args.work_dir / "gold.txt"
    gold.write_text(
        "".join(sql_line(r["query"]) + "\t" + r["db_id"] + "\n" for r in rows),
        encoding="utf-8",
    )
    scores = []
    for method, predictions in inputs:
        pred = args.work_dir / f"{method}.txt"
        pred.write_text(
            "".join(
                (sql_line(r["predicted_sql"]) or INVALID_SQL) + "\n"
                for r in predictions
            ),
            encoding="utf-8",
        )
        command = [
            args.python,
            str(evaluator),
            "--gold",
            str(gold.resolve()),
            "--pred",
            str(pred.resolve()),
            "--etype",
            "exec",
            "--db",
            str(args.db.resolve()),
            "--table",
            str(args.table.resolve()),
        ]
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout,
        )
        (args.work_dir / f"{method}.log").write_text(result.stdout, encoding="utf-8")
        (args.work_dir / f"{method}.command.json").write_text(
            json.dumps(command, indent=2) + "\n", encoding="utf-8"
        )
        if result.returncode:
            raise RuntimeError(
                f"Spider failed for {method}: see {args.work_dir / (method + '.log')}"
            )
        score = parse_scores(result.stdout, len(rows))
        scores.append(
            dict(
                method=method,
                EX=score,
                evaluated_examples=len(rows),
                empty_predictions=sum(
                    not r["predicted_sql"].strip() for r in predictions
                ),
            )
        )
        print(f"{method}: EX={score:.3f}, n={len(rows)}")
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically only after every requested method succeeded.
    temporary = args.summary.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["method", "EX", "evaluated_examples", "empty_predictions"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(scores)
    temporary.replace(args.summary)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--examples", type=Path, default=ROOT / "data/examples.json")
    p.add_argument("--subset", type=Path, default=ROOT / "data/subset.json")
    p.add_argument("--spider-root", type=Path, default=ROOT.parent / "spider")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--table", type=Path, required=True)
    p.add_argument(
        "--prediction",
        action="append",
        required=True,
        help="method=normalized.jsonl; repeat for each method",
    )
    p.add_argument(
        "--python", default=sys.executable, help="Python with nltk for Spider"
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Evaluator timeout per method in seconds",
    )
    p.add_argument("--work-dir", type=Path, default=ROOT / "results/evaluation")
    p.add_argument("--summary", type=Path, default=ROOT / "results/summary.csv")
    evaluate(p.parse_args())

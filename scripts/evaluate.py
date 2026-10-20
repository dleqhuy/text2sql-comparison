"""Validate alignment and score with original Spider or direct SQLite execution."""

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
LEVELS = ("easy", "medium", "hard", "extra", "all")


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
    if not count or not score:
        raise ValueError(
            "Spider did not report execution scores/counts; inspect evaluator log"
        )
    counts = [int(value) for value in count.groups()]
    values = [float(value) for value in score.groups()]
    if counts[-1] != expected_count or sum(counts[:-1]) != expected_count:
        raise ValueError("Spider difficulty counts do not match the subset size")
    if any(not 0 <= value <= 1 for value in values):
        raise ValueError("Invalid Spider EX score")
    return {
        level: dict(EX=value if size else None, evaluated_examples=size)
        for level, size, value in zip(LEVELS, counts, values)
    }


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_report(path, scores, breakdown, backend="spider"):
    first = scores[0]["method"]
    counts = {
        row["difficulty"]: row["evaluated_examples"]
        for row in breakdown
        if row["method"] == first
    }
    order = ("all", *LEVELS[:-1])
    headers = [f"{level} (n={counts[level]})" for level in order]
    lines = [
        "# EX theo độ khó",
        "",
        "Độ khó được lấy từ evaluator Spider gốc, dựa trên gold SQL.",
        "EX được lấy từ đầu ra evaluator, làm tròn đến 3 chữ số thập phân.",
        "",
        "| Method | " + " | ".join(headers) + " |",
        "|---|" + "---:|" * len(order),
    ]
    for result in scores:
        method = result["method"]
        values = {
            row["difficulty"]: row["EX"] for row in breakdown if row["method"] == method
        }
        cells = [
            "—" if values[level] is None else f"{values[level]:.1%}" for level in order
        ]
        lines.append("| " + method + " | " + " | ".join(cells) + " |")
    lines += ["", "`—`: không có câu ở độ khó này, không phải EX bằng 0.", ""]
    if backend == "sqlite":
        lines[3] = (
            "Backend: SQLite, chấm trực tiếp trên một database cho mỗi câu; "
            "không phải test-suite accuracy. Điểm dùng độ chính xác đầy đủ."
        )
        lines += [
            "Giữ DISTINCT và số dòng trùng; cho phép hoán vị cột nhất quán; "
            "chỉ bắt buộc thứ tự dòng khi gold có ORDER BY ngoài cùng. "
            "Không thay giá trị dự đoán bằng giá trị gold.",
            "",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def evaluate(args):
    backend = getattr(args, "execution_backend", "spider")
    query_timeout = getattr(args, "query_timeout", 10)
    if query_timeout <= 0:
        raise ValueError("--query-timeout must be positive")
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
    breakdown = []
    difficulty_counts = None
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
        if backend == "sqlite":
            command = [
                args.python,
                str(Path(__file__).with_name("sqlite_eval.py")),
                "--gold",
                str(gold.resolve()),
                "--pred",
                str(pred.resolve()),
                "--db",
                str(args.db.resolve()),
                "--spider-root",
                str(args.spider_root.resolve()),
                "--details",
                str((args.work_dir / f"{method}.details.json").resolve()),
                "--query-timeout",
                str(query_timeout),
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
                f"{backend} evaluator failed for {method}: "
                f"see {args.work_dir / (method + '.log')}"
            )
        levels = parse_scores(result.stdout, len(rows))
        counts = [levels[level]["evaluated_examples"] for level in LEVELS]
        if difficulty_counts is not None and counts != difficulty_counts:
            raise ValueError("Spider difficulty counts differ between methods")
        difficulty_counts = counts
        breakdown.extend(
            dict(method=method, difficulty=level, **levels[level]) for level in LEVELS
        )
        score = levels["all"]["EX"]
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
    # Write reports only after every requested method succeeded.
    write_csv(
        args.summary,
        ["method", "EX", "evaluated_examples", "empty_predictions"],
        scores,
    )
    write_csv(
        args.difficulty_summary or args.summary.with_name("by_difficulty.csv"),
        ["method", "difficulty", "EX", "evaluated_examples"],
        breakdown,
    )
    write_report(
        args.report or args.summary.with_name("report.md"), scores, breakdown, backend
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--examples", type=Path, default=ROOT / "data/dev_full/examples.json"
    )
    p.add_argument("--subset", type=Path, default=ROOT / "data/dev_full/subset.json")
    p.add_argument("--spider-root", type=Path, default=ROOT.parent / "spider")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--table", type=Path, required=True)
    p.add_argument(
        "--execution-backend",
        choices=("spider", "sqlite"),
        default="spider",
        help="spider: original parser-based score; sqlite: direct single-database EX",
    )
    p.add_argument(
        "--query-timeout",
        type=float,
        default=10,
        help="SQLite backend deadline per query in seconds (default: 10)",
    )
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
    p.add_argument(
        "--work-dir", type=Path, default=ROOT / "results/full_dev/evaluation"
    )
    p.add_argument(
        "--summary", type=Path, default=ROOT / "results/full_dev/summary.csv"
    )
    p.add_argument(
        "--difficulty-summary",
        type=Path,
        help="Default: by_difficulty.csv beside summary",
    )
    p.add_argument("--report", type=Path, help="Default: report.md beside summary")
    evaluate(p.parse_args())

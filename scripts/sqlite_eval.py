"""SQLite execution scoring without parsing predictions with Spider's restricted AST.

Result comparison follows the bag/column permutation semantics of
https://github.com/taoyds/test-suite-sql-eval/blob/e97acc546ecbee8fa27fa8dbf025ef61493a876c/exec_eval.py.
The comparison is implemented locally with deterministic column constraints.
This evaluates one database per example, NOT a distilled test suite.
"""

import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import sys
import time

LEVELS = ("easy", "medium", "hard", "extra", "all")


def order_matters(sql):
    """Only an outer ORDER BY constrains the final result order."""
    tokens = re.findall(
        r"--[^\n\r]*|/\*.*?\*/|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\""
        r"|`(?:``|[^`])*`|\[[^\]]*\]|[A-Za-z_]+|[()]",
        sql,
        re.S,
    )
    depth = 0
    previous = None
    for token in tokens:
        if token == "(":
            depth += 1
            previous = None
        elif token == ")":
            depth -= 1
            previous = None
        elif token.startswith(("--", "/*")):
            continue
        elif depth == 0:
            word = token.upper()
            if previous == "ORDER" and word == "BY":
                return True
            previous = word
    return False


def result_eq(gold, predicted, ordered=False):
    """Match bags of rows under ONE consistent permutation of columns."""
    if len(gold) != len(predicted):
        return False
    if not gold:
        return True
    width = len(gold[0])
    if width != len(predicted[0]):
        return False
    if gold == predicted:
        return True
    expected = gold if ordered else Counter(gold)
    gold_columns = [Counter(row[i] for row in gold) for i in range(width)]
    pred_columns = [Counter(row[i] for row in predicted) for i in range(width)]
    candidates = [
        [j for j in range(width) if gold_columns[i] == pred_columns[j]]
        for i in range(width)
    ]
    if any(not choices for choices in candidates):
        return False
    positions = sorted(range(width), key=lambda i: len(candidates[i]))
    permutation = [None] * width

    def match(depth, used):
        if depth == width:
            transformed = [tuple(row[j] for j in permutation) for row in predicted]
            return (transformed if ordered else Counter(transformed)) == expected
        i = positions[depth]
        for j in candidates[i]:
            if j not in used:
                permutation[i] = j
                if match(depth + 1, used | {j}):
                    return True
        return False

    return match(0, set())


def execute(database, sql, timeout):
    """Run a single statement read-only, with a SQLite VM deadline."""
    deadline = time.monotonic() + timeout
    with closing(
        sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    ) as conn:
        # Match upstream test-suite decoding for malformed UTF-8 in Spider data.
        conn.text_factory = lambda raw: raw.decode("utf-8", errors="ignore")
        conn.execute("PRAGMA query_only = ON")
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        cursor = conn.execute(sql)
        if cursor.description is None:
            raise ValueError("Prediction must return a result set")
        return cursor.fetchall(), len(cursor.description)


def evaluate(args):
    # Only GOLD SQL is parsed, for the standard Spider difficulty labels.
    sys.path.insert(0, str(args.spider_root.resolve()))
    from evaluation import Evaluator, Schema, get_schema, get_sql

    with args.gold.open() as stream:
        gold = [line.strip().split("\t") for line in stream if line.strip()]
    predictions = args.pred.read_text().splitlines()
    if len(predictions) != len(gold):
        raise ValueError("Gold/prediction count mismatch")
    totals = Counter()
    correct = Counter()
    records = []
    schemas = {}
    for index, ((gold_sql, db_id), prediction) in enumerate(zip(gold, predictions)):
        database = args.db / db_id / (db_id + ".sqlite")
        if db_id not in schemas:
            schemas[db_id] = Schema(get_schema(str(database)))
        difficulty = Evaluator().eval_hardness(get_sql(schemas[db_id], gold_sql))
        # Gold errors invalidate the run; never silently count these as model errors.
        try:
            gold_rows, gold_width = execute(database, gold_sql, args.query_timeout)
        except Exception as error:
            raise RuntimeError(f"Gold execution failed at {index} ({db_id})") from error
        ordered = order_matters(gold_sql)
        error_text = None
        try:
            pred_rows, pred_width = execute(database, prediction, args.query_timeout)
            matched = gold_width == pred_width and result_eq(
                gold_rows, pred_rows, ordered
            )
        except (sqlite3.Error, sqlite3.Warning, ValueError) as error:
            matched = False
            error_text = f"{type(error).__name__}: {error}"
        for level in (difficulty, "all"):
            totals[level] += 1
            correct[level] += int(matched)
        records.append(
            dict(
                index=index,
                db_id=db_id,
                difficulty=difficulty,
                correct=matched,
                order_matters=ordered,
                prediction_error=error_text,
            )
        )
    # Persist the policy with every run so the metric cannot be mistaken for TSA.
    args.details.write_text(
        json.dumps(
            dict(
                backend="sqlite",
                metric="single_database_execution_accuracy",
                policy=dict(
                    preserve_duplicates=True,
                    allow_column_permutation=True,
                    row_order="gold_outer_order_by",
                    keep_distinct=True,
                    plug_values=False,
                    invalid_utf8="ignore (upstream test-suite policy)",
                    query_timeout=args.query_timeout,
                ),
                evaluated_examples=len(records),
                correct=correct["all"],
                EX=correct["all"] / len(records) if records else None,
                examples=records,
            ),
            indent=2,
        )
        + "\n"
    )
    print("count " + " ".join(str(totals[level]) for level in LEVELS))
    print(
        "execution "
        + " ".join(
            f"{correct[level] / totals[level]:.12f}" if totals[level] else "0.000"
            for level in LEVELS
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--spider-root", type=Path, required=True)
    parser.add_argument("--details", type=Path, required=True)
    parser.add_argument("--query-timeout", type=float, default=10)
    args = parser.parse_args()
    if args.query_timeout <= 0:
        parser.error("--query-timeout must be positive")
    evaluate(args)

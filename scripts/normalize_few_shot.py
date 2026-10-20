"""Normalize original DIN-SQL .txt output or its published CSV output."""

import argparse
import csv
from pathlib import Path
from common import ROOT, examples, write_predictions


def normalize(raw, rows):
    raw = Path(raw)
    if raw.suffix.lower() == ".csv":
        with raw.open(encoding="utf-8-sig", newline="") as stream:
            records = list(csv.DictReader(stream))
        if len(records) != len(rows):
            raise ValueError("Positional CSV must have exactly one row per example")
        for record, row in zip(records, rows):
            if (
                record.get("NLQ") != row["question"]
                or record.get("DATABASE") != row["db_id"]
            ):
                raise ValueError("CSV question/database does not match subset order")
        return [r["PREDICTED SQL"] for r in records]
    # Blank lines are real failed predictions. Missing tail/middle lines are ambiguous.
    lines = raw.read_text(encoding="utf-8").splitlines()
    if len(lines) != len(rows):
        raise ValueError(
            "Positional SQL output must have exactly one line per example, including blank failures"
        )
    return lines


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument(
        "--examples", type=Path, default=ROOT / "data/dev_full/examples.json"
    )
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/full_dev/predictions/few_shot.jsonl",
    )
    a = p.parse_args()
    rows = examples(a.examples)
    write_predictions(rows, normalize(a.raw, rows), a.output)

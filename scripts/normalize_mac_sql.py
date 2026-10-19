"""Normalize MAC-SQL JSONL by local idx; retain skipped examples as empty SQL."""

import argparse
import json
from pathlib import Path
from common import ROOT, examples, write_predictions


def normalize(raw, rows):
    predictions = [""] * len(rows)
    seen = set()
    for line in Path(raw).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        index = record["idx"]
        if type(index) is not int or not 0 <= index < len(rows) or index in seen:
            raise ValueError(f"Duplicate or out-of-range MAC-SQL idx: {index}")
        seen.add(index)
        if (
            record["db_id"] != rows[index]["db_id"]
            or record["query"] != rows[index]["question"]
        ):
            raise ValueError(f"MAC-SQL identity mismatch at idx {index}")
        value = record.get("pred")
        predictions[index] = "" if value is None else value
    return predictions


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--examples", type=Path, default=ROOT / "data/examples.json")
    p.add_argument(
        "--output", type=Path, default=ROOT / "results/predictions/mac_sql.jsonl"
    )
    a = p.parse_args()
    rows = examples(a.examples)
    write_predictions(rows, normalize(a.raw, rows), a.output)

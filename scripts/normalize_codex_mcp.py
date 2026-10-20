"""Validate Codex predictions against the shared subset and normalize SQL."""

import argparse
from pathlib import Path

from common import ROOT, examples, write_predictions
from evaluate import validate_predictions


def normalize(raw, rows):
    return [r["predicted_sql"] for r in validate_predictions(raw, rows)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument(
        "--examples", type=Path, default=ROOT / "data/dev_full/examples.json"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/full_dev/predictions/codex_mcp.jsonl",
    )
    args = parser.parse_args()
    rows = examples(args.examples)
    write_predictions(rows, normalize(args.raw, rows), args.output)

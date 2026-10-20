"""Normalize the original DAIL-SQL RESULTS_MODEL-*.txt file (same subset order)."""

import argparse
from pathlib import Path
from common import ROOT, examples, write_predictions
from normalize_few_shot import normalize

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument(
        "--examples", type=Path, default=ROOT / "data/dev_full/examples.json"
    )
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/full_dev/predictions/dail_sql.jsonl",
    )
    a = p.parse_args()
    if a.raw.suffix.lower() == ".csv":
        p.error("DAIL-SQL expects its original plain-text SQL output")
    rows = examples(a.examples)
    write_predictions(rows, normalize(a.raw, rows), a.output)

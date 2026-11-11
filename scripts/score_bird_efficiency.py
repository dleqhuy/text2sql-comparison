"""Score VES/R-VES from saved raw timings or committed per-example evidence."""

import argparse
import csv
import hashlib
import math
from collections import Counter
from pathlib import Path

from common import ROOT, read_json, write_json
from evaluate import write_csv
from evaluate_bird_rves import METHODS, compute_original_ves, load_bird

EVIDENCE_FIELDS = (
    "method",
    "sql_idx",
    "example_id",
    "db_id",
    "difficulty",
    "status",
    "valid_set_match",
    "measured_pairs",
    "filtered_pairs",
    "mean_filtered_time_ratio",
    "reward",
)


def recompute_timing(bird, record, iterations):
    """Validate successful measurements and both upstream reward and mean ratio."""
    if record["status"] != "reward_positive":
        if record["reward"] != 0:
            raise ValueError("Failed measurement must have zero reward")
        return
    p, g = record["predicted_times_seconds"], record["gold_times_seconds"]
    if len(p) != iterations or len(g) != iterations or not record["valid_set_match"]:
        raise ValueError("Successful measurement has missing timings or invalid result")
    if not all(math.isfinite(t) and t > 0 for t in p + g):
        raise ValueError("Invalid timing sample")
    filtered = bird.clean_abnormal([gt / pred for pred, gt in zip(p, g)])
    ratio = sum(filtered) / len(filtered)
    if not math.isclose(ratio, record["mean_filtered_time_ratio"], rel_tol=1e-12):
        raise ValueError("Saved mean ratio differs from raw timing pairs")
    if (
        len(filtered) != record["filtered_pairs"]
        or record["measured_pairs"] != iterations
    ):
        raise ValueError("Timing counts differ")
    reward = (
        1.25
        if ratio >= 2
        else 1
        if ratio >= 1
        else 0.75
        if ratio >= 0.5
        else 0.5
        if ratio >= 0.25
        else 0.25
    )
    if reward != record["reward"]:
        raise ValueError("Saved R-VES reward differs from raw timing pairs")


def summarize(records):
    summary, breakdown = [], []
    for method in METHODS:
        method_records = [r for r in records if r["method"] == method]
        if not method_records:
            raise ValueError(f"Missing method: {method}")
        if [r["sql_idx"] for r in method_records] != list(range(len(method_records))):
            raise ValueError("Missing, duplicate or reordered records")
        for level in ("all", "easy", "medium", "hard", "extra"):
            subset = [
                r for r in method_records if level == "all" or r["difficulty"] == level
            ]
            if not subset:
                continue
            counts = Counter(r["status"] for r in subset)
            # Preserve the upstream addition order across Python versions.
            rves_total = 0.0
            for record in subset:
                rves_total += math.sqrt(record["reward"]) * 100
            result = {
                "method": method,
                "difficulty": level,
                "R_VES": rves_total / len(subset),
                "VES": compute_original_ves(subset),
                "evaluated_examples": len(subset),
                "valid_set_matches": sum(r["valid_set_match"] for r in subset),
                "reward_positive": counts["reward_positive"],
                "query_errors": counts["query_error"],
                "timeouts": counts["timeout"],
                "empty_filters": counts["empty_outlier_filter"],
            }
            breakdown.append(result)
            if level == "all":
                summary.append({k: v for k, v in result.items() if k != "difficulty"})
    identities = [
        [
            (r["example_id"], r["db_id"], r["difficulty"])
            for r in records
            if r["method"] == m
        ]
        for m in METHODS
    ]
    if any(ids != identities[0] for ids in identities[1:]):
        raise ValueError("Methods have different example IDs, databases or difficulty")
    return summary, breakdown


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir", type=Path, default=ROOT / "results/bird_rves_full_dev"
    )
    parser.add_argument("--bird-root", type=Path, default=ROOT.parent / "BIRD-mini-dev")
    parser.add_argument(
        "--from-csv",
        action="store_true",
        help="Recompute from committed evidence; no raw logs or BIRD dependencies needed",
    )
    args = parser.parse_args()
    evidence = args.input_dir / "efficiency_per_example.csv"
    provenance_path = args.input_dir / "efficiency_provenance.json"
    records, raw_hashes = [], {}
    if args.from_csv:
        provenance = read_json(provenance_path)
        if (
            hashlib.sha256(evidence.read_bytes()).hexdigest()
            != provenance["evidence_sha256"]
        ):
            raise ValueError("Evidence checksum differs")
        with evidence.open() as stream:
            for row in csv.DictReader(stream):
                for key in ("sql_idx", "measured_pairs", "filtered_pairs"):
                    row[key] = int(row[key])
                row["valid_set_match"] = row["valid_set_match"] == "True"
                row["reward"] = float(row["reward"])
                row["mean_filtered_time_ratio"] = (
                    float(row["mean_filtered_time_ratio"])
                    if row["mean_filtered_time_ratio"]
                    else None
                )
                records.append(row)
    else:
        bird = load_bird(args.bird_root)
        manifest = read_json(args.input_dir / "manifest.json")
        source = args.bird_root / "evaluation/evaluation_ves.py"
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_sha256"]:
            raise ValueError("BIRD evaluator differs from the original measurement")
        for method in METHODS:
            path = args.input_dir / f"{method}.details.json"
            details = read_json(path)
            if len(details) != manifest["examples"]:
                raise ValueError("Incomplete measurement")
            raw_hashes[method] = hashlib.sha256(path.read_bytes()).hexdigest()
            for record in details:
                recompute_timing(bird, record, manifest["iterations"])
                record["method"] = method
                records.append({k: record[k] for k in EVIDENCE_FIELDS})
        provenance = {
            "dataset": manifest["dataset"],
            "examples_per_method": manifest["examples"],
            "timing_reused": True,
            "timing_scope": "Mini-Dev execute/fetch/close, excluding connection opening",
            "iterations": manifest["iterations"],
            "workers": manifest["workers"],
            "full_passes": manifest["full_passes"],
            "meta_timeout": manifest["meta_timeout"],
            "bird_commit": manifest["bird_commit"],
            "evaluator_sha256": manifest["source_sha256"],
            "python": manifest["python"],
            "sqlite": manifest["sqlite"],
            "platform": manifest["platform"],
            "prediction_sha256": {m: manifest["sources"][m]["sha256"] for m in METHODS},
            "raw_details_sha256": raw_hashes,
            "ves_formula": "100 * sum(sqrt(mean_filtered_time_ratio) for successful queries) / all_queries",
            "r_ves_formula": "100 * sum(sqrt(reward)) / all_queries",
        }
    summary, breakdown = summarize(records)
    # Check the existing R-VES results before replacing either summary file.
    with (args.input_dir / "summary.csv").open() as stream:
        previous = {r["method"]: float(r["R_VES"]) for r in csv.DictReader(stream)}
    if any(
        not math.isclose(r["R_VES"], previous[r["method"]], rel_tol=1e-12)
        for r in summary
    ):
        raise ValueError("R-VES changed; refusing to replace summary")
    if not args.from_csv:
        write_csv(evidence, EVIDENCE_FIELDS, records)
        provenance["evidence_sha256"] = hashlib.sha256(
            evidence.read_bytes()
        ).hexdigest()
        write_json(provenance_path, provenance)
    write_csv(args.input_dir / "summary.csv", list(summary[0]), summary)
    write_csv(args.input_dir / "by_difficulty.csv", list(breakdown[0]), breakdown)
    for row in summary:
        print(
            f"{row['method']}: VES={row['VES']:.4f}, R-VES={row['R_VES']:.4f}, n={row['evaluated_examples']}"
        )


if __name__ == "__main__":
    main()

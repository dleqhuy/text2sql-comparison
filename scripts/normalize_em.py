"""Normalize saved SQL, verify SQLite equivalence, then rerun Spider EM."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

import sqlglot
from common import ROOT, examples, read_json, write_json
from evaluate import validate_predictions, write_csv
from spider_normalize import normalize
from sqlite_eval import execute, order_matters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/em_normalized_full_dev"
    )
    args = parser.parse_args()
    rows = examples(ROOT / "data/dev_full/examples.json")
    sources = {
        method: ROOT / f"results/full_dev/predictions/{method}.jsonl"
        for method in ("few_shot", "mac_sql", "dail_sql")
    }
    sources["codex_mcp"] = ROOT / "results/codex_full_dev/predictions/codex_mcp.jsonl"
    db_root = ROOT / "downloads/spider_data/database"
    schemas = {}
    for entry in read_json(ROOT / "data/dev_full/tables.json"):
        schema = {name.lower(): [] for name in entry["table_names_original"]}
        for table_idx, name in entry["column_names_original"]:
            if table_idx >= 0:
                schema[entry["table_names_original"][table_idx].lower()].append(
                    name.lower()
                )
        schemas[entry["db_id"]] = schema
    output = args.output.resolve()
    pred_root = output / "predictions"
    pred_root.mkdir(parents=True, exist_ok=True)
    stats = []
    manifest = {
        "sqlglot": sqlglot.__version__,
        "sources": {},
        "normalizer_sha256": hashlib.sha256(
            Path(__file__).with_name("spider_normalize.py").read_bytes()
        ).hexdigest(),
    }
    for method, path in sources.items():
        records = validate_predictions(path, rows)
        audit = []
        for row, record in zip(rows, records):
            original = record["predicted_sql"]
            accepted = original
            candidate = None
            rules = {}
            status = "unchanged"
            error = None
            try:
                candidate, rules = normalize(original, schemas[row["db_id"]])
                if candidate != original:
                    database = db_root / row["db_id"] / f"{row['db_id']}.sqlite"
                    before, width_before = execute(database, original, 10)
                    after, width_after = execute(database, candidate, 10)
                    ordered = order_matters(original)
                    # Column positions must match; no permutation is allowed here.
                    equivalent = width_before == width_after and (
                        before == after
                        if ordered
                        else Counter(before) == Counter(after)
                    )
                    if not equivalent:
                        status = "rejected_result_difference"
                    else:
                        status = "accepted_verified"
                        accepted = candidate
            except (
                sqlglot.errors.SqlglotError,
                sqlite3.Error,
                ValueError,
                KeyError,
                TypeError,
            ) as exc:
                status = "retained_original_error"
                error = f"{type(exc).__name__}: {exc}"
            record["predicted_sql"] = accepted
            audit.append(
                {
                    "example_id": row["example_id"],
                    "db_id": row["db_id"],
                    "status": status,
                    "rules": rules,
                    "error": error,
                    "original_sql": original,
                    "candidate_sql": candidate,
                    "normalized_sql": accepted,
                }
            )
        (pred_root / f"{method}.jsonl").write_text(
            "".join(
                json.dumps(record, ensure_ascii=False) + "\n" for record in records
            ),
            encoding="utf-8",
        )
        write_json(output / f"{method}.normalization.json", audit)
        counts = Counter(item["status"] for item in audit)
        stats.append(
            {
                "method": method,
                "examples": len(records),
                "accepted_verified": counts["accepted_verified"],
                "unchanged": counts["unchanged"],
                "rejected_result_difference": counts["rejected_result_difference"],
                "retained_original_error": counts["retained_original_error"],
            }
        )
        manifest["sources"][method] = {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        print(method, dict(counts), flush=True)
    write_csv(output / "normalization_summary.csv", list(stats[0]), stats)
    write_json(output / "normalization_manifest.json", manifest)
    command = [
        sys.executable,
        str(Path(__file__).with_name("evaluate_em.py")),
        "--prediction-root",
        str(pred_root),
        "--output",
        str(output),
    ]
    write_json(output / "evaluation_command.json", command)
    subprocess.run(command, check=True)
    report = output / "report.md"
    text = report.read_text(encoding="utf-8")
    text += (
        "\n## Chuẩn hóa và kiểm tra\n\n"
        "Điểm này là EM sau chuẩn hóa prediction, khác với EM trên SQL gốc. "
        "Giữ nguyên gold và mã evaluator Spider. Chuẩn hóa không đọc gold SQL; "
        "dùng schema để xử lý identifier/alias. Không bỏ CAST, điều kiện NULL, "
        "DISTINCT, literal, không đổi outer join thành inner join.\n\n"
        "Chỉ nhận thay đổi khi SQL gốc và SQL mới thực thi SQLite có cùng số cột, "
        "cùng giá trị theo vị trí cột và số lần lặp của dòng; giữ thứ tự dòng khi "
        "có ORDER BY ngoài cùng. Không hoán vị cột. Alias nhãn cột ở đầu ra có thể "
        "được bỏ trong bản dành riêng cho EM; alias được scope khác sử dụng được giữ lại. "
        "Đối chiếu thực thi là kiểm tra trên database hiện có, không phải chứng minh "
        "tương đương trên mọi dữ liệu. Các quy tắc được kiểm thử thêm bằng dữ liệu nhân tạo.\n\n"
        "SQL bị lỗi/chênh kết quả khi kiểm tra sẽ giữ nguyên bản gốc. "
        "Prediction gốc và kết quả EM cũ không bị ghi đè. "
        "Xem `normalization_summary.csv` và `*.normalization.json` cho từng thay đổi.\n\n"
        "Chạy lại từ `text2sql/`:\n\n```bash\n"
        "NLTK_DATA=/tmp/text2sql-nltk text2sql-comparison/.venv/bin/python text2sql-comparison/scripts/normalize_em.py\n```\n"
    )
    text += "\n## So với SQL gốc\n\n"
    text += "| Method | EM gốc | EM chuẩn hóa | Lỗi parser gốc → mới |\n|---|---:|---:|---:|\n"
    for method in sources:
        previous = ROOT / f"results/em_full_dev/{method}.details.json"
        if previous.is_file():
            old = read_json(previous)
            new = read_json(output / f"{method}.details.json")
            old_em = sum(item["EM"] for item in old) / len(old)
            new_em = sum(item["EM"] for item in new) / len(new)
            old_errors = sum(item["parse_error"] is not None for item in old)
            new_errors = sum(item["parse_error"] is not None for item in new)
            text += f"| {method} | {old_em:.2%} | {new_em:.2%} | {old_errors} → {new_errors} |\n"
    report.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

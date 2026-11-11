"""Score saved full-dev predictions with the original Spider Exact Set Match."""

import argparse
import hashlib
import shlex
import sys
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

from common import ROOT, examples, read_json, sql_line, write_json
from evaluate import validate_predictions, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/em_full_dev")
    parser.add_argument(
        "--prediction-root",
        type=Path,
        help="Directory containing all four method.jsonl files",
    )
    args = parser.parse_args()
    rows = examples(ROOT / "data/dev_full/examples.json")
    assert read_json(ROOT / "data/dev_full/subset.json") == [
        row["example_id"] for row in rows
    ]
    sources = {
        method: ROOT / f"results/full_dev/predictions/{method}.jsonl"
        for method in ("few_shot", "mac_sql", "dail_sql")
    }
    sources["codex_mcp"] = ROOT / "results/codex_full_dev/predictions/codex_mcp.jsonl"
    if args.prediction_root:
        sources = {
            method: args.prediction_root / f"{method}.jsonl" for method in sources
        }
    predictions = {
        method: validate_predictions(path, rows) for method, path in sources.items()
    }
    spider_root = ROOT.parent / "spider"
    sys.path.insert(0, str(spider_root))
    import evaluation as spider

    db_root = ROOT / "downloads/spider_data/database"
    tables = ROOT / "data/dev_full/tables.json"
    metadata = read_json(ROOT / "data/dev_full/source.json")
    assert hashlib.sha256(tables.read_bytes()).hexdigest() == metadata["tables_sha256"]
    for db in {row["db_id"] for row in rows}:
        path = db_root / db / f"{db}.sqlite"
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == metadata["databases_sha256"][db]
        )
    kmaps = spider.build_foreign_key_map_from_json(str(tables))
    args.output.mkdir(parents=True, exist_ok=True)
    gold = args.output / "gold.txt"
    gold.write_text(
        "".join(sql_line(row["query"]) + "\t" + row["db_id"] + "\n" for row in rows),
        encoding="utf-8",
    )
    summary, breakdown = [], []
    original_evaluator, original_get_sql = spider.Evaluator, spider.get_sql
    for method, records in predictions.items():
        details = []
        current = {}

        class RecordingEvaluator(original_evaluator):
            # Record the original evaluator's decisions without changing them.
            def eval_hardness(self, sql, *, current=current):
                self.record_top_level = True
                result = super().eval_hardness(sql)
                current["difficulty"] = result
                return result

            def eval_exact_match(
                self, pred, label, *, details=details, current=current
            ):
                result = super().eval_exact_match(pred, label)
                if not getattr(self, "record_top_level", False):
                    return result
                row = rows[len(details)]
                details.append(
                    {
                        "example_id": row["example_id"],
                        "db_id": row["db_id"],
                        "EM": int(result),
                        "parse_error": current.pop("parse_error", None),
                        "difficulty": current["difficulty"],
                    }
                )
                return result

        def recording_get_sql(schema, query, *, current=current):
            try:
                return original_get_sql(schema, query)
            except Exception as error:
                current["parse_error"] = f"{type(error).__name__}: {error}"
                raise

        pred = args.output / f"{method}.txt"
        pred.write_text(
            "".join(
                (sql_line(record["predicted_sql"]) or "__MISSING_PREDICTION__") + "\n"
                for record in records
            ),
            encoding="utf-8",
        )
        spider.Evaluator, spider.get_sql = RecordingEvaluator, recording_get_sql
        try:
            with (
                (args.output / f"{method}.log").open("w", encoding="utf-8") as log,
                redirect_stdout(log),
            ):
                spider.evaluate(str(gold), str(pred), str(db_root), "match", kmaps)
        finally:
            spider.Evaluator, spider.get_sql = original_evaluator, original_get_sql
        assert len(details) == len(rows)
        assert Counter(row["difficulty"] for row in details) == {
            "easy": 248,
            "medium": 446,
            "hard": 174,
            "extra": 166,
        }
        write_json(args.output / f"{method}.details.json", details)
        for level in ("all", "easy", "medium", "hard", "extra"):
            subset = [d for d in details if level == "all" or d["difficulty"] == level]
            correct = sum(d["EM"] for d in subset)
            result = {
                "method": method,
                "difficulty": level,
                "correct": correct,
                "evaluated_examples": len(subset),
                "EM": correct / len(subset),
                "parse_errors": sum(d["parse_error"] is not None for d in subset),
            }
            breakdown.append(result)
            if level == "all":
                summary.append({k: v for k, v in result.items() if k != "difficulty"})
                print(
                    f"{method}: {correct}/{len(subset)} EM={result['EM']:.4%}, "
                    f"parse_errors={result['parse_errors']}",
                    flush=True,
                )
    write_csv(args.output / "summary.csv", list(summary[0]), summary)
    write_csv(args.output / "by_difficulty.csv", list(breakdown[0]), breakdown)
    write_json(
        args.output / "manifest.json",
        {
            "evaluator": str(spider_root / "evaluation.py"),
            "evaluator_sha256": hashlib.sha256(
                (spider_root / "evaluation.py").read_bytes()
            ).hexdigest(),
            "disable_value": spider.DISABLE_VALUE,
            "disable_distinct": spider.DISABLE_DISTINCT,
            "python": sys.executable,
            "db_root": str(db_root),
            "tables": str(tables),
            "sources": {
                method: {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for method, path in sources.items()
            },
        },
    )
    lines = [
        "# Spider 1.0 dev — Exact Set Match",
        "",
        (
            "Chấm 1.034 prediction đã lưu mỗi phương pháp bằng `spider/evaluation.py`, "
            "`etype=match`. Kiểm tra ID, database, câu hỏi và thứ tự trước khi chấm; "
            "kiểm tra SHA-256 của schema/database theo dữ liệu chuẩn bị ban đầu."
        ),
        "",
        "| Phương pháp | Đúng / tổng | EM | Lỗi parser Spider |",
        "|---|---:|---:|---:|",
    ]
    names = {
        "few_shot": "DIN-SQL",
        "mac_sql": "MAC-SQL",
        "dail_sql": "DAIL-SQL",
        "codex_mcp": "Codex MCP SQL",
    }
    for result in summary:
        lines.append(
            f"| {names[result['method']]} | {result['correct']} / {result['evaluated_examples']} "
            f"| {result['EM']:.2%} | {result['parse_errors']} |"
        )
    lines += [
        "",
        "| Phương pháp | Easy (248) | Medium (446) | Hard (174) | Extra (166) |",
        "|---|---:|---:|---:|---:|",
    ]
    for method in sources:
        cells = [
            f"{r['EM']:.2%}"
            for r in breakdown
            if r["method"] == method and r["difficulty"] != "all"
        ]
        lines.append("| " + names[method] + " | " + " | ".join(cells) + " |")
    lines += [
        "",
        (
            "EM ở đây là Exact Set Match theo parser/cấu trúc SQL của Spider; "
            "không phải so khớp chuỗi hay execution accuracy. Giữ mặc định evaluator: "
            "`DISABLE_VALUE=True`, `DISABLE_DISTINCT=True`. SQL không parse được "
            "được chấm bằng SQL rỗng theo chính evaluator; không loại khỏi mẫu số. "
            "Lỗi parser Spider không đồng nghĩa SQL không hợp lệ trong SQLite."
        ),
        "",
        (
            "Mỗi phương pháp có input `.txt`, log chính thức `.log`, và kết quả từng câu "
            "`.details.json`. `manifest.json` lưu nguồn và checksum. Không gọi lại model."
        ),
        "",
        "Chạy lại từ thư mục `text2sql/` (cần dữ liệu NLTK punkt_tab):",
        "",
        "```bash",
        "NLTK_DATA=/tmp/text2sql-nltk "
        + shlex.join(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--output",
                str(args.output.resolve()),
            ]
            + (
                ["--prediction-root", str(args.prediction_root.resolve())]
                if args.prediction_root
                else []
            )
        ),
        "```",
        "",
    ]
    (args.output / "report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

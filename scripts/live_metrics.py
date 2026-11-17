"""Score one saved demo prediction; no model calls or writes to the database."""

import json
import math
import sqlite3
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sqlite_eval import execute, order_matters, result_eq


def exact_match(database, predicted, gold, db_id, tables):
    sys.path.insert(0, str(ROOT.parent / "spider"))
    import evaluation as spider

    schema = spider.Schema(spider.get_schema(str(database)))
    mapping = spider.build_foreign_key_map_from_json(str(tables))[db_id]
    # A missing tokenizer or invalid gold is an evaluation setup failure (N/A).
    gold_ast = spider.get_sql(schema, gold)
    parser_error = None
    try:
        predicted_ast = spider.get_sql(schema, predicted)
    except Exception as error:  # noqa: BLE001 — use the original evaluator's empty prediction fallback
        parser_error = f"SQL dự đoán không được parser Spider hỗ trợ: {error}"
        predicted_ast = {
            "except": None,
            "from": {"conds": [], "table_units": []},
            "groupBy": [],
            "having": [],
            "intersect": None,
            "limit": None,
            "orderBy": [],
            "select": [False, []],
            "union": None,
            "where": [],
        }
    parsed = []
    for item in (predicted_ast, gold_ast):
        valid = spider.build_valid_col_units(item["from"]["table_units"], schema)
        parsed.append(
            spider.rebuild_sql_col(valid, spider.rebuild_sql_val(item), mapping)
        )
    evaluator = spider.Evaluator()
    em = int(evaluator.eval_exact_match(*parsed))
    return em, evaluator.partial_scores, parser_error


def timed_query(database, sql, deadline):
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 100)
    start = time.perf_counter_ns()
    try:
        connection.execute(sql).fetchall()
    finally:
        connection.close()
    return max((time.perf_counter_ns() - start) / 1e9, 1e-9)


def score(request):
    database = Path(request["database"]).resolve()
    predicted, gold = request["predicted"], request["gold"]
    result = dict(  # noqa: C408
        cm=None,
        cm_error=None,
        em=None,
        ex=None,
        ves=None,
        em_error=None,
        ex_error=None,
        ves_error=None,
        iterations=0,
        predicted_ms=None,
        gold_ms=None,
        ves_valid_match=None,
    )
    try:
        result["em"], result["cm"], parser_error = exact_match(
            database, predicted, gold, request["db_id"], Path(request["tables"])
        )
        if parser_error:
            result["em_error"] = parser_error
            result["cm_error"] = (
                "Parser Spider không hỗ trợ SQL dự đoán; CM được chấm với dự đoán rỗng theo evaluator gốc."
            )
    except Exception as error:  # noqa: BLE001 — each metric reports its own failure
        # Spider's restricted parser can reject valid SQLite. Do not report this
        # as an execution failure or silently substitute string equality.
        result["em_error"] = f"Spider parser: {type(error).__name__}: {error}"
        result["cm_error"] = result["em_error"]
    try:
        gold_rows, gold_width = execute(database, gold, 2)
    except Exception as error:  # noqa: BLE001 — an invalid reference is not a model error
        result["ex_error"] = f"SQL tham chiếu: {type(error).__name__}: {error}"
        result["ves_error"] = "Không có kết quả tham chiếu hợp lệ để đánh giá."
        return result
    try:
        predicted_rows, predicted_width = execute(database, predicted, 2)
        result["ex"] = int(
            gold_width == predicted_width
            and result_eq(gold_rows, predicted_rows, order_matters(gold))
        )
    except Exception as error:  # noqa: BLE001 — execution failures contribute zero
        result.update(ex=0, ves=0.0, ves_valid_match=False)
        result["ex_error"] = f"SQL dự đoán: {type(error).__name__}: {error}"
        result["ves_error"] = "VES=0 vì SQL dự đoán không thực thi được."
        return result
    # Match BIRD's validity check for VES (set comparison). EX above retains
    # this repository's stricter bag/ordering/column permutation semantics.
    result["ves_valid_match"] = set(predicted_rows) == set(gold_rows)
    if not result["ves_valid_match"]:
        result["ves"] = 0.0
        return result
    try:
        deadline = time.monotonic() + 5
        predicted_times, gold_times = [], []
        for _ in range(10):
            if time.monotonic() >= deadline:
                raise TimeoutError("Vượt ngân sách đo 5 giây")
            predicted_times.append(timed_query(database, predicted, deadline))
            gold_times.append(timed_query(database, gold, deadline))
        ratios = [g / p for p, g in zip(predicted_times, gold_times)]
        mean, std = statistics.mean(ratios), statistics.pstdev(ratios)
        filtered = [
            ratio for ratio in ratios if mean - 3 * std < ratio < mean + 3 * std
        ]
        if not filtered:
            raise ValueError("Không còn mẫu sau lọc ngoại lệ 3σ")
        result.update(
            ves=100 * math.sqrt(statistics.mean(filtered)),
            iterations=len(ratios),
            predicted_ms=statistics.mean(predicted_times) * 1000,
            gold_ms=statistics.mean(gold_times) * 1000,
        )
    except Exception as error:  # noqa: BLE001 — each metric reports its own failure
        result["ves_error"] = f"{type(error).__name__}: {error}"
    return result


if __name__ == "__main__":
    print(json.dumps(score(json.load(sys.stdin))))

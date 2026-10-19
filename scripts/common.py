"""Small file/validation helpers shared by the command-line scripts."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Conservatively retain quoting on SQLite keywords: removing it can change SQL
# meaning (e.g. a column named `order`). Such names remain unsupported by Spider.
SQLITE_KEYWORDS = set(
    """
ABORT ACTION ADD AFTER ALL ALTER ALWAYS ANALYZE AND AS ASC ATTACH AUTOINCREMENT
BEFORE BEGIN BETWEEN BY CASCADE CASE CAST CHECK COLLATE COLUMN COMMIT CONFLICT
CONSTRAINT CREATE CROSS CURRENT CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP
DATABASE DEFAULT DEFERRABLE DEFERRED DELETE DESC DETACH DISTINCT DO DROP EACH
ELSE END ESCAPE EXCEPT EXCLUDE EXCLUSIVE EXISTS EXPLAIN FAIL FILTER FIRST
FOLLOWING FOR FOREIGN FROM FULL GENERATED GLOB GROUP GROUPS HAVING IF IGNORE
IMMEDIATE IN INDEX INDEXED INITIALLY INNER INSERT INSTEAD INTERSECT INTO IS
ISNULL JOIN KEY LAST LEFT LIKE LIMIT MATCH MATERIALIZED NATURAL NO NOT NOTHING
NOTNULL NULL NULLS OF OFFSET ON OR ORDER OTHERS OUTER OVER PARTITION PLAN PRAGMA
PRECEDING PRIMARY QUERY RAISE RANGE RECURSIVE REFERENCES REGEXP REINDEX RELEASE
RENAME REPLACE RESTRICT RETURNING RIGHT ROLLBACK ROW ROWS SAVEPOINT SELECT SET
TABLE TEMP TEMPORARY THEN TIES TO TRANSACTION TRIGGER UNBOUNDED UNION UNIQUE
UPDATE USING VACUUM VALUES VIEW VIRTUAL WHEN WHERE WINDOW WITH WITHOUT TRUE FALSE
""".split()
)


def _rewrite_sql(sql, *, strip_comments=False, unquote_identifiers=False):
    """Scan SQL without interpreting comment markers inside quoted tokens."""
    if not isinstance(sql, str):
        raise ValueError("SQL must be a string")
    result = []
    i = 0
    while i < len(sql):
        start = i
        if sql.startswith("--", i):
            end = sql.find("\n", i)
            i = len(sql) if end == -1 else end
            if strip_comments:
                result.append(" ")
                continue
        elif sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            i = len(sql) if end == -1 else end + 2
            if strip_comments:
                # Whitespace prevents neighboring tokens from joining together.
                result.append(" ")
                continue
        elif sql[i] in "'\"`[":
            opening = sql[i]
            closing = "]" if opening == "[" else opening
            i += 1
            closed = False
            while i < len(sql):
                if sql[i] != closing:
                    i += 1
                elif opening != "[" and i + 1 < len(sql) and sql[i + 1] == closing:
                    i += 2  # SQL escapes quote characters by doubling them.
                else:
                    i += 1
                    closed = True
                    break
            if unquote_identifiers and opening == "`" and closed:
                name = sql[start + 1 : i - 1]
                if (
                    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
                    and name.upper() not in SQLITE_KEYWORDS
                ):
                    result.append(name)
                    continue
        else:
            i += 1
        result.append(sql[start:i])
    return "".join(result)


def normalize_identifier_quotes(sql):
    """Unquote simple non-keyword backtick identifiers, preserving SQL literals.

    Do not guess replacements for names containing spaces, punctuation, escaped
    backticks or keywords. Preserve malformed/unclosed tokens for evaluation.
    """
    return _rewrite_sql(sql, unquote_identifiers=True)


def strip_sql_comments(sql):
    """Remove line/block comments while preserving literals and identifiers."""
    return _rewrite_sql(sql, strip_comments=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def examples(path):
    rows = read_json(path)
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty array of subset examples")
    ids = [r["example_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate subset example IDs")
    for row in rows:
        for key in ("example_id", "db_id", "question", "query"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Invalid subset field: {key}")
    return rows


def sql_line(sql):
    # Only flatten line separators; do not collapse spaces inside SQL literals.
    if not isinstance(sql, str):
        raise ValueError("SQL must be a string")
    return sql.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()


def write_predictions(rows, sqls, output):
    if len(rows) != len(sqls):
        raise ValueError("Prediction count does not match subset")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = [
        dict(
            example_id=r["example_id"],
            db_id=r["db_id"],
            question=r["question"],
            predicted_sql=sql_line(
                _rewrite_sql(s, strip_comments=True, unquote_identifiers=True)
            ),
        )
        for r, s in zip(rows, sqls)
    ]
    output.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )

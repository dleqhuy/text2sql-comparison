"""Regression checks for alignment, failed predictions and the official evaluator."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import (
    normalize_identifier_quotes,
    strip_sql_comments,
    write_json,
    write_predictions,
)
from prepare_data import prepare
from normalize_few_shot import normalize as normalize_text
from normalize_mac_sql import normalize as normalize_mac
from evaluate import evaluate, parse_scores, validate_predictions, INVALID_SQL


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.rows = [
            dict(
                example_id=f"dev_{i:04d}",
                db_id="demo",
                question=f"Question {i}",
                query="SELECT name FROM items",
            )
            for i in range(2)
        ]

    def tearDown(self):
        self.temp.cleanup()

    def test_text_preserves_blank_failures_and_literal_spaces(self):
        path = self.root / "raw.txt"
        path.write_text("SELECT 'a  b'\n\n")
        values = normalize_text(path, self.rows)
        self.assertEqual(values, ["SELECT 'a  b'", ""])
        write_predictions(self.rows, values, self.root / "out.jsonl")
        self.assertEqual(
            validate_predictions(self.root / "out.jsonl", self.rows)[0][
                "predicted_sql"
            ],
            "SELECT 'a  b'",
        )
        path.write_text("SELECT 1\n")
        with self.assertRaises(ValueError):
            normalize_text(path, self.rows)

    def test_mac_orders_by_idx_and_fills_missing(self):
        path = self.root / "raw.jsonl"
        record = dict(idx=1, query="Question 1", db_id="demo", pred="SELECT 2")
        path.write_text(json.dumps(record) + "\n")
        self.assertEqual(normalize_mac(path, self.rows), ["", "SELECT 2"])
        path.write_text((json.dumps(record) + "\n") * 2)
        with self.assertRaises(ValueError):
            normalize_mac(path, self.rows)

    def test_rejects_shuffled_normalized_predictions(self):
        path = self.root / "pred.jsonl"
        write_predictions(self.rows[::-1], ["SELECT 1", "SELECT 2"], path)
        with self.assertRaises(ValueError):
            validate_predictions(path, self.rows)

    def test_rejects_incomplete_evaluator_count(self):
        with self.assertRaises(ValueError):
            parse_scores(
                "count 1 0 0 0 1\nexecution 1.000 0.000 0.000 0.000 1.000\n", 2
            )

    def test_identifier_quotes_preserve_literals_comments_and_escaped_quotes(self):
        sql = "SELECT `s`.`Name`, 'a `Name` and ''quoted''', \"literal `x`\", [a`b] FROM `singer` AS `s` -- `comment`\n/* `comment` */"
        expected = "SELECT s.Name, 'a `Name` and ''quoted''', \"literal `x`\", [a`b] FROM singer AS s -- `comment`\n/* `comment` */"
        self.assertEqual(normalize_identifier_quotes(sql), expected)
        self.assertEqual(normalize_identifier_quotes(expected), expected)

    def test_unsafe_or_malformed_identifier_quotes_are_retained(self):
        sql = "SELECT `order`, `true`, `full name`, `a``b`, `1abc`, `unclosed"
        self.assertEqual(normalize_identifier_quotes(sql), sql)

    def test_identifier_normalization_preserves_sqlite_results(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE singer (Name TEXT, Country TEXT)")
            db.execute("INSERT INTO singer VALUES ('a `Name`', 'France')")
            sql = "SELECT `Name`, 'a `Name`' FROM `singer` WHERE `Country` = 'France'"
            self.assertEqual(
                db.execute(sql).fetchall(),
                db.execute(normalize_identifier_quotes(sql)).fetchall(),
            )

    def test_comment_removal_preserves_strings_and_quoted_identifiers(self):
        sql = "SELECT '-- /* text */', 'it''s -- text', \"a--b\", `a/*b*/`, [c--d] /* remove */ -- remove\nFROM items"
        expected = "SELECT '-- /* text */', 'it''s -- text', \"a--b\", `a/*b*/`, [c--d]    \nFROM items"
        self.assertEqual(strip_sql_comments(sql), expected)

    def test_comment_removal_preserves_sqlite_semantics_and_token_boundaries(self):
        queries = [
            "-- SQLite\nSELECT 1/* separate */+2; -- trailing",
            "SELECT '/* text */', 'a--b', 'it''s -- text' /* comment */",
            "SELECT/* separate */1",
            "SELECT 1 -- comment\r\n+ 2",
            "SELECT 1 /* comment until EOF",
        ]
        with sqlite3.connect(":memory:") as db:
            for query in queries:
                with self.subTest(query=query):
                    self.assertEqual(
                        db.execute(query).fetchall(),
                        db.execute(strip_sql_comments(query)).fetchall(),
                    )
        self.assertEqual(strip_sql_comments("-- comment only"), " ")
        self.assertEqual(
            strip_sql_comments("SELECT 'unclosed -- literal"),
            "SELECT 'unclosed -- literal",
        )

    def test_writer_removes_comments_before_flattening_lines(self):
        path = self.root / "pred.jsonl"
        write_predictions(
            self.rows,
            ["-- SQLite\nSELECT `name` FROM `items`;", "-- only comment"],
            path,
        )
        predictions = validate_predictions(path, self.rows)
        self.assertEqual(predictions[0]["predicted_sql"], "SELECT name FROM items;")
        self.assertEqual(predictions[1]["predicted_sql"], "")

    def fixture(self):
        source = self.root / "source"
        db_dir = source / "database/demo"
        db_dir.mkdir(parents=True)
        with sqlite3.connect(db_dir / "demo.sqlite") as db:
            db.execute("CREATE TABLE items (name TEXT)")
            db.execute("INSERT INTO items VALUES ('one')")
        write_json(source / "dev.json", self.rows)
        write_json(
            source / "tables.json",
            [
                dict(
                    db_id="demo",
                    table_names_original=["items"],
                    table_names=["items"],
                    column_names_original=[[-1, "*"], [0, "name"]],
                    column_names=[[-1, "*"], [0, "name"]],
                    column_types=["text", "text"],
                    primary_keys=[],
                    foreign_keys=[],
                )
            ],
        )
        return source

    def test_prepare_freezes_selection_and_detects_dataset_change(self):
        source = self.fixture()
        out = self.root / "data"
        self.assertEqual(prepare(source, out, count=2), 2)
        self.assertEqual(prepare(source, out, count=1), 2)
        write_json(source / "dev.json", self.rows[::-1])
        with self.assertRaises(ValueError):
            prepare(source, out)

    def test_missing_database_fails_before_writing_data(self):
        source = self.fixture()
        (source / "database/demo/demo.sqlite").unlink()
        with self.assertRaises(FileNotFoundError):
            prepare(source, self.root / "data")
        self.assertFalse((self.root / "data/examples.json").exists())

    def test_official_spider_exec_keeps_missing_prediction(self):
        try:
            from nltk import word_tokenize
        except ImportError:
            self.skipTest(
                "Install comparison dependencies for Spider integration check"
            )
        word_tokenize("select name from items")
        source = self.fixture()
        data = self.root / "data"
        prepare(source, data, count=2)
        pred = self.root / "pred.jsonl"
        write_predictions(
            self.rows,
            ["-- SQLite\nSELECT `name` FROM `items`", "-- only comment"],
            pred,
        )
        args = argparse.Namespace(
            examples=data / "examples.json",
            subset=data / "subset.json",
            spider_root=Path(__file__).resolve().parents[2] / "spider",
            db=source / "database",
            table=source / "tables.json",
            prediction=[f"fixture={pred}"],
            work_dir=self.root / "eval",
            summary=self.root / "summary.csv",
            python=sys.executable,
            timeout=30,
        )
        evaluate(args)
        self.assertIn("fixture,0.5,2,1", args.summary.read_text())
        self.assertIn(INVALID_SQL, (args.work_dir / "fixture.txt").read_text())


if __name__ == "__main__":
    unittest.main()

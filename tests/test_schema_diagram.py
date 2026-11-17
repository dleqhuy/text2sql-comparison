"""Schema metadata for the demo diagram, without a PostgreSQL dependency."""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.live_models import SchemaObject
from app.services import pipeline


class SchemaDiagramTests(unittest.TestCase):
    def test_keys_types_quoted_names_and_implicit_composite_references(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            database = data / "database/demo/demo.sqlite"
            database.parent.mkdir(parents=True)
            with sqlite3.connect(database) as connection:
                connection.executescript("""
                    CREATE TABLE "parent table" (a INTEGER, b TEXT, PRIMARY KEY (b, a));
                    CREATE TABLE child (
                        id INTEGER PRIMARY KEY,
                        parent_b TEXT NOT NULL,
                        parent_a INTEGER,
                        FOREIGN KEY (parent_b, parent_a) REFERENCES "PARENT TABLE"
                    );
                    CREATE TABLE "a""quote" (value REAL);
                    CREATE TABLE self_ref (id INTEGER PRIMARY KEY, parent INTEGER REFERENCES self_ref(id));
                """)
            with patch.object(pipeline, "DATA", data):
                tables = {
                    row["name"]: SchemaObject.model_validate(row)
                    for row in pipeline.schema("demo")
                }
            child = tables["child"]
            self.assertEqual(child.columns[0].primary_key, 1)
            self.assertTrue(child.columns[1].not_null)
            self.assertEqual(child.columns[1].type, "TEXT")
            self.assertEqual(
                [
                    (key.column, key.target_table, key.target_column, key.sequence)
                    for key in child.foreign_keys
                ],
                [
                    ("parent_b", "PARENT TABLE", "b", 0),
                    ("parent_a", "PARENT TABLE", "a", 1),
                ],
            )
            self.assertEqual(len({key.id for key in child.foreign_keys}), 1)
            self.assertEqual(tables['a"quote'].columns[0].type, "REAL")
            self.assertEqual(tables['a"quote'].foreign_keys, [])
            self.assertEqual(tables["self_ref"].foreign_keys[0].target_column, "id")
            self.assertIn("CREATE TABLE", child.ddl)

    def test_demo_database_metadata(self):
        if not (
            pipeline.DATA / "database/concert_singer/concert_singer.sqlite"
        ).exists():
            self.skipTest("Spider database not installed")
        tables = {
            row["name"]: SchemaObject.model_validate(row)
            for row in pipeline.schema("concert_singer")
        }
        self.assertEqual(
            set(tables), {"concert", "singer", "singer_in_concert", "stadium"}
        )
        for table in tables.values():
            for key in table.foreign_keys:
                self.assertIn(key.target_table.lower(), tables)
                target = tables[key.target_table.lower()]
                self.assertIn(
                    key.target_column.lower(), [c.name.lower() for c in target.columns]
                )


if __name__ == "__main__":
    unittest.main()

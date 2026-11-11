"""Semantic regression cases for Spider syntax adaptation."""

import sqlite3
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from spider_normalize import normalize


class NormalizeTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(
            "CREATE TABLE t (x INTEGER, y TEXT);"
            "INSERT INTO t VALUES (1,'b'),(2,'a'),(2,'a'),(NULL,'c');"
            "CREATE TABLE u (x INTEGER); INSERT INTO u VALUES (1),(3);"
        )
        self.schema = {"t": ["x", "y"], "u": ["x"]}

    def tearDown(self):
        self.conn.close()

    def equivalent(self, sql, ordered=False):
        normalized, _ = normalize(sql, self.schema)
        before = self.conn.execute(sql).fetchall()
        after = self.conn.execute(normalized).fetchall()
        self.assertEqual(
            before if ordered else Counter(before),
            after if ordered else Counter(after),
            normalized,
        )
        return normalized

    def test_labels_and_order_alias(self):
        result = self.equivalent(
            'SELECT "x" AS num, COUNT(*) AS n FROM "t" GROUP BY num ORDER BY n DESC, num',
            True,
        )
        self.assertNotIn(" AS num", result)
        self.assertIn("ORDER BY COUNT(*) DESC", result)

    def test_sqlite_column_alias_collision_resolution(self):
        self.equivalent("SELECT -x AS x FROM t WHERE x > 0 ORDER BY x", True)
        self.equivalent(
            "SELECT -x AS x, COUNT(*) FROM t GROUP BY x HAVING x > 0 ORDER BY x", True
        )
        self.equivalent("SELECT -x AS x FROM t ORDER BY x + 1", True)

    def test_derived_and_cte_output_names(self):
        for sql in [
            "SELECT d.n FROM (SELECT x AS n FROM t) d ORDER BY d.n",
            "WITH q AS (SELECT x AS n FROM t) SELECT n FROM q ORDER BY n",
        ]:
            result = self.equivalent(sql, True)
            self.assertIn("AS n", result)

    def test_correlated_and_reused_table_aliases(self):
        self.equivalent(
            "SELECT a.x FROM t a WHERE EXISTS (SELECT 1 FROM u b WHERE b.x=a.x)"
        )
        self.equivalent("SELECT a.x FROM t a WHERE a.x IN (SELECT a.x FROM u a)")
        self.equivalent("SELECT t.x FROM t t ORDER BY t.x", True)

    def test_left_join_cast_null_distinct_and_duplicates(self):
        result = self.equivalent(
            "SELECT DISTINCT CAST(a.x AS TEXT) AS n FROM t a LEFT JOIN u b ON a.x=b.x WHERE b.x IS NULL ORDER BY n",
            True,
        )
        self.assertIn("LEFT JOIN", result)
        self.assertIn("CAST", result)
        self.assertIn("IS NULL", result)
        self.assertIn("DISTINCT", result)
        self.equivalent("SELECT a.y FROM t a INNER JOIN u b ON a.x=b.x")

    def test_quoted_literals_and_inequality(self):
        result = self.equivalent(
            "SELECT y, 'a<>b', 'AS x', \"unknown\" FROM t WHERE y <> 'b'"
        )
        self.assertIn("'a<>b'", result)
        self.assertIn('"unknown"', result)
        self.assertIn("!=", result)

    def test_volatile_alias_retained(self):
        result, _ = normalize("SELECT RANDOM() AS r FROM t ORDER BY r", self.schema)
        self.assertIn("AS r", result)

    def test_double_quoted_string_must_resolve_in_its_own_scope(self):
        self.conn.execute("CREATE TABLE v (y TEXT)")
        self.conn.execute("INSERT INTO v VALUES ('value')")
        self.schema["v"] = ["y"]
        result = self.equivalent('SELECT "x", y AS x FROM v')
        self.assertIn('"x"', result)

    def test_postfix_not_operators_preserved(self):
        for sql in [
            "SELECT x FROM t WHERE x NOT IN (SELECT x FROM u)",
            "SELECT y FROM t WHERE y NOT LIKE 'a%'",
            "SELECT x FROM t WHERE x NOT BETWEEN 1 AND 2",
            "SELECT x FROM t WHERE x IS NOT NULL",
        ]:
            result = self.equivalent(sql)
            self.assertNotIn("WHERE NOT", result)

    def test_multiple_statements_rejected(self):
        with self.assertRaises(ValueError):
            normalize("SELECT x FROM t; SELECT x FROM u", self.schema)

    def test_normalization_is_idempotent(self):
        sql = 'SELECT a."x" AS n FROM "t" a WHERE a.x <> 1 ORDER BY n'
        once, _ = normalize(sql, self.schema)
        twice, _ = normalize(once, self.schema)
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()

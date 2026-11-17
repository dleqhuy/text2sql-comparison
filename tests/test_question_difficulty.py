"""Keep UI difficulty labels consistent with Spider's original evaluator."""

import ast
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.difficulty import difficulty


class QuestionDifficultyTests(unittest.TestCase):
    def test_labels_match_original_evaluator_on_all_installed_splits(self):
        source = ROOT.parent / "spider/evaluation.py"
        # Load only the official evaluator's hardness rules. Tokenization/NLTK
        # is unnecessary because each dataset row already contains its SQL AST.
        names = {
            "has_agg",
            "get_nestedSQL",
            "count_agg",
            "count_component1",
            "count_component2",
            "count_others",
            "Evaluator",
        }
        nodes = [
            node
            for node in ast.parse(source.read_text()).body
            if (
                isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
            )
            or (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id in {"WHERE_OPS", "AGG_OPS"}
                    for target in node.targets
                )
            )
        ]
        namespace = {}
        exec(  # noqa: S102 — execute only checked-in official evaluator rules
            compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"),
            namespace,
        )
        official = namespace["Evaluator"]()
        for split in ["dev", "train_spider", "train_others", "test"]:
            path = ROOT / f"downloads/spider_data/{split}.json"
            if not path.exists():
                continue
            rows = json.loads(path.read_text())
            counts = Counter()
            for index, row in enumerate(rows):
                expected = official.eval_hardness(row["sql"])
                actual = difficulty(row["sql"])
                self.assertEqual(actual, expected, (split, index))
                counts[actual] += 1
            self.assertEqual(set(counts), {"easy", "medium", "hard", "extra"})
            if split == "dev":
                self.assertEqual(
                    counts, {"easy": 248, "medium": 446, "hard": 174, "extra": 166}
                )


if __name__ == "__main__":
    unittest.main()

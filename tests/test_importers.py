from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conjecture_records.importers.formal_conjectures import import_tree
from conjecture_records.importers.openconjecture import import_metadata


class ImporterTests(unittest.TestCase):
    def test_openconjecture_is_metadata_only(self) -> None:
        row = {
            "id": 4,
            "arxiv_id": "2601.12345v1",
            "title": "Example",
            "conjecture_text": "private-to-this-test body",
            "future_statement_body": "unknown body field",
            "publication_decision": "publish",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = import_metadata(path, "abc", "https://example.test/data")
        encoded = json.dumps(result)
        self.assertNotIn("private-to-this-test body", encoded)
        self.assertNotIn("unknown body field", encoded)
        self.assertNotIn("conjecture_text", result["records"][0]["metadata"])
        self.assertEqual(result["source"]["body_policy"], "metadata_only")

    def test_formal_importer_keeps_tree_metadata(self) -> None:
        tree = {
            "tree": [
                {"path": "FormalConjectures/2601.12345.lean", "type": "blob", "sha": "a", "size": 10},
                {"path": "README.md", "type": "blob", "sha": "b", "size": 20},
                {"path": "../escape.lean", "type": "blob", "sha": "c", "size": 30},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tree.json"
            path.write_text(json.dumps(tree), encoding="utf-8")
            result = import_tree(path, "abc", "https://example.test/repo")
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["records"][0]["source_ids"], ["2601.12345"])


if __name__ == "__main__":
    unittest.main()

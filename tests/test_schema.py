from __future__ import annotations

import copy
import unittest
from pathlib import Path

from conjecture_records.catalog import build_commentary_records
from conjecture_records.schema import validate_record


FIXTURE = Path(__file__).parent / "fixtures" / "commentary"


class SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = build_commentary_records(FIXTURE, "1" * 40)[0]

    def test_valid_record(self) -> None:
        self.assertEqual(validate_record(self.record), [])

    def test_invalid_status(self) -> None:
        record = copy.deepcopy(self.record)
        record["settlement"]["status"] = "solved"
        self.assertTrue(any("status" in error for error in validate_record(record)))

    def test_path_traversal_rejected(self) -> None:
        record = copy.deepcopy(self.record)
        record["crosswalk"]["formal_conjectures_paths"] = ["../private.lean"]
        self.assertTrue(any("unsafe" in error for error in validate_record(record)))


if __name__ == "__main__":
    unittest.main()

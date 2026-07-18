from __future__ import annotations

import unittest

from conjecture_records.crosswalk import build_crosswalk, normalize_arxiv_id


class CrosswalkTests(unittest.TestCase):
    def test_normalize_version(self) -> None:
        self.assertEqual(normalize_arxiv_id("arXiv:2601.12345v2"), "2601.12345")

    def test_exact_arxiv_crosswalk(self) -> None:
        result = build_crosswalk(
            [{"arxiv_id": "2601.12345v1", "openconjecture_id": 7}],
            [{"path": "Formal/Example.lean", "source_ids": ["2601.12345"]}],
        )
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["rows"][0]["openconjecture_ids"], [7])


if __name__ == "__main__":
    unittest.main()

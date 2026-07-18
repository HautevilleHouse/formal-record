from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from conjecture_records.catalog import (
    build_commentary_records,
    canonical_bytes,
    extract_authors,
    extract_openconjecture_ids,
    extract_routes,
    extract_statement,
    load_records,
    stable_record_id,
    write_catalog,
)


FIXTURE = Path(__file__).parent / "fixtures" / "commentary"
REVISION = "1" * 40


class CatalogTests(unittest.TestCase):
    def test_stable_identifier(self) -> None:
        self.assertEqual(
            stable_record_id("2601.12345v1", "example-packet"),
            stable_record_id("2601.12345v1", "example-packet"),
        )
        self.assertNotEqual(
            stable_record_id("2601.12345v1", "example-packet"),
            stable_record_id("2601.12345v2", "example-packet"),
        )

    def test_build_and_write_are_deterministic(self) -> None:
        records = build_commentary_records(FIXTURE, REVISION)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["settlement"]["status"], "disproved")
        self.assertEqual(record["crosswalk"]["openconjecture_ids"], [7])
        self.assertEqual(record["verification"]["routes"][0]["kind"], "python")
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_catalog = write_catalog(records, REVISION, Path(first))
            second_catalog = write_catalog(records, REVISION, Path(second))
            self.assertEqual(first_catalog, second_catalog)
            self.assertEqual((Path(first) / "records.jsonl").read_bytes(), (Path(second) / "records.jsonl").read_bytes())
            self.assertEqual(load_records(Path(first) / "records.jsonl"), records)
            digest = hashlib.sha256(b"".join(canonical_bytes(item) for item in records)).hexdigest()
            self.assertEqual(first_catalog["records_sha256"], digest)

    def test_mixed_proof_and_counterexample_is_not_flattened(self) -> None:
        from conjecture_records.catalog import classify_settlement

        self.assertEqual(
            classify_settlement("packet", "Proof of the weak form and counterexample to the strict gloss"),
            ("statement_defective", "mixed"),
        )

    def test_public_source_identity_variants_are_preserved(self) -> None:
        identity = {
            "source_author": "Example Author",
            "openconjecture": {"id": 1688},
        }
        self.assertEqual(extract_authors(identity), ["Example Author"])
        self.assertEqual(extract_openconjecture_ids(identity), [1688])

    def test_statement_hash_prefers_claim_over_archive_and_reads_nested(self) -> None:
        identity = {
            "source_object": "Conjecture 1",
            "pdf": {"sha256": "a" * 64},
            "eprint": {"sha256": "b" * 64},
            "conjecture_excerpt": {"sha256": "c" * 64},
            "source_archive_sha256": "d" * 64,
        }
        statement = extract_statement(identity, "fallback")
        self.assertEqual(statement["content_sha256"], "c" * 64)
        self.assertEqual(statement["label"], "Conjecture 1")

    def test_statement_hash_falls_back_to_tex_or_packet(self) -> None:
        tex_only = extract_statement({"target": "slice", "source_tex_sha256": "e" * 64}, "role")
        self.assertEqual(tex_only["content_sha256"], "e" * 64)
        packet_only = extract_statement({"target": "slice", "packet_sha256": "f" * 64}, "role")
        self.assertEqual(packet_only["content_sha256"], "f" * 64)

    def test_python_and_nested_lean_routes_are_both_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory)
            (packet / "checkers").mkdir()
            (packet / "checkers" / "verify.py").write_text("print('PASS')\n", encoding="utf-8")
            (packet / "lean").mkdir()
            (packet / "lean" / "lakefile.lean").write_text("package Example\n", encoding="utf-8")
            routes = extract_routes(packet, "example-packet")
        self.assertEqual([route["kind"] for route in routes], ["python", "lean"])
        self.assertEqual(
            routes[1]["command"],
            "cd openconjectures/example-packet/lean && lake build",
        )


if __name__ == "__main__":
    unittest.main()

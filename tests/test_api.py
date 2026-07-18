from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from conjecture_records.api import make_handler
from conjecture_records.catalog import build_commentary_records, write_catalog


FIXTURE = Path(__file__).parent / "fixtures" / "commentary"


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        output = Path(self.temporary.name)
        records = build_commentary_records(FIXTURE, "1" * 40)
        write_catalog(records, "1" * 40, output)
        self.record_id = records[0]["record_id"]
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(output / "records.jsonl"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def get(self, path: str):
        with urlopen(self.base + path, timeout=3) as response:
            return response.status, json.load(response)

    def test_routes(self) -> None:
        status, health = self.get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["record_count"], 1)
        _, one = self.get(f"/records/{self.record_id}")
        self.assertEqual(one["record_id"], self.record_id)
        _, search = self.get("/search?q=fixture")
        self.assertEqual(search["count"], 1)
        _, stats = self.get("/stats")
        self.assertEqual(stats["status_counts"]["disproved"], 1)

    def test_missing_record(self) -> None:
        with self.assertRaises(HTTPError) as context:
            self.get("/records/cr_000000000000000000000000")
        self.assertEqual(context.exception.code, 404)
        context.exception.close()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .catalog import load_records


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def make_handler(records_path: Path):
    records = load_records(records_path)
    by_id = {record["record_id"]: record for record in records}

    class RecordsHandler(BaseHTTPRequestHandler):
        server_version = "FormalRecord"

        def log_message(self, format: str, *args: object) -> None:
            return

        def send_json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = _json_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == "/health":
                self.send_json({"status": "ok", "record_count": len(records)})
                return
            if parsed.path == "/records":
                status = query.get("status", [None])[0]
                result = [record for record in records if status is None or record["settlement"]["status"] == status]
                self.send_json({"count": len(result), "records": result})
                return
            if parsed.path.startswith("/records/"):
                record = by_id.get(unquote(parsed.path.removeprefix("/records/")))
                if record is None:
                    self.send_json({"error": "record_not_found"}, HTTPStatus.NOT_FOUND)
                else:
                    self.send_json(record)
                return
            if parsed.path == "/search":
                needle = query.get("q", [""])[0].casefold().strip()
                result = [
                    record
                    for record in records
                    if needle
                    and needle
                    in " ".join(
                        [
                            record["title"],
                            record["source"]["identifier"],
                            record["settlement"]["summary"],
                            *map(str, record["crosswalk"]["openconjecture_ids"]),
                        ]
                    ).casefold()
                ]
                self.send_json({"count": len(result), "records": result})
                return
            if parsed.path == "/stats":
                counts: dict[str, int] = {}
                for record in records:
                    status = record["settlement"]["status"]
                    counts[status] = counts.get(status, 0) + 1
                self.send_json({"record_count": len(records), "status_counts": dict(sorted(counts.items()))})
                return
            self.send_json({"error": "route_not_found"}, HTTPStatus.NOT_FOUND)

    return RecordsHandler


def serve(records_path: Path, host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(records_path))
    server.serve_forever()

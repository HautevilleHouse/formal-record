from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SAFE_METADATA_KEYS = frozenset(
    {
        "id",
        "openconjecture_id",
        "conjecture_id",
        "paper_id",
        "arxiv_id",
        "arxiv_identifier",
        "title",
        "paper_title",
        "authors",
        "category",
        "categories",
        "source_location",
        "environment",
        "label",
        "abs_url",
        "pdf_url",
        "source_url",
        "license",
        "license_url",
        "submitted_at",
        "updated_at",
        "publication_decision",
        "publication_text_reason",
        "publication_policy_version",
    }
)


def _first(record: dict[str, Any], *keys: str) -> Any:
    return next((record[key] for key in keys if key in record and record[key] not in (None, "")), None)


def import_metadata(path: Path, source_revision: str, source_url: str) -> dict[str, Any]:
    payload = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        public = {key: value[key] for key in sorted(SAFE_METADATA_KEYS & value.keys())}
        rows.append(
            {
                "openconjecture_id": _first(public, "openconjecture_id", "conjecture_id", "id"),
                "arxiv_id": _first(public, "arxiv_id", "paper_id", "arxiv_identifier"),
                "title": _first(public, "title", "paper_title"),
                "source_location": _first(public, "source_location", "environment", "label"),
                "publication_decision": public.get("publication_decision"),
                "publication_text_reason": public.get("publication_text_reason"),
                "publication_policy_version": public.get("publication_policy_version"),
                "metadata": public,
            }
        )
    rows.sort(key=lambda row: (str(row.get("arxiv_id") or ""), str(row.get("openconjecture_id") or "")))
    return {
        "schema_version": "1.0",
        "source": {
            "steward": "OpenConjecture",
            "url": source_url,
            "revision": source_revision,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "license_route": "https://huggingface.co/datasets/davisrbr/openconjecture",
            "body_policy": "metadata_only",
        },
        "record_count": len(rows),
        "records": rows,
    }

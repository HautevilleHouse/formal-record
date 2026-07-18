from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ARXIV_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)")


def import_tree(path: Path, source_revision: str, source_url: str) -> dict[str, Any]:
    payload = path.read_bytes()
    value = json.loads(payload)
    tree = value.get("tree") if isinstance(value, dict) else None
    if not isinstance(tree, list):
        raise ValueError("GitHub tree payload must contain a tree array")
    records: list[dict[str, Any]] = []
    for item in tree:
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        item_path = str(item.get("path", ""))
        if not item_path.endswith(".lean") or item_path.startswith("/") or ".." in item_path.split("/"):
            continue
        records.append(
            {
                "path": item_path,
                "blob_sha": item.get("sha"),
                "size": item.get("size"),
                "source_ids": sorted(set(ARXIV_RE.findall(item_path))),
            }
        )
    records.sort(key=lambda record: record["path"])
    return {
        "schema_version": "1.0",
        "source": {
            "steward": "Google DeepMind",
            "url": source_url,
            "revision": source_revision,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "license": "Apache-2.0",
            "body_policy": "tree_metadata_only",
        },
        "record_count": len(records),
        "records": records,
    }

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

ARXIV_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)")


def normalize_arxiv_id(value: str) -> str | None:
    match = ARXIV_RE.search(value)
    return match.group(1) if match else None


def build_crosswalk(
    openconjecture_records: list[dict[str, Any]],
    formal_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    oc_by_arxiv: dict[str, list[int]] = defaultdict(list)
    for record in openconjecture_records:
        arxiv_id = normalize_arxiv_id(str(record.get("arxiv_id", "")))
        record_id = record.get("openconjecture_id")
        if arxiv_id and isinstance(record_id, int):
            oc_by_arxiv[arxiv_id].append(record_id)

    formal_by_arxiv: dict[str, list[str]] = defaultdict(list)
    for entry in formal_entries:
        candidates = [str(entry.get("path", "")), *[str(value) for value in entry.get("source_ids", [])]]
        for candidate in candidates:
            if arxiv_id := normalize_arxiv_id(candidate):
                formal_by_arxiv[arxiv_id].append(str(entry["path"]))

    arxiv_ids = sorted(set(oc_by_arxiv) | set(formal_by_arxiv))
    rows = [
        {
            "arxiv_id": arxiv_id,
            "openconjecture_ids": sorted(set(oc_by_arxiv.get(arxiv_id, []))),
            "formal_conjectures_paths": sorted(set(formal_by_arxiv.get(arxiv_id, []))),
        }
        for arxiv_id in arxiv_ids
    ]
    return {
        "row_count": len(rows),
        "matched_count": sum(
            bool(row["openconjecture_ids"] and row["formal_conjectures_paths"]) for row in rows
        ),
        "rows": rows,
    }

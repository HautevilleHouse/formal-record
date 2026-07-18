from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

SCHEMA_VERSION = "1.0"
RECORD_ID_RE = re.compile(r"^cr_[0-9a-f]{24}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}v\d+$")

STATUSES = frozenset(
    {
        "open",
        "attacked",
        "partial",
        "proved",
        "disproved",
        "statement_defective",
        "superseded",
    }
)
RESULT_TYPES = frozenset(
    {
        "none",
        "proof",
        "counterexample",
        "classification",
        "computer_assisted_resolution",
        "statement_correction",
        "mixed",
    }
)
REVIEW_STATUSES = frozenset(
    {"unreviewed", "internal_replay", "external_reviewed", "author_confirmed"}
)
ROUTE_KINDS = frozenset(
    {"python", "lean", "cpp", "certificate", "manual", "symbolic"}
)


def _required(mapping: Mapping[str, Any], names: Iterable[str], prefix: str) -> list[str]:
    return [f"{prefix}.{name}: missing" for name in names if name not in mapping]


def validate_record(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _required(
            record,
            (
                "schema_version",
                "record_id",
                "title",
                "source",
                "crosswalk",
                "statement",
                "settlement",
                "verification",
                "review",
                "rights",
                "provenance",
            ),
            "record",
        )
    )
    if errors:
        return errors

    if record["schema_version"] != SCHEMA_VERSION:
        errors.append("record.schema_version: unsupported")
    if not isinstance(record["record_id"], str) or not RECORD_ID_RE.fullmatch(
        record["record_id"]
    ):
        errors.append("record.record_id: expected cr_ followed by 24 lowercase hex digits")
    if not isinstance(record["title"], str) or not record["title"].strip():
        errors.append("record.title: expected non-empty string")

    source = record["source"]
    if not isinstance(source, Mapping):
        errors.append("record.source: expected object")
    else:
        errors.extend(_required(source, ("kind", "identifier", "url"), "record.source"))
        if source.get("kind") == "arxiv" and not ARXIV_RE.fullmatch(
            str(source.get("identifier", ""))
        ):
            errors.append("record.source.identifier: expected versioned arXiv identifier")
        if not str(source.get("url", "")).startswith("https://"):
            errors.append("record.source.url: expected https URL")

    crosswalk = record["crosswalk"]
    if not isinstance(crosswalk, Mapping):
        errors.append("record.crosswalk: expected object")
    else:
        oc_ids = crosswalk.get("openconjecture_ids")
        formal_paths = crosswalk.get("formal_conjectures_paths")
        if not isinstance(oc_ids, list) or any(
            not isinstance(value, int) or value < 0 for value in oc_ids
        ):
            errors.append("record.crosswalk.openconjecture_ids: expected nonnegative integers")
        if not isinstance(formal_paths, list) or any(
            not isinstance(value, str) or value.startswith("/") or ".." in value.split("/")
            for value in formal_paths
        ):
            errors.append("record.crosswalk.formal_conjectures_paths: unsafe relative path")

    settlement = record["settlement"]
    if not isinstance(settlement, Mapping):
        errors.append("record.settlement: expected object")
    else:
        errors.extend(
            _required(settlement, ("status", "result_type", "summary", "packet_url"), "record.settlement")
        )
        if settlement.get("status") not in STATUSES:
            errors.append("record.settlement.status: unsupported")
        if settlement.get("result_type") not in RESULT_TYPES:
            errors.append("record.settlement.result_type: unsupported")
        if not str(settlement.get("packet_url", "")).startswith("https://github.com/"):
            errors.append("record.settlement.packet_url: expected GitHub URL")

    verification = record["verification"]
    if not isinstance(verification, Mapping):
        errors.append("record.verification: expected object")
    else:
        routes = verification.get("routes")
        if not isinstance(routes, list) or not routes:
            errors.append("record.verification.routes: expected at least one route")
        else:
            for index, route in enumerate(routes):
                if not isinstance(route, Mapping):
                    errors.append(f"record.verification.routes[{index}]: expected object")
                    continue
                if route.get("kind") not in ROUTE_KINDS:
                    errors.append(f"record.verification.routes[{index}].kind: unsupported")
                if not isinstance(route.get("command"), str) or not route["command"].strip():
                    errors.append(f"record.verification.routes[{index}].command: missing")

    review = record["review"]
    if not isinstance(review, Mapping) or review.get("status") not in REVIEW_STATUSES:
        errors.append("record.review.status: unsupported")

    provenance = record["provenance"]
    if not isinstance(provenance, Mapping):
        errors.append("record.provenance: expected object")
    else:
        digest = provenance.get("source_identity_sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append("record.provenance.source_identity_sha256: expected SHA-256")

    return errors


def validate_catalog(catalog: Mapping[str, Any], records: list[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _required(
            catalog,
            ("schema_version", "source_revision", "record_count", "records_sha256", "status_counts"),
            "catalog",
        )
    )
    if errors:
        return errors
    if catalog["schema_version"] != SCHEMA_VERSION:
        errors.append("catalog.schema_version: unsupported")
    if catalog["record_count"] != len(records):
        errors.append("catalog.record_count: mismatch")
    ids = [record.get("record_id") for record in records]
    if len(ids) != len(set(ids)):
        errors.append("records: duplicate record_id")
    for index, record in enumerate(records):
        errors.extend(f"records[{index}].{error}" for error in validate_record(record))
    return errors

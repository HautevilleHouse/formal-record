from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .schema import SCHEMA_VERSION, validate_catalog

ARXIV_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5}v\d+)(?!\d)")
README_ROW_RE = re.compile(
    r"^\| \[(?P<title>[^]]+)\]\(openconjectures/(?P<slug>[^/)]+)/?\)"
    r" \| (?P<source>.*?) \| (?P<role>.*?) \|$"
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_record_id(source_identifier: str, packet_slug: str) -> str:
    key = f"arxiv\0{source_identifier}\0{packet_slug}".encode()
    return "cr_" + hashlib.sha256(key).hexdigest()[:24]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def read_commentary_index(readme: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in readme.read_text(encoding="utf-8").splitlines():
        match = README_ROW_RE.fullmatch(line)
        if match:
            row = match.groupdict()
            rows[row["slug"]] = row
    return rows


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def extract_arxiv_id(identity: dict[str, Any]) -> str:
    preferred = [
        identity.get("arxiv_id"),
        identity.get("source_id"),
        identity.get("identifier"),
        identity.get("eprint"),
        (identity.get("arxiv") or {}).get("identifier")
        if isinstance(identity.get("arxiv"), dict)
        else None,
    ]
    for value in [*preferred, *_walk_strings(identity)]:
        if isinstance(value, str) and (match := ARXIV_RE.search(value)):
            return match.group(1)
    raise ValueError("source_identity.json has no versioned arXiv identifier")


def extract_title(identity: dict[str, Any], fallback: str) -> str:
    nested = identity.get("arxiv")
    candidates = [
        identity.get("title"),
        identity.get("source_title"),
        nested.get("title") if isinstance(nested, dict) else None,
        fallback,
    ]
    return next(str(value).strip() for value in candidates if isinstance(value, str) and value.strip())


def extract_authors(identity: dict[str, Any]) -> list[str]:
    nested = identity.get("arxiv")
    value = identity.get("authors")
    if value is None and isinstance(nested, dict):
        value = nested.get("authors")
    if value is None:
        value = identity.get("source_authors")
    if value is None:
        value = identity.get("source_author")
    if value is None and identity.get("author"):
        value = [identity["author"]]
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def extract_openconjecture_ids(identity: dict[str, Any]) -> list[int]:
    values: list[Any] = []
    for key in ("openconjecture_id", "openconjecture_ids"):
        value = identity.get(key)
        if isinstance(value, list):
            values.extend(value)
        elif value is not None:
            values.append(value)
    nested = identity.get("openconjecture")
    if isinstance(nested, dict):
        value = nested.get("id", nested.get("ids"))
        if isinstance(value, list):
            values.extend(value)
        elif value is not None:
            values.append(value)
    result: list[int] = []
    for item in values:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str) and item.isdigit():
            result.append(int(item))
    return sorted(set(result))


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_STATEMENT_HASH_PRIORITY: tuple[tuple[str, ...], ...] = (
    ("claim", "statement", "conjecture", "content", "row", "excerpt"),
    ("tex", "payload", "file", "source_statement"),
    ("packet",),
    ("archive", "eprint", "downloaded"),
    ("pdf",),
)


def _collect_sha256_entries(identity: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    """Collect sha256 fields; reject fat-finger / truncated digests instead of skipping them."""
    entries: list[tuple[str, str]] = []
    for key, value in identity.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, str) and "sha256" in key.lower():
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(
                    f"{path}: expected lowercase hex SHA-256 of exactly 64 characters, "
                    f"got length {len(value)}"
                )
            entries.append((path, value))
        elif isinstance(value, dict):
            entries.extend(_collect_sha256_entries(value, path))
    return entries


def _statement_hash_sort_key(path: str) -> tuple[int, str]:
    lowered = path.lower()
    for index, words in enumerate(_STATEMENT_HASH_PRIORITY):
        if any(word in lowered for word in words):
            return (index, path)
    return (len(_STATEMENT_HASH_PRIORITY), path)


def extract_statement(identity: dict[str, Any], role: str) -> dict[str, Any]:
    label_candidates = [
        identity.get("source_object"),
        identity.get("target"),
        identity.get("claim"),
        identity.get("statement"),
        identity.get("open_problem"),
    ]
    label = next(
        (str(value).strip() for value in label_candidates if isinstance(value, (str, int)) and str(value).strip()),
        role,
    )
    location_candidates = [
        identity.get("source_lines"),
        identity.get("source_statement_lines"),
        identity.get("conjecture_lines"),
        identity.get("source_statement_boundary"),
        identity.get("source_lines_used"),
        identity.get("source_line_anchors"),
    ]
    location_value = next((value for value in location_candidates if value), None)
    location = json.dumps(location_value, sort_keys=True) if isinstance(location_value, (dict, list)) else location_value
    hashes = _collect_sha256_entries(identity)
    hashes.sort(key=lambda item: _statement_hash_sort_key(item[0]))
    if not hashes:
        raise ValueError(f"Missing statement.content_sha256 for target: {label}")
    return {
        "label": label,
        "location": str(location) if location else None,
        "content_sha256": hashes[0][1],
    }


def classify_settlement(slug: str, role: str) -> tuple[str, str]:
    text = f"{slug} {role}".lower()
    if "proof" in text and "counterexample" in text:
        return "statement_defective", "mixed"
    if "counterexample" in text or "disproof" in text or "obstruction" in text:
        return "disproved", "counterexample"
    if "classification" in text:
        return "proved", "classification"
    if "computer-assisted" in text or "computer assisted" in text or "unique-multiset" in text:
        return "proved", "computer_assisted_resolution"
    if "correction" in text or "statement-defective" in text:
        return "statement_defective", "statement_correction"
    if "proof" in text or "inequalities" in text or "reciprocity" in text or "normalized values" in text or "bijection" in text:
        return "proved", "proof"
    return "partial", "mixed"


def _receipt_commands(packet_dir: Path) -> list[str]:
    commands: list[str] = []
    for path in sorted(packet_dir.rglob("*.json")):
        if "receipt" not in path.name.lower():
            continue
        try:
            receipt = _read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        value = receipt.get("commands", receipt.get("command"))
        if isinstance(value, str):
            commands.append(value)
        elif isinstance(value, dict):
            commands.extend(str(value[key]) for key in sorted(value) if isinstance(value[key], str))
        elif isinstance(value, list):
            commands.extend(str(item) for item in value if isinstance(item, str))
    return sorted(set(commands))


def _route_kind(command: str) -> str:
    lowered = command.lower()
    if "lake build" in lowered:
        return "lean"
    if "python" in lowered:
        return "python"
    if "c++" in lowered or "g++" in lowered or "clang++" in lowered:
        return "cpp"
    return "manual"


def extract_routes(packet_dir: Path, slug: str) -> list[dict[str, str]]:
    commands = _receipt_commands(packet_dir)
    if not commands:
        checkers = sorted(path for path in packet_dir.rglob("*.py") if "check" in path.parts or "checkers" in path.parts)
        commands.extend(f"python3 openconjectures/{slug}/{path.relative_to(packet_dir)}" for path in checkers[:2])
    if not any(_route_kind(command) == "lean" for command in commands):
        lakefiles = sorted([*packet_dir.rglob("lakefile.toml"), *packet_dir.rglob("lakefile.lean")])
        for lakefile in lakefiles:
            relative = lakefile.parent.relative_to(packet_dir)
            working_directory = Path("openconjectures") / slug / relative
            commands.append(f"cd {working_directory} && lake build")
    if not commands:
        commands.append(f"inspect openconjectures/{slug}/README.md and packet certificate files")
    return [{"kind": _route_kind(command), "command": command} for command in commands]


def _license_url(identity: dict[str, Any]) -> str | None:
    candidates = [
        identity.get("license_url"),
        identity.get("source_license"),
        identity.get("source_license_family"),
    ]
    return next((str(value) for value in candidates if isinstance(value, str) and value.startswith("https://")), None)


def build_commentary_records(commentary_root: Path, source_revision: str) -> list[dict[str, Any]]:
    index = read_commentary_index(commentary_root / "README.md")
    records: list[dict[str, Any]] = []
    packets_root = commentary_root / "openconjectures"
    for identity_path in sorted(packets_root.glob("*/data/source_identity.json")):
        packet_dir = identity_path.parent.parent
        slug = packet_dir.name
        identity_bytes = identity_path.read_bytes()
        identity = json.loads(identity_bytes)
        # The packet directory is authoritative when the human README index
        # lags behind Commentary HEAD.  Derive a deterministic fallback row so
        # catalog rebuilds do not silently omit newly published packets.
        row = index.get(slug)
        if row is None:
            packet_readme = packet_dir / "README.md"
            heading = slug.replace("-", " ").title()
            if packet_readme.exists():
                for line in packet_readme.read_text(encoding="utf-8").splitlines():
                    if line.startswith("# "):
                        heading = line[2:].strip()
                        break
            row = {
                "slug": slug,
                "title": heading,
                "source": str(identity.get("source", identity.get("source_url", ""))),
                "role": str(identity.get("scope", identity.get("target", "bounded packet"))),
            }
        try:
            arxiv_id = extract_arxiv_id(identity)
        except ValueError:
            # Formal-Conjectures-only packets may have no arXiv identifier;
            # retain them in Commentary but leave them outside this arXiv-keyed
            # catalog until a versioned source identifier is recorded.
            continue
        source_url = f"https://arxiv.org/abs/{arxiv_id}"
        status, result_type = classify_settlement(slug, row["role"])
        record = {
            "schema_version": SCHEMA_VERSION,
            "record_id": stable_record_id(arxiv_id, slug),
            "title": extract_title(identity, row["title"]),
            "authors": extract_authors(identity),
            "source": {
                "kind": "arxiv",
                "identifier": arxiv_id,
                "url": source_url,
            },
            "crosswalk": {
                "openconjecture_ids": extract_openconjecture_ids(identity),
                "formal_conjectures_paths": [],
            },
            "statement": extract_statement(identity, row["source"]),
            "settlement": {
                "status": status,
                "result_type": result_type,
                "summary": row["role"],
                "packet_url": f"https://github.com/HautevilleHouse/commentary/tree/main/openconjectures/{slug}",
            },
            "verification": {
                "evidence": "packet_replay",
                "routes": extract_routes(packet_dir, slug),
            },
            "review": {"status": "internal_replay"},
            "rights": {
                "record_notice": "All Rights Reserved - No License Granted",
                "upstream_license_url": _license_url(identity),
            },
            "provenance": {
                "source_repository": "https://github.com/HautevilleHouse/commentary",
                "source_revision": source_revision,
                "source_identity_path": f"openconjectures/{slug}/data/source_identity.json",
                "source_identity_sha256": sha256_bytes(identity_bytes),
            },
        }
        records.append(record)
    return sorted(records, key=lambda item: item["record_id"])


def write_catalog(records: list[dict[str, Any]], source_revision: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records_payload = b"".join(canonical_bytes(record) for record in records)
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "source_revision": source_revision,
        "record_count": len(records),
        "records_sha256": sha256_bytes(records_payload),
        "status_counts": dict(sorted(Counter(record["settlement"]["status"] for record in records).items())),
        "result_type_counts": dict(
            sorted(Counter(record["settlement"]["result_type"] for record in records).items())
        ),
    }
    errors = validate_catalog(catalog, records)
    if errors:
        raise ValueError("\n".join(errors))
    (output_dir / "records.jsonl").write_bytes(records_payload)
    (output_dir / "catalog.json").write_bytes(canonical_bytes(catalog))
    return catalog


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        records.append(value)
    return records

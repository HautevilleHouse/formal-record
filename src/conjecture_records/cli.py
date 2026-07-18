from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from .api import serve
from .catalog import build_commentary_records, canonical_bytes, load_records, write_catalog
from .crosswalk import build_crosswalk
from .importers.formal_conjectures import import_tree
from .importers.openconjecture import import_metadata
from .schema import validate_catalog
from .verify import execute_plans, plan_routes


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def command_build_commentary(args: argparse.Namespace) -> int:
    records = build_commentary_records(args.commentary_root, args.source_revision)
    catalog = write_catalog(records, args.source_revision, args.output)
    _print({"status": "ok", **catalog})
    return 0


def command_validate(args: argparse.Namespace) -> int:
    records = load_records(args.records)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    payload = b"".join(canonical_bytes(record) for record in records)
    errors = validate_catalog(catalog, records)
    digest = hashlib.sha256(payload).hexdigest()
    if catalog.get("records_sha256") != digest:
        errors.append("catalog.records_sha256: mismatch")
    _print({"status": "ok" if not errors else "fail", "record_count": len(records), "errors": errors})
    return 0 if not errors else 1


def command_import_openconjecture(args: argparse.Namespace) -> int:
    result = import_metadata(args.input, args.source_revision, args.source_url)
    _write_json(args.output, result)
    _print({"status": "ok", "record_count": result["record_count"], "body_policy": "metadata_only"})
    return 0


def command_import_formal(args: argparse.Namespace) -> int:
    result = import_tree(args.input, args.source_revision, args.source_url)
    _write_json(args.output, result)
    _print({"status": "ok", "record_count": result["record_count"], "body_policy": "tree_metadata_only"})
    return 0


def command_crosswalk(args: argparse.Namespace) -> int:
    openconjecture = json.loads(args.openconjecture.read_text(encoding="utf-8"))
    formal = json.loads(args.formal.read_text(encoding="utf-8"))
    result = build_crosswalk(openconjecture["records"], formal["records"])
    _write_json(args.output, result)
    _print({"status": "ok", "row_count": result["row_count"], "matched_count": result["matched_count"]})
    return 0


def command_stats(args: argparse.Namespace) -> int:
    records = load_records(args.records)
    _print(
        {
            "record_count": len(records),
            "status_counts": dict(sorted(Counter(record["settlement"]["status"] for record in records).items())),
            "openconjecture_crosswalk_count": sum(bool(record["crosswalk"]["openconjecture_ids"]) for record in records),
            "formal_crosswalk_count": sum(bool(record["crosswalk"]["formal_conjectures_paths"]) for record in records),
        }
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    records = load_records(args.records)
    selected = [record for record in records if args.record_id in (None, record["record_id"])]
    if args.record_id and not selected:
        _print({"status": "fail", "error": "record_not_found"})
        return 1
    output = []
    failed = False
    for record in selected:
        plans = plan_routes(record, args.commentary_root)
        results = execute_plans(plans, args.timeout) if args.execute else plans
        if args.execute and any(result.get("status") == "failed" for result in results):
            failed = True
        output.append({"record_id": record["record_id"], "routes": results})
    _print({"status": "fail" if failed else "ok", "execute": args.execute, "records": output})
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="formal-record")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-commentary", help="build deterministic records from commentary packets")
    build.add_argument("--commentary-root", type=Path, required=True)
    build.add_argument("--source-revision", required=True)
    build.add_argument("--output", type=Path, required=True)
    build.set_defaults(func=command_build_commentary)

    validate = subparsers.add_parser("validate", help="validate records and catalog digest")
    validate.add_argument("--records", type=Path, default=Path("registry/records.jsonl"))
    validate.add_argument("--catalog", type=Path, default=Path("registry/catalog.json"))
    validate.set_defaults(func=command_validate)

    oc = subparsers.add_parser("import-openconjecture", help="import OpenConjecture metadata without statement bodies")
    oc.add_argument("--input", type=Path, required=True)
    oc.add_argument("--source-revision", required=True)
    oc.add_argument("--source-url", required=True)
    oc.add_argument("--output", type=Path, required=True)
    oc.set_defaults(func=command_import_openconjecture)

    formal = subparsers.add_parser("import-formal-conjectures", help="import DeepMind Git tree metadata")
    formal.add_argument("--input", type=Path, required=True)
    formal.add_argument("--source-revision", required=True)
    formal.add_argument("--source-url", required=True)
    formal.add_argument("--output", type=Path, required=True)
    formal.set_defaults(func=command_import_formal)

    crosswalk = subparsers.add_parser("crosswalk", help="crosswalk two metadata snapshots by arXiv id")
    crosswalk.add_argument("--openconjecture", type=Path, required=True)
    crosswalk.add_argument("--formal", type=Path, required=True)
    crosswalk.add_argument("--output", type=Path, required=True)
    crosswalk.set_defaults(func=command_crosswalk)

    stats = subparsers.add_parser("stats", help="summarize current records")
    stats.add_argument("--records", type=Path, default=Path("registry/records.jsonl"))
    stats.set_defaults(func=command_stats)

    verify = subparsers.add_parser("verify", help="plan or execute allowlisted packet replay routes")
    verify.add_argument("--records", type=Path, default=Path("registry/records.jsonl"))
    verify.add_argument("--commentary-root", type=Path, required=True)
    verify.add_argument("--record-id")
    verify.add_argument("--execute", action="store_true")
    verify.add_argument("--timeout", type=int, default=300)
    verify.set_defaults(func=command_verify)

    server = subparsers.add_parser("serve", help="serve the read-only local API")
    server.add_argument("--records", type=Path, default=Path("registry/records.jsonl"))
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8080)
    server.set_defaults(func=lambda args: (serve(args.records, args.host, args.port), 0)[1])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        _print({"status": "fail", "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())

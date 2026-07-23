# Formal Record

Formal Record is a source-bound catalog of mathematical conjectures and checked outcomes published by [HautevilleHouse Commentary](https://github.com/HautevilleHouse/commentary).

The repository gives each result a stable identifier, source version, crosswalk, replay route, review state, and public packet link. It stays compact: upstream projects remain with their original stewards, and this repository records links and metadata instead of mirroring their corpora.

## Current Catalog

- 39 source-bound result packets
- versioned arXiv identifiers for every record
- OpenConjecture identifiers when the source packet supplies one
- packet replay routes and source-identity hashes
- read-only search and statistics API

The generated catalog lives in [`registry/records.jsonl`](registry/records.jsonl). [`registry/catalog.json`](registry/catalog.json) binds its record count, outcome counts, source revision, and SHA-256 digest.

## Repository Roles

| Surface | Role |
|---|---|
| [commentary](https://github.com/HautevilleHouse/commentary) | Human-readable proofs, counterexamples, certificates, and replay packets |
| [formal-record](https://github.com/HautevilleHouse/formal-record) | Machine-readable index, crosswalk, replay policy, and read-only API |
| arXiv and cited papers | Source statements and version history |
| OpenConjecture | Upstream conjecture discovery metadata |
| DeepMind Formal Conjectures | Upstream Lean statement metadata |

## Use

The package has no runtime dependencies beyond Python.

```bash
python3 -m pip install -e .
formal-record validate
formal-record stats
formal-record serve --host 127.0.0.1 --port 8080
```

The local API exposes:

```text
GET /health
GET /records
GET /records/{record_id}
GET /records?status=disproved
GET /search?q=cycle
GET /stats
```

## Deterministic Build

Generate the catalog from a checked Commentary revision:

```bash
formal-record build-commentary \
  --commentary-root /path/to/commentary \
  --source-revision COMMIT_SHA \
  --output registry
```

The build reads each packet's public `source_identity.json`, replay receipt, and root index row. It emits stable ordering and canonical JSON bytes, so the same source revision produces the same catalog digest.

## Upstream Crosswalks

The importers are metadata-first:

```bash
formal-record import-openconjecture \
  --input conjectures.jsonl \
  --source-revision DATASET_COMMIT \
  --source-url https://huggingface.co/datasets/davisrbr/openconjecture \
  --output .tmp/openconjecture.json

formal-record import-formal-conjectures \
  --input github-tree.json \
  --source-revision REPOSITORY_COMMIT \
  --source-url https://github.com/google-deepmind/formal-conjectures \
  --output .tmp/formal-conjectures.json

formal-record crosswalk \
  --openconjecture .tmp/openconjecture.json \
  --formal .tmp/formal-conjectures.json \
  --output .tmp/crosswalk.json
```

The OpenConjecture importer removes statement-body fields. The DeepMind importer reads Git tree metadata without copying Lean files. [`docs/UPSTREAMS.md`](docs/UPSTREAMS.md) records the source and rights boundary.

## Replay Policy

`formal-record verify` accepts only narrow Python checker and Lean build command shapes. It rejects absolute paths, parent traversal, command substitution, pipes, redirects, and unlisted executables. Planning is the default; execution requires `--execute` and a local Commentary checkout.

```bash
formal-record verify --commentary-root /path/to/commentary
```

## Claim Boundary

This catalog identifies the public packet and the checks recorded by that packet. The cited source controls the original statement. Each Commentary packet controls its bounded mathematical claim, dependencies, and carried remainder. Internal replay and external review remain distinct fields.

## Citation And Rights

Cite the relevant record, Commentary packet, original source, and upstream identifier. See [`CITATION.cff`](CITATION.cff).

All Rights Reserved - No License Granted. Third-party metadata remains subject to the rights and terms of its original steward. No patent license is granted.

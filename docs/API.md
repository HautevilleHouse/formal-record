# Read-Only API

The reference server reads a generated JSONL catalog into memory and exposes JSON over HTTP.

| Route | Result |
|---|---|
| `/health` | Service status and record count |
| `/records` | All records, optionally filtered by `status` |
| `/records/{record_id}` | One exact record |
| `/search?q=...` | Case-insensitive search over title, source id, summary, and OpenConjecture id |
| `/stats` | Catalog and status counts |

The server binds to `127.0.0.1` by default and performs no mutation. A production host should add its own authentication, caching, rate limits, observability, and availability controls around this read-only contract.

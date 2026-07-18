# Record Schema

Each line of `registry/records.jsonl` is one record.

| Field | Role |
|---|---|
| `record_id` | Stable identifier derived from the versioned source id and packet slug |
| `source` | Versioned source identity and public URL |
| `crosswalk` | OpenConjecture ids and DeepMind formal-statement paths when established |
| `statement` | Source label, location, and content hash when published by the packet |
| `settlement` | Bounded status, result type, summary, and Commentary packet URL |
| `verification` | Declarative replay routes and evidence class |
| `review` | Internal replay, external review, or author-confirmation state |
| `rights` | Record notice and upstream license route |
| `provenance` | Public source repository, revision, path, and identity-file hash |

Statuses are `open`, `attacked`, `partial`, `proved`, `disproved`, `statement_defective`, and `superseded`. Review state remains orthogonal to mathematical status.

The normative machine-readable shape is [`schema/record.schema.json`](../schema/record.schema.json).

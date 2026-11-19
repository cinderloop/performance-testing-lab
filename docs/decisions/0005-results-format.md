# ADR 0005: Results format and layout

- Status: **Accepted** (2026-11-20, Phase 1)

## Context

Ground rule 1 says every number must come from a real run whose raw data and manifest are committed or reproducible. Analysis needs per-request data. k6's end-of-test summary only holds per-run aggregates, which can't be combined across runs (spike §14: for checkout, the mean of per-run p95s was 70 ms against a pooled p95 of 127 ms). The spike also showed that k6's default summary mixes failures into `http_req_duration`.

## Decision

`perflab run` writes one directory per run, `results/<run-id>/`. The run ID is `<UTC yyyymmddThhmmssZ>-<script stem>-<4 hex>`.

| File | Content | Role |
|---|---|---|
| `manifest.json` | everything the plan's "Run manifest" section lists, plus `valid` and `invalid_reasons` | **judging and reproducing** the run |
| `k6-raw.json.gz` | k6 `--out json`, one JSON line per sample, gzip | **source of truth for analysis** |
| `k6-summary.json` | k6's `handleSummary` data, unchanged | convenience, never used for cross-run statistics |
| `k6-stdout.log` | k6 console output, including the text summary | human reading |
| `k6-resources.csv` | the k6 container's CPU (cores) and memory, about once per second, from the Docker stats API | load-generator health (Phase 4.6) |
| `reset.json` | the reset protocol's checks and idle CPU per container | proof the reset ran and passed |

- Raw output is JSON lines rather than CSV. JSON keeps every tag plus `metadata.trace_id` (needed for trace correlation in Phase 3), and gzip keeps it small: the 40-request foundation check compressed to about 6 KB.
- Every request carries a `name` tag (endpoint id), `endpoint_group`, and the run-wide `run_id`. The `url` system tag is dropped, so raw files and any metrics store stay bounded in cardinality.
- The text summary always shows success and failure latency on separate lines, with the error rate beside them.
- Results are committed. Runs made under invalid conditions are kept, marked invalid, and never used for comparison. Large raw files stay gzipped. If the repo grows too big, that's a separate decision; nothing gets deleted silently.

## Consequences

- Analysis code (Phase 4) reads `k6-raw.json.gz` and `manifest.json` only.
- `manifest.json` records the exact `docker create` command for k6, and `command.perflab` the CLI invocation. Together with the git commit, that reproduces the run.

## Amendment 2026-11-20 (Phase 2): full raw output is not committed

The first breakpoint run (25 min) produced an 86 MB `k6-raw.json.gz`. k6 writes about ten metric lines per request (`http_req_blocked`, `…_connecting`, `…_waiting` …, plus one per check), and the soak and breakpoint runs would go over GitHub's 100 MB file limit. Decided with the owner:

- **Committed:** `samples.csv.gz`, derived from the raw file by `analysis.compact`. It has one row per request, session end and dropped session, with every field analysis uses kept verbatim: k6's timestamp, the duration, and the `expected_response`, `name`, `endpoint_group`, `status`, `error_code`, `journey`, `step` and `scenario` tags. A unit test proves analysis gives identical results from either file, and the reports of the first two Phase 2 runs were rebuilt from both and compared equal. It's about 9% of the raw size.
- **Not committed:** `k6-raw.json.gz` (git-ignored). It's kept locally and published as a **GitHub Release asset** for each phase. `raw_archive.json` in the run directory records its size and SHA-256, so a downloaded copy can be verified.
- Runs from Phase 1 keep their already-committed (small) raw files.
- `metadata.trace_id` isn't in the compact file yet. Phase 3 adds a column for it when trace correlation is wired in.

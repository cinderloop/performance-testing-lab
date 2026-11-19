# ADR 0008: Explicit request timeouts

- Status: **Accepted** (2026-11-20, Phase 1)
- Evidence: [spike-findings.md §3, §11, §15](../spike-findings.md)

## Context

k6's default request timeout is 60 s. That's far longer than any user waits, and in a closed model a stalled VU stops generating load for up to a minute, which hides problems (Phase 4.2). When a request times out, k6 reports `status=0`, `error_code=1050` and counts it in `http_req_failed`. Spike data points:

- The worst real request observed was 6.1 s: a checkout during the GC spiral.
- Fault flags inject 5 s or 10 s delays (`imageSlowLoad`, `intlShippingSlowdown`).

## Decision

- **One run-wide timeout, 10 s by default**, set explicitly on every request by `k6/lib/http.ts`. It comes from `TIMEOUT_MS` (100–60,000 ms, validated), which the runner always passes and records as `request_timeout_ms` in the manifest.
- 10 s stands in for "a user has given up". **That's an assumption**, not a measured figure, since there's no production data to derive it from.
- **A timeout is a failure.** It's a non-expected response: k6 tags it `expected_response=false` and counts it in `http_req_failed`. Its duration goes into failure latency, not success latency.
- Individual requests may override the timeout in code (`timeoutMs`), for example an experiment that wants a fault's full delay visible. The override is in the script, so the git commit records it.
- Fault-flag variants are chosen with the timeout in mind:
  - 5 s delays show as latency.
  - 10 s delays sit exactly at the boundary, and an experiment using them must say which side it wants.

## Consequences

- Stalls longer than 10 s appear as errors with a known code, not as one huge latency.
- Timeout counts must be reported next to latency (measurement rules). The text summary already shows failures separately, and Phase 3 dashboards will show timeouts as their own series.

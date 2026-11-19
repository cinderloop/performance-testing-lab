# Thresholds (PROVISIONAL)

Everything on this page is **provisional**. Phase 4.8 replaces it with thresholds derived from stated example SLOs and the measured baseline and run-to-run variance, recorded in an ADR. Until then these values are generous, SLO-style limits chosen up front. They were **not** tuned to this laptop's measured latency, so they can't be "passed by construction".

## k6 thresholds (`k6/lib/thresholds.ts`)

Latency thresholds count **successful requests only** (`expected_response:true`). Failures are counted by the error-rate threshold instead, because fast failures would otherwise make latency look better.

| Metric | Threshold | Reasoning |
|---|---|---|
| Error rate (`http_req_failed`) | < 1% | a shop that fails 1 request in 100 is visibly broken |
| Checks (`checks`) | > 99% | content checks catch wrong answers with a 200 status |
| Page documents, success p95 | < 1000 ms | server time for the HTML only, so well under a typical page-load budget |
| API calls, success p95 | < 500 ms | a page makes 3–10 of these, partly in sequence |
| Flag evaluation, success p95 | < 500 ms | blocks feature rendering on every page |
| Checkout, success p95 | < 2000 ms | does the most work (payment, shipping, email, Kafka), and users tolerate a slower "place order" |

The Python analysis mirrors the per-group and error-rate limits (`src/analysis/criteria.py`), and a unit test fails if the two disagree.

## Where they apply

| Scenario | k6 thresholds | Computed criterion (`perflab report`, from raw data) |
|---|---|---|
| smoke | all of the above, plus **zero** failed requests and **100%** checks | none |
| load | all of the above | none |
| stress | none: exceeding them is the point | **recovery** |
| spike | none | **recovery** |
| soak | all of the above | **soak trend** |
| breakpoint | abort conditions only (below) | **breakpoint** |

## Computed criteria

All use **10 s windows** by request start time, matching the 10 s server-side metric resolution. All are provisional.

**Breakpoint:**
- A window *fails* when its error rate is ≥ 1%, or when a group with at least 20 successes in the window has a success p95 at or above its limit (page 1000 ms, API 500 ms, flags 500 ms).
- The breakpoint is the planned arrival rate at the start of the last good window before the **first 3 consecutive failing windows** (30 s).

**Recovery (stress, spike):**
- The baseline is the second half of the `baseline` phase: success p95 `p95_b` and error rate `e_b`.
- Recovered means 3 consecutive windows with at least 20 successes, success p95 ≤ max(1.5 × `p95_b`, `p95_b` + 25 ms), and error rate ≤ `e_b` + 1 percentage point.
- Time to recover is measured from the start of the load drop to the start of the first of those windows.
- If it doesn't happen within the 6-minute recovery phase, the result is "not recovered", reported as such.

**Soak trend:**
- Compares success p95 over the last 10 minutes of the steady phase with the first 10 minutes.
- **Degraded** if the ratio is above 1.2.

## Breakpoint stop condition (`k6/scenarios/breakpoint.ts`)

k6 aborts the run (`abortOnFail`, evaluation delayed 60 s) when:
- the error rate exceeds 5%, or
- success p95 exceeds 3 s, or
- more than 100 sessions couldn't start (VUs exhausted).

k6 evaluates thresholds over everything since the start, not per window, so the abort comes **after** the real breaking point. That's fine: it only has to end the run cleanly. The breakpoint itself is computed from the windows above. The ramp's end, 3000 sessions/min after 25 min, bounds the run regardless.

## What to expect in Phase 4.8

- Thresholds per endpoint group derived from example SLOs (for example "99% of API calls under 300 ms over a run").
- A threshold is set only where the measured run-to-run variance (Phase 4.7) shows it can tell a real regression from noise.

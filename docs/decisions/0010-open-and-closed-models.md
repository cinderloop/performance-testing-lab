# ADR 0010: Open workload model for load scenarios; closed only for smoke

- Status: **Accepted** (2026-11-20, Phase 2)

## Context

In a **closed** model, a fixed number of VUs loop: each starts its next session only when the previous one finishes. When the system slows down, the VUs slow down too and offered load falls, which hides the slowdown. This is coordinated omission, demonstrated in Phase 4.1 and 4.2. In an **open** model, sessions arrive at a set rate regardless of response time, as independent shoppers do, so a slowdown shows up as growing latency, queueing and eventually `dropped_iterations`.

## Decision

- **load, stress, spike, soak and breakpoint use an open model:** k6 `ramping-arrival-rate`, rates in sessions per minute (`timeUnit: 1m`), with each scenario's shape declared as named phases (`k6/lib/phases.ts`). The same declaration feeds k6 and the analysis.
- **smoke uses a closed model** (`per-vu-iterations`, 1 VU, 6 sessions). Its job is to prove every journey works, not to model load.
- VU pools are sized by Little's Law with headroom. `dropped_iterations` (sessions k6 couldn't start because every VU was busy) is always reported, and in the breakpoint scenario it's an abort condition.
- The closed model stays available for the open-vs-closed experiment (Phase 4.1), where showing what it hides is the point.

## Consequences

- Offered load is known exactly from the plan, and achieved throughput can be compared against it.
- When the system can't keep up, an open model grows concurrency without bound. The VU cap (`maxVUs`) bounds k6's memory; beyond it, sessions are dropped and counted, never silently skipped.

# ADR 0003: Memory limits for the Go services with `GOMEMLIMIT=16MiB`

- Status: **Accepted** (2026-11-20, by the owner after the Phase 0 spike)
- Evidence: [spike-findings.md §3](../spike-findings.md#3-resource-usage-at-idle-docker-allocation-and-limits)

## Context

Upstream 3.1.0 sets `GOMEMLIMIT=16MiB` for product-catalog and checkout, under a 20 MB container limit. On the spike's first start, both services sat in a GC death spiral at idle: about 1.0 and 0.5 cores, and a product-detail median of 80 ms. Restarting just those two services cleared it (about 0.004 cores, 4 ms median), and it didn't come back during the spike. At idle they use about 10–12 MiB, so there is only about 5 MiB of headroom, and load is likely to bring the spiral back. A baseline taken in that state would measure GC thrashing, not the shop, and whether it happens depends on luck at startup.

Options considered:

- **(a)** Raise the limits for the baseline and write up the upstream default as a finding.
- **(b)** Keep the upstream values and treat the spiral as the built-in bottleneck for the bottleneck hunt.
- **(c)** Run both configurations throughout.

## Decision

**(a).** The lab's override sets `GOMEMLIMIT=48MiB` and `mem_limit: 64M` for product-catalog and checkout. Every run's manifest records the effective values. The upstream 16 MiB setting is documented as a finding, and it stays available as a named configuration for a later experiment (for example, the bottleneck hunt), which would be pre-registered like any other.

Regardless of the setting, the reset protocol ends with a **health gate**. The run is refused if either service uses more than 0.05 cores at idle, or if the product-detail median on a short probe is far above the reset baseline. The exact thresholds are fixed in Phase 1.

## Consequences

- The baseline doesn't reflect upstream defaults for these two services. The docs say so, and the manifest shows the difference.
- 48 MiB is a proposal. Phase 2 load tests confirm the headroom, and if they show it's too tight, the limit gets a new ADR rather than a silent change.
- Docker VM memory needs about 90 MB more in total. That's negligible next to the ≥ 12 GB recommendation (C11).

## Update 2026-11-20 (Phase 1): health gate as implemented

The thresholds left open above are now fixed in `src/perflab/reset.py` and documented in [reset-protocol.md](../reset-protocol.md):

- **Idle CPU:** product-catalog and checkout must each average ≤ **0.05 cores** over the reset's 30 s settle window, measured from cumulative cgroup CPU through the Docker API (not `docker stats` snapshots, which spike §3 showed to be misleading).
- **Go memory:** `go_memory_used_bytes` (summed over memory types) must be below `go_memory_limit_bytes` for both services, from Prometheus. Missing data fails the gate.

**Change from the original wording:** the "product-detail median on a short probe" check was dropped. It needs a baseline that doesn't exist before Phase 2, it sends extra traffic into every reset, and the GC spiral shows up directly in the CPU and memory checks. If Phase 2 shows a case the CPU gate misses, a probe will be added by a new ADR.

The first resets under the new limits passed with both services at about 0.003 cores, and product-catalog at about 15.6 MiB used of 48 MiB. That's just under upstream's old 16 MiB limit, at idle, which supports the decision.

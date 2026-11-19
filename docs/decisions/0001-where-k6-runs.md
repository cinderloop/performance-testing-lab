# ADR 0001: Where k6 runs

- Status: **Accepted** (2026-11-20, by the owner after the Phase 0 spike)
- Evidence: [spike-findings.md §5](../spike-findings.md#5-where-k6-should-run)

## Context

The app, the observability stack and k6 share one MacBook (M4 Max, 16 cores), and the app runs inside Docker Desktop's Linux VM. k6 can run either natively on macOS, reaching the demo through Docker Desktop's port forwarding on `localhost:8080`, or in a container on the demo's Docker network, reaching `frontend-proxy:8080` directly. Neither option removes contention, because it's one machine either way. What differs is which overheads are visible, measurable and controllable.

## Options and evidence (spike, invalid run conditions, indicative only)

| | Native (Homebrew k6 2.3.0) | Container (`grafana/k6:2.3.0`) |
|---|---|---|
| Network path | host → Docker Desktop port forwarder → VM → Envoy | container → bridge network → Envoy |
| 1 VU latency, `/api/currency` (median) | 1.10–1.24 ms | 0.74–0.98 ms |
| 10 VUs, 15 s, throughput | ~2,340 req/s | ~2,610 req/s |
| Forwarder overhead visible in metrics? | No. It uses host CPU outside the VM. | Not applicable |
| k6's own CPU/memory | host process (`ps`, `/usr/bin/time`) | the same `docker_stats` series as every service |
| Can be limited (`cpus`, `mem_limit`) | no (only `taskpolicy`/`nice`) | yes, which the load-generator saturation experiment needs |
| Pinning | Homebrew build reports `commit/devel`, and `brew upgrade` changes it | image digest `sha256:2dd4756e…0b8`, official build |
| Reproducible by readers | needs a host install of the exact version | `docker run` only |

## Decision

Run k6 **in a container on the `opentelemetry-demo` network**, pinned by digest, with `K6_NO_USAGE_REPORT=true`. The target URL is `http://frontend-proxy:8080`. The local-target guard allows `localhost`, `127.0.0.1` and the configured Docker hostname `frontend-proxy` only.

## Consequences

- The k6 container competes with the app for the VM's vCPUs. That's measured, not hidden. The saturation experiment (Phase 4.6) can apply `cpus:` limits to k6.
- Results aren't comparable with native runs. The manifest records `k6_location`.
- k6 writes raw output to a bind-mounted `results/<run-id>/` directory.
- Native k6 is still documented as an alternative for people without Docker networking access. It needs a pinned release binary, not Homebrew.

# ADR 0009: Local-target guard and loopback-only ports

- Status: **Accepted** (2026-11-20, Phase 1)
- Evidence: [spike-findings.md §5, §12](../spike-findings.md)

## Context

Ground rule 3: load must never reach anything except the local demo. Ground rule 4: every exposed tool binds to 127.0.0.1, because the tools use default credentials (Grafana `admin`, Postgres `changeit`). The spike found upstream publishes 29 ports on `0.0.0.0`.

## Decision

**Guard (`k6/lib/guard.ts`):**
- An exact-host allowlist: `localhost`, `127.0.0.1`, and the demo's in-network hostname `frontend-proxy` (ADR 0001).
- The list is in the repo, not in an environment variable, so a run can't widen it.
- The guard runs twice:
  - **at init**, on `BASE_URL`: the script dies before the first request
  - **on every request**, in `k6/lib/http.ts`: absolute URLs are refused, so a path can't escape to another host
- It's deliberately strict. It also rejects:
  - user-info (`a@b`)
  - IPv6 literals
  - other loopback addresses
  - trailing dots
  - percent-encoding
  - non-http(s) schemes
  - malformed ports

**Tests:**
- 38 unit tests (`tests/k6/guard.test.ts`, `tests/k6/config.test.ts`) cover these cases, including lookalike hosts such as `localhost.example.com` and `127.0.0.1.nip.io`.
- `perflab inspect` also proves the guard fires **inside the pinned k6**. It runs `k6 inspect -e BASE_URL=https://example.com` on every script, in a container with `--network none`, so even a guard failure couldn't send a packet. CI runs this.

**Ports (`demo/compose.lab.yaml`):**
- Every service gets `ports: !reset []`, except:
  - `frontend-proxy`: `127.0.0.1:8080` (shop and tool UIs) and `127.0.0.1:10000` (Envoy admin, for request counters)
  - `prometheus`: `127.0.0.1:9090`
- `perflab ports` checks the fully resolved compose model and fails on any published port whose `host_ip` isn't `127.0.0.1`, or if the load generator is part of the default configuration. CI runs it.

## Consequences

- Pointing the lab at another system means editing `LOCAL_DOCKER_HOSTS` in the repo. That's deliberate friction.
- Native k6 (the documented alternative in ADR 0001) uses `http://localhost:8080`, which the allowlist already covers.

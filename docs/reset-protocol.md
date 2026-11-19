# Reset protocol

Every measured run starts from the same state (ground rule 7). `make reset` runs the protocol on its own, and `perflab run` runs it before every run. The result is written to `results/<run-id>/reset.json`, and its pass/fail goes into the manifest.

Implementation: [`src/perflab/reset.py`](../src/perflab/reset.py). The evaluation logic is unit-tested in [`tests/python/test_reset_checks.py`](../tests/python/test_reset_checks.py).

## What is reset, and what is kept

| State | Where | Reset by |
|---|---|---|
| Carts | Valkey (`valkey-cart`, in memory) | recreating the container |
| Orders, order items, shipping | Postgres (`astronomy-db`), anonymous volume | recreating with a **fresh anonymous volume**, which re-runs `init.sql` |
| Order events | Kafka topic `orders`, consumers `accounting` and `fraud-detection` | recreating Kafka with fresh volumes |
| Feature flags | `src/flagd/demo.flagd.json`, a bind mount that flagd-ui rewrites on every change | `git checkout` of the pinned file, then recreating flagd and flagd-ui |
| flagd-ui scheduler (switches flags at random once started) | flagd-ui process memory | recreating flagd-ui (it starts stopped) |
| In-process state: caches, the `emailMemoryLeak` leak, Go heaps | every app service | recreating the app tier |
| Observability: Prometheus TSDB, Jaeger (memory), OpenSearch, Grafana, collector | | **kept**, so history spans runs. Runs are separated by time and `run_id` |

## Steps

1. **Restore pristine feature flags:** `git -C demo/.upstream checkout -- src/flagd/demo.flagd.json`, then check that the upstream clone is at the pinned commit with no local changes.
2. **Remove the app tier with its anonymous volumes:** `docker compose … rm --force --stop --volumes` on the 21 app services (`compose.APP_TIER`: everything except grafana, jaeger, prometheus, opensearch, otel-collector and opamp-server).
3. **Recreate and wait for health:** `docker compose … up --detach --no-recreate --wait --wait-timeout 300`.
4. **Settle for 30 s** while measuring every container's CPU (cumulative cgroup CPU through the Docker API, before and after) and Envoy's `cluster.frontend.upstream_rq_total` counter.
5. **Verify the start state:**

   | Check | How | Pass |
   |---|---|---|
   | No orders | `psql … -c 'select count(*) from accounting."order"'` | `0` |
   | No carts | `valkey-cli dbsize` | ≤ 1 (cart writes one bookkeeping key on start) |
   | Empty order queue | `kafka-get-offsets.sh --topic orders` | every partition at offset 0 |
   | Flags pristine | `GET /feature/api/read` vs the pinned file | every flag on its pinned `defaultVariant`, no extra flags |
   | Load generator off (1) | Docker API, all containers | no `load-generator` container |
   | Load generator off (2) | `GET /loadgen/` | `503` (Envoy route has no upstream) |
   | No idle traffic | Envoy counter delta over the settle window | ≤ 2 (the collector's `http_check` hits the frontend about once a minute) |

6. **Health gate ([ADR 0003](decisions/0003-go-memory-limits.md)):**

   | Check | Pass |
   |---|---|
   | product-catalog and checkout idle CPU over the settle window | ≤ 0.05 cores each |
   | `go_memory_used_bytes` (summed) vs `go_memory_limit_bytes`, from Prometheus | used < limit for both; missing data fails |

If any check fails, `make reset` exits non-zero. `perflab run` still runs, but marks the run invalid and lists each failed check. Use `--require-valid` to abort instead.

## How long it takes

About a minute: roughly 30 s until every service is healthy, the 30 s settle window, then a few seconds of checks. Each run's `reset.json` records `seconds_to_healthy` and the timestamps.

## Load generator: why it's off, and how that's verified

Upstream starts a Locust load generator (5 users plus a browser user) that would mix its traffic into every measurement. `demo/compose.lab.yaml` puts it behind a compose profile (`loadgen`) that is never activated, and removes `frontend-proxy`'s dependency on it. `make ports` fails if it ever becomes part of the default configuration. The reset protocol then verifies it three ways at run time: no container, a dead route, and no idle traffic.

## Why not `docker compose down -v` every time?

It would also wipe Prometheus and Jaeger history, which is useful across runs, and it takes longer. A full `make down && make up` is still the right move after changing compose files or when the observability stack itself is suspect.

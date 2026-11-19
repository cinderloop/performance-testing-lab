# Phase 0 spike findings

Date: 2026-11-19. Everything in this document was observed on the machine below, against the local demo only.
Numbers come from short throwaway checks, not from measured runs: none of them meet the plan's run-validity rules (see §13). Treat them as "what the system looks like", not as results.

**Machine:** Apple M4 Max (16 cores), 64 GB RAM, macOS 26.0 (25A354), Docker Desktop 4.95.0 (Engine 29.8.2, Compose v5.6.0). Docker VM: 16 CPUs, **7.75 GiB memory**.

**Throwaway material.** The demo was cloned to a scratch directory, not into this repo. The spike override and check scripts also lived there and are reproduced inline below where they matter. Nothing from the spike is project code.

---

## 1. Demo version and pinning

| Item | Value |
|---|---|
| Demo release | **3.1.0** (latest, published 2026-09-18), git `dedc0178918e260823323b8d95005a8cb924b007` |
| Clone | `git clone --depth 1 --branch 3.1.0 https://github.com/open-telemetry/opentelemetry-demo.git` |
| Start command used | `docker compose --env-file .env --env-file .env.override -f compose.yaml -f compose.full.yaml -f compose.observability.yaml -f compose.extras.yaml -f <our-override>.yaml up -d --wait` |

Pinning gotchas found:

1. **The images aren't pinned by default.** Every demo service uses `image: ${IMAGE_NAME}:${DEMO_VERSION}-<svc>`, and `.env` sets `DEMO_VERSION=latest`. Without an override you get whatever `latest` is on the day you start.
2. **The 3.1.0 tag's `.env` says `IMAGE_VERSION=3.0.0`.** That variable is only used for build cache, but it's misleading. Published `3.1.0-*` images exist for every service.
3. Fix: `.env.override` with `DEMO_VERSION=3.1.0` and `IMAGE_VERSION=3.1.0`, plus digests recorded in the manifest. Recorded digests (multi-arch index digests, from `docker image inspect -f '{{index .RepoDigests 0}}'`):

<details><summary>27 image digests (click)</summary>

| Image | Digest |
|---|---|
| ghcr.io/open-feature/flagd:v0.16.0 | sha256:32234e63c1d0634883aabd31cbd46802934aaaef0153dfd653b5d1017940bb4e |
| ghcr.io/open-telemetry/demo:3.1.0-accounting | sha256:bfd9d13ac58a4eb5eb5130aa9ac1920686e2214030f4f2ab8bf178121879fcd9 |
| ghcr.io/open-telemetry/demo:3.1.0-ad | sha256:dfd7a4697116d7f961f2c6e8be1bd187f2af7555d6d4138c016097921d7c7ed0 |
| ghcr.io/open-telemetry/demo:3.1.0-cart | sha256:17c881cf29af5032e47d3dbd677afb132cbde66aad6355c7c2af8a6dbfc80581 |
| ghcr.io/open-telemetry/demo:3.1.0-checkout | sha256:d4448ff541290fc57cca71d4bfd35d522959edf62a8bb55158467583f9fad4e2 |
| ghcr.io/open-telemetry/demo:3.1.0-currency | sha256:ba65e72d5841f909e0ee09498572092923f59e249ae4bf084ab63a82b33811c1 |
| ghcr.io/open-telemetry/demo:3.1.0-email | sha256:bd7754c1e0986f892b86ed6ab9067a372640d342ff8eee2074bedb61c649ce71 |
| ghcr.io/open-telemetry/demo:3.1.0-flagd-ui | sha256:97a3d37e709f80e2018cdc0d45ea12d5b59092693e0e003d65089da966107062 |
| ghcr.io/open-telemetry/demo:3.1.0-fraud-detection | sha256:a07ee694304b23e3e4e1ca9bdaa7a02e3eb30d1805d87dfe95e7ea31cd3aa703 |
| ghcr.io/open-telemetry/demo:3.1.0-frontend | sha256:28358db4620686eda30dfabfc770b9ff0db73819ebac0895064271b446110289 |
| ghcr.io/open-telemetry/demo:3.1.0-frontend-proxy | sha256:fd4da88bfeaadd9437a4ee00f708e129a9eedb9c48874cea8e94b034983280a1 |
| ghcr.io/open-telemetry/demo:3.1.0-image-provider | sha256:46d1a7e95109c0064122ca0bfb49cd05191fb90a6264b6be508e0d98f2c963f1 |
| ghcr.io/open-telemetry/demo:3.1.0-kafka | sha256:4402ba7fd54470782a445f07c67e1d3f44d88ac8c5c0abf5d8298190a3f7a6ee |
| ghcr.io/open-telemetry/demo:3.1.0-opamp-server | sha256:3b6c6220bf9c7d8e6fdb8d1966316e80c5ac2004db6ae29c46681009d50e2093 |
| ghcr.io/open-telemetry/demo:3.1.0-opensearch | sha256:0a8401e9db8f7638b189a822a1a56a54dd4598cc42891ef59e3d003b2768b4ad |
| ghcr.io/open-telemetry/demo:3.1.0-payment | sha256:10d6bd20d8a00abe7705d553ab23a4f35e29b2816ab021049e63e89d07cc9192 |
| ghcr.io/open-telemetry/demo:3.1.0-product-catalog | sha256:7578cbf65fa4f0fc68e077e4f299ecccaa31d9778d407e41ab5973d247fd4b8e |
| ghcr.io/open-telemetry/demo:3.1.0-quote | sha256:e0b1ab3784fdbf0112521d3c5c733643f1cefa4eef5f592f845977465400181e |
| ghcr.io/open-telemetry/demo:3.1.0-recommendation | sha256:9dd7d7c320d2794a87c78cf534892519dace661a9022eb2cad5de1b75d994c18 |
| ghcr.io/open-telemetry/demo:3.1.0-shipping | sha256:7130dba0e77e90575b3f04fa8be39182cffe05f39df586a6620e9d221ee31e77 |
| ghcr.io/open-telemetry/demo:3.1.0-telemetry-docs | sha256:3f257a843222df2462d903fd57b12af5f31dc99a0f174b45136a4f3ba5c71203 |
| ghcr.io/open-telemetry/opentelemetry-collector-releases/opentelemetry-collector-contrib:0.159.0 | sha256:1f2c54a30e713fac6b3ae77a1ec84010c2007e29ced8ec666214fc2f6739c1cc |
| ghcr.io/valkey-io/valkey:9.0.4-alpine3.23 | sha256:107b203169a20ef7c87548c157f4e4a833dbbbd20fefd3a26740b7f98ac80216 |
| grafana/grafana:13.1.0 | sha256:121a7a9ece6dc10b969f1f96eed64b4f07dfac0d0b8abc070f7cb83bbde86f63 |
| postgres:18.4 | sha256:a02db8cac496f15b094798a38254f14d6e00741f709360e5e00bb6668ea31636 |
| quay.io/jaegertracing/jaeger:2.19.0 | sha256:ede4864215be4cd85bd8c3129a2fea6c5713c5653c7282c429dba123014bc68b |
| quay.io/prometheus/prometheus:v3.13.1 | sha256:3c42b892cf723fa54d2f262c37a0e1f80aa8c8ddb1da7b9b0df9455a35a7f893 |

</details>

Release-note facts that matter for this project:
- 3.0.0 replaced the Locust load generator with a k6-based one. **3.1.0 reverts it to Locust** "due to a dependency licensing issue", and removes the `loadGeneratorTraffic` / `loadGeneratorVUs` flags.
- 3.1.0 adds a **flagd-ui scheduler** that can switch random failure flags on and off by itself. It's off until someone starts it from the UI (see §9).

## 2. Native arm64

**All 27 images run natively as `linux/arm64`, with no emulation.** I checked with `docker image inspect -f '{{.Os}}/{{.Architecture}}'` on every image in the resolved config. The optional profiling images (§8) and `grafana/k6:2.3.0` also publish arm64. Nothing is blocked.

Pull time on first start: about 6 min. Images on disk: **11.3 GB**.

## 3. Resource usage at idle, Docker allocation and limits

Idle = full stack (core + full + observability), load generator off, no traffic, sampled 10 × 30 s with `docker stats --no-stream`, 1–6 min after start. A separate Prometheus `rate()` check over 2 min corrected the misleading `docker stats` snapshots (see the product-catalog note).

| | Value |
|---|---|
| Demo containers (27) idle memory | **~3.2 GiB** (sum of medians) |
| Demo idle CPU | ~0.7 cores normally; **~2 cores** in the anomalous first start (product-catalog + checkout thrashing, see below) |
| Summed memory limits (27 services, load generator excluded) | **6,399 MiB** (7,899 MiB with the load generator) |
| CPU limits in upstream compose | **none** on any service |
| Docker VM memory today | 7.75 GiB, shared with an unrelated running project ("toolshop", 6 containers, ~1.3 GiB) |

Containers close to their memory limit at idle: opensearch 1013/1024 MiB (99%), kafka 575/620 (93%), flagd 64/75 (85%), flagd-ui 171/200 (85%), fraud-detection 249/300 (83%), ad 242/300 (81%). The full per-container table is in the appendix.

**Finding: product-catalog and checkout can get stuck in a GC death spiral.** Upstream sets `GOMEMLIMIT=16MiB` explicitly for both (`compose.yaml` lines 141 and 537), under a 20 MB container limit. On the first start of the stack:
- `go_memory_used_bytes` was about 17.2 MB, above the 16 MiB `go_memory_limit_bytes`. The Go GC then runs nearly continuously.
- product-catalog used **~1.0 core** and checkout **~0.5 core at idle** (`rate(container_cpu_usage_nanoseconds_total[1m])`). `docker stats` single snapshots showed anywhere from 0% to 369% and hid this.
- 20 sequential single requests to `/api/products/{id}`: **median 80 ms, max 178 ms**, against 2 ms for `/api/currency`.
- One real-browser checkout took 6.1 s (4.1 s inside `ProductCatalogService/GetProduct`, called from checkout). Another failed with `14 UNAVAILABLE: Connection dropped` after 4 s.

After restarting just those two services, both settled at about 10–12 MiB with ~0.004 cores, and product detail dropped to a **4 ms median**. Raising the container limit to 64 MB made no difference on its own, because `GOMEMLIMIT` is set independently. The restart is what cleared it.

**I could not reproduce the spiral afterwards**: it didn't come back in a 10-minute idle watch, an app-tier reset, or a cold full `down -v` / `up`. So the cause is unknown; first-ever start and startup ordering are the leading suspects. The real risk is the headroom: about 11 MiB used at idle against a 16 MiB soft limit means **load is likely to push both services into the spiral**. Either way it would dominate any bottleneck study. See plan change **C1**.

**Recommended Docker allocation:** at least **12 GB memory** for the Docker VM (summed limits of 6.4 GB, plus k6 in a container, plus the VM's own overhead, plus headroom for raised limits). 16 CPUs is fine. The other project's containers should be stopped for measured runs (rule 7). See "Needs you".

**Sensible limits (proposal for Phase 1, to confirm at load in Phase 2):** keep upstream memory limits except for these: product-catalog and checkout `GOMEMLIMIT` 48MiB with a 64M limit, opensearch 1.5G, kafka 800M. Add **CPU limits** only where an experiment needs saturation (e.g. load-generator saturation, bottleneck hunt). Upstream has none, so today any service can borrow all 16 vCPUs. That's realistic for "one shared box", but it weakens USE analysis because nothing ever throttles. If we add CPU limits, the `docker_stats` throttling metrics must be enabled (§8).

## 4. Disabling the built-in load generator

Upstream starts `load-generator` (Locust, `LOCUST_AUTOSTART=true`, 5 users, plus a Playwright browser user, since compose forces `LOCUST_BROWSER_TRAFFIC_ENABLED=true`).

**Reliable way to disable it: don't create the container.** Our override puts it behind a compose profile and removes `frontend-proxy`'s dependency on it. Without that second change, `docker compose config` fails with `service "frontend-proxy" depends on undefined service "load-generator"`.

```yaml
services:
  load-generator:
    profiles: ["loadgen"]          # never started unless --profile loadgen
  frontend-proxy:
    depends_on: !override          # upstream list minus load-generator
      frontend: {condition: service_healthy}
      flagd-ui: {condition: service_healthy}
      telemetry-docs: {condition: service_healthy}
      jaeger: {condition: service_started}
      grafana: {condition: service_started}
      opamp-server: {condition: service_healthy}
```

Setting `LOCUST_AUTOSTART=false` is weaker, because the process still runs and can be started from its UI.

**Verification (all three passed, and should be automated in the reset protocol):**

| Check | Command | Expected when off |
|---|---|---|
| No container | `docker ps -a --filter name=^load-generator$ -q \| wc -l` | `0` |
| Proxy route has no upstream | `curl -s -o /dev/null -w '%{http_code}' localhost:8080/loadgen/` | `503` |
| No idle traffic to the frontend | Envoy admin `curl -s localhost:10000/stats \| grep '^cluster.frontend.upstream_rq_total'`, 60 s apart | **+1 per minute** (the collector's `http_check` receiver), nothing else |
| (optional) no `load-generator` service in Jaeger | `curl -s localhost:8080/jaeger/ui/api/services` | not listed |

## 5. Where k6 should run

Same tiny workload against `GET /api/currency` (a cheap endpoint, so the path dominates), alternating three times each:

| | Native (`localhost:8080`, through Docker Desktop port forwarding) | Container (`grafana/k6:2.3.0` on the `opentelemetry-demo` network, `frontend-proxy:8080`) |
|---|---|---|
| 1 VU, 300 sequential requests: median / p95 / p99 | 1.10–1.24 / 1.69–1.84 / 3.1–4.2 ms | 0.74–0.98 / 1.27–1.62 / 2.7–3.3 ms |
| 10 VUs, 15 s: throughput | 2,321 and 2,361 req/s | 2,612 and 2,604 req/s |
| 10 VUs, 15 s: median / p95 | 3.9 / 6.7–6.8 ms | 3.5 / 6.1 ms |
| k6 own CPU | 0.42 cores (`/usr/bin/time -l`: 3.4 s user + 2.8 s sys over 15 s), 56 MB RSS | measurable per container through the existing `docker_stats` receiver |

Findings:
- Native adds about **0.2–0.4 ms** per request and caps throughput about **10% lower** at this concurrency. The extra hop is Docker Desktop's port forwarder, which uses host CPU outside the VM and isn't visible in any container metric.
- Inside the VM, k6 shares the same 16 vCPUs as the app. That's contention we can see and limit (`cpus:`), and its CPU and memory appear in the same Prometheus series as every other container.
- Neither path removes contention, since it's one machine either way. The question is which contention we can measure and control.
- Homebrew's k6 here reports `commit/devel`, and Homebrew already offers 2.4.0, so a `brew upgrade` would silently change the pinned version. The image is an official build pinned by digest `grafana/k6@sha256:2dd4756ec6e14e62778916e1eb850108e4b499304c02df56760fa0bdb0fba0b8` (linux/arm64, `k6 v2.3.0 (commit/e088784614, go1.27.1)`).

**Recommendation: run k6 in a container on the demo network, pinned by digest.** It gives a shorter path, its own resource usage in the same metrics as the services, the option of CPU limits for the saturation experiment, and reproducibility without a host install. Native k6 stays as a documented alternative. ADR: [`decisions/0001-where-k6-runs.md`](decisions/0001-where-k6-runs.md) (*Accepted* 2026-11-20).

Consequence for the guard: the allowed hosts become `localhost`, `127.0.0.1` and the configured Docker hostname `frontend-proxy`.

## 6. HTTP entry point and the requests behind each journey

Entry point: **Envoy `frontend-proxy` on port 8080** (host `http://localhost:8080`, in-network `http://frontend-proxy:8080`). Envoy routes:

| Prefix | Upstream |
|---|---|
| `/` (catch-all) | frontend (Next.js, pages router) |
| `/images/` | image-provider (nginx), prefix stripped |
| `/flagservice/` | flagd (OFREP/Connect) |
| `/otlp-http/` | otel-collector HTTP (browser telemetry) |
| `/jaeger/`, `/grafana/`, `/feature`, `/loadgen/`, `/telemetry/`, `/opamp/`, `/profiles/`, `/chatbot/` | tool UIs |

I captured what a real browser sends with headless Chrome (playwright-core 1.64.1), running one fresh-session journey. The table shows document and API requests only. Asset counts are in §7.

| Journey step | Requests (method, path) |
|---|---|
| **Home** | `GET /` (document) · `POST /flagservice/flagd.evaluation.v1.Service/ResolveAll` · `GET /api/currency` · `GET /api/cart?sessionId={uid}&currencyCode=` · `GET /api/cart?sessionId={uid}&currencyCode=USD` · `GET /api/products?currencyCode=USD` · `GET /api/products?currencyCode=` |
| **Product page** (client-side navigation) | `GET /api/products/{productId}?currencyCode=USD` · `GET /api/data?contextKeys={categories, comma-joined}` (ads) · `GET /api/recommendations?productIds={productId}&sessionId={uid}&currencyCode=USD` |
| **Add to cart** (navigates to `/cart`) | `POST /api/cart?currencyCode=USD` · `GET /api/cart?sessionId={uid}&currencyCode=USD` · `GET /api/data?contextKeys=…` · `GET /api/shipping?itemList=[…]&currencyCode=USD&address={…}` |
| **View cart** | `GET /cart` (document: only on a direct visit or reload, which wasn't part of the capture; k6 got 200) · `GET /api/cart?sessionId={uid}&currencyCode=USD` · `GET /api/recommendations?productIds=&sessionId={uid}&currencyCode=USD` |
| **Checkout** | `POST /api/checkout?currencyCode=USD`, then navigate to `/cart/checkout/{orderId}?order={url-encoded order JSON}` · `GET /api/cart…` · `GET /api/recommendations…` · `GET /api/data…` |

Notes:
- The browser **calls `/api/cart` and `/api/products` twice** on home, once with an empty `currencyCode` (a React effect ordering quirk). That's real traffic, so the ADR decides whether to reproduce it.
- Client-side navigation doesn't fetch the product or cart page documents. A direct visit or reload does (`GET /product/{id}`, `GET /cart`).

**Payloads (as sent by the browser):**

```json
POST /api/cart?currencyCode=USD
{"item":{"productId":"0PUK6V6EV0","quantity":1},"userId":"7203f652-97e5-42ea-abd3-aaa6092813e8"}
```

```json
POST /api/checkout?currencyCode=USD
{"userId":"7203f652-97e5-42ea-abd3-aaa6092813e8","email":"someone@example.com",
 "address":{"streetAddress":"1600 Amphitheatre Parkway","state":"CA","country":"United States","city":"Mountain View","zipCode":"94043"},
 "userCurrency":"USD",
 "creditCard":{"creditCardCvv":672,"creditCardExpirationMonth":1,"creditCardExpirationYear":2030,"creditCardNumber":"4432-8015-6152-0454"}}
→ 200 {"orderId":"b102064e-…","shippingTrackingId":"…","shippingCost":{…},"shippingAddress":{…},"items":[…]}
```

```
GET /api/shipping?itemList=[{"productId":"0PUK6V6EV0","quantity":1}]&currencyCode=USD
    &address={"streetAddress":"1600 Amphitheatre Parkway","city":"Mountain View","state":"CA","country":"United States","zipCode":"94043"}
```

**Dynamic values / correlation:**

| Value | Where it comes from | Notes |
|---|---|---|
| `userId` / `sessionId` | **Generated in the browser** (`uuid v4`, stored in `localStorage["session"]`). The server never issues it. | Same value used as `sessionId` (GET cart, recommendations) and `userId` (POST cart, checkout). One per virtual user. |
| `productId` | `GET /api/products` response `[].id` | 10 products in the catalogue (`catalog.products`). |
| `contextKeys` for ads | `GET /api/products/{id}` response `.categories` | |
| `orderId` | `POST /api/checkout` response `.orderId` | Used in the confirmation page URL. |

The demo's Locust file isn't a good reference for journeys. It calls `GET /api/cart` **without** `sessionId` (so it always reads an empty cart), and it never fetches documents.

The throwaway k6 journey built from this table passed all checks, including `checkout 200 + orderId`.

## 7. What traffic is realistic

Per page view in the capture (cold, fresh browser):

| Kind | Home (cold) | Home (warm) | Notes |
|---|---|---|---|
| Document | 1 | 1 | `Cache-Control: private, no-cache, no-store` |
| `/_next/static/*` JS/CSS | 16 scripts + 1 CSS (~260 KiB in total) | same requests, served from browser cache | `Cache-Control: public, max-age=31536000, immutable`: CDN/browser cache in real life |
| Product images `/images/products/*.jpg` (image-provider) | 10 | 10 again | **No `Cache-Control`**, and fetched by JS (`fetch`) on every view. 21–361 KiB each, the biggest share of bytes (~2.1 MiB cold page) |
| Icons/logo `/icons/*`, `/images/opentelemetry-demo-logo.png` | several | | small |
| `POST /flagservice/…/ResolveAll` | 1 | 1 | browser feature-flag evaluation through flagd |
| `POST /otlp-http/v1/traces` | 2+ per step | | browser OpenTelemetry export to the collector |
| **External** `fonts.googleapis.com`, `fonts.gstatic.com` | 2 | 2 | public internet: must never be part of a load test |

**Recommendation (ADR [`decisions/0002-realistic-traffic.md`](decisions/0002-realistic-traffic.md), *Accepted* 2026-11-20):**
- **Include:** documents, all `/api/*` calls in the order and multiplicity the browser makes them (including the duplicate calls), and `/flagservice` ResolveAll (it's application traffic hitting flagd).
- **Exclude by default:** `/_next/static/*` (immutable, CDN-served in a real deployment), external fonts (non-local, so the guard forbids them anyway), and browser `/otlp-http` telemetry (it's the observer, not the user; including it would mix observer effect into every result).
- **Images: excluded by default, with an opt-in "with-images" journey variant.** They'd normally come from a CDN, but they're served by our stack and they're what the `imageSlowLoad` flag degrades. Excluding them makes that flag invisible to k6. I need your call on this (see "Needs you").

## 8. Stateful parts and reset procedure

| State | Where | After 1 checkout | Reset |
|---|---|---|---|
| Carts | Valkey `valkey-cart`, in memory, no volume | 3 keys | recreate container (`FLUSHALL` also works) |
| Orders | Postgres `astronomy-db`, `accounting."order"`, `orderitem`, `shipping`, in the anonymous volume `/var/lib/postgresql` | 1 order | recreate with a **fresh anonymous volume** (re-runs `init.sql`) |
| Catalogue | Postgres `catalog.products` (seeded by `init.sql`) | 10 rows | same |
| Order events | Kafka topic `orders` (anonymous volumes), consumers `accounting`, `fraud-detection` | log-end offset 1, lag 0 | recreate Kafka with fresh volumes |
| Feature flags | `src/flagd/demo.flagd.json`, a **bind mount that flagd-ui rewrites on every change** | — | restore the pristine file from our repo copy, then restart flagd |
| In-process state | recommendation cache (`recommendationCacheFailure`), email memory leak (`emailMemoryLeak`), Go heap (§3) | — | restarting the app services clears it |
| Observability | Prometheus TSDB, Jaeger (in memory, 25k traces max), OpenSearch | — | **keep** across runs (history is useful, and runs are separated by time windows) |

**Procedure tested (app-tier reset, keeps observability):**
1. Restore the flags file.
2. `docker compose … rm -fsv <21 app services>`. The `-v` removes their anonymous volumes.
3. `docker compose … up -d --no-recreate --wait --wait-timeout 300`.
4. Verify, all of these as observed:
   - `select count(*) from accounting."order"` → 0
   - `valkey-cli dbsize` → 1 (a `cart` string key the cart service creates on start)
   - `kafka-get-offsets.sh --topic orders` → `orders:0:0`
   - every flag on its `defaultVariant` (`off`), via `GET localhost:8080/feature/api/read`
   - load-generator containers → 0

**Timing: 31 s** to healthy. A cold full `down -v` + `up` took 8 s + 29 s (with images already pulled).

Add to the protocol, based on §3: a **post-reset health gate**. Fail the run if product-catalog or checkout idle CPU over 60 s is above about 0.05 cores, or if `go_memory_used_bytes` exceeds `go_memory_limit_bytes`. Note that the Go images are distroless (no `cat`), so measure from the docker side or Prometheus, not with `docker exec`.

## 9. Observability that ships with the demo

All UIs go through the proxy on port 8080. Default local credentials, so loopback-only binding is essential (§12).

| Component | URL | Notes |
|---|---|---|
| Grafana 13.1.0 | http://localhost:8080/grafana/ | 10 provisioned dashboards (APM, demo, spanmetrics, exemplars, collector, PostgreSQL, NGINX, Linux, self-observability, events) |
| Jaeger 2.19.0 | http://localhost:8080/jaeger/ui/ (API `…/jaeger/ui/api/traces/{id}`) | **in-memory store, `MEMORY_MAX_TRACES=25000`**: old traces are evicted under load |
| Prometheus v3.13.1 | http://localhost:9090 (loopback publish) | `--web.enable-otlp-receiver` **on**, `--web.enable-remote-write-receiver` **off**, `exemplar-storage` on, retention 7 d, **0 scrape targets** |
| OpenSearch | in-network only | logs |
| flagd-ui | http://localhost:8080/feature/ (API `/feature/api/read`, `/feature/api/write`) | the write API replaces the **whole** flag file |
| Envoy admin | http://localhost:10000/stats | useful for request counters (§4) |

**Metric resolution: Prometheus doesn't scrape anything.** All metrics are pushed through OTLP (SDK → collector → `otlp_http/prometheus` with batching). The global `scrape_interval: 60s` therefore applies to nothing, and the effective resolution is set by:

| Source | Interval |
|---|---|
| App SDK metrics (RED histograms `http_server_*`, `rpc_server_*`, runtime) | **60 s**: `OTEL_METRIC_EXPORT_INTERVAL` isn't set anywhere, so the SDK default applies |
| `span_metrics` connector (`traces_span_metrics_*`) | collector connector default |
| `docker_stats` (container CPU, memory, network, block I/O) | receiver default (10 s per upstream docs; not verified directly) |
| `redis`, `nginx`, `prometheus/ad` receivers | 10 s (explicit) |

**60 s is too coarse** for minute-scale experiments (warm-up, spikes, recovery). Plan change **C3**: set `OTEL_METRIC_EXPORT_INTERVAL=10000` (or 5000) for every service through the override, and document the plan's "scrape interval" as "export/push interval".

**Is it sufficient for RED/USE?**
- RED per service: yes. `http_server_request_duration_seconds_*`, `rpc_server_call_duration_seconds_*` and span-metrics are all present.
- USE: container CPU/memory/network/block I/O are present for **every** container, including the other project's (useful for recording contention), from the collector's `docker_stats` receiver. **CPU throttling metrics aren't collected.** They're optional `docker_stats` metrics, worth enabling only if we add CPU limits. Host metrics (`system_cpu_*`) describe the Docker VM, not macOS.
- Missing: container memory RSS (enabled in config but no series appeared), and any macOS-host view. The runner has to capture host conditions (§11).
- Overhead to remember for the observer-effect experiment: the collector uses the `debug` exporter on every pipeline, and all SDKs sample 100% (no `OTEL_TRACES_SAMPLER` set, i.e. the parent-based always-on default).

**Profiling:** upstream ships `compose.profiling.yaml` (OTel eBPF profiler collector `0.159.0`, `privileged: true`, `pid: host`, mounts the Docker socket and `/sys/kernel/debug`, plus the Firepit UI at `/profiles/`). Both images are arm64. **Not started in this spike**: whether the eBPF profiler works inside the Docker Desktop LinuxKit VM is still open. It's free and local, so I propose trying it at the start of Phase 3, and documenting why not if it fails.

## 10. k6 metrics into Prometheus, tagging, trace context

Docs read for **k6 v2.3.x** (grafana.com/docs/k6/v2.3.x/…). Facts used:

- `-o experimental-prometheus-rw` is still experimental in v2.3. It needs Prometheus's `--web.enable-remote-write-receiver` (currently off). Defaults: push every 5 s, trends as `p(99)` gauges, or native histograms behind the experimental `native-histograms` feature flag.
- `-o opentelemetry` is listed as **stable** in v2.3. Default export every 10 s.

**Tested: k6 OTel output straight into the demo Prometheus's existing OTLP receiver, with no Prometheus changes.**

```bash
K6_NO_USAGE_REPORT=true \
K6_OTEL_EXPORTER_PROTOCOL=http/protobuf \
K6_OTEL_HTTP_EXPORTER_ENDPOINT=localhost:9090 \
K6_OTEL_HTTP_EXPORTER_URL_PATH=/api/v1/otlp/v1/metrics \
K6_OTEL_HTTP_EXPORTER_INSECURE=true \
K6_OTEL_EXPORT_INTERVAL=1s \
K6_OTEL_SERVICE_NAME=k6-spike \
k6 run -o json=check.json -o opentelemetry k6-spike-check.js
```

Result: `http_req_duration_milliseconds_bucket`, `http_reqs_total`, `http_req_failed_total`, `checks_total`, `iterations_total`, `iteration_duration_*`, `data_*` and `target_info` appeared with `service_name="k6-spike"`. Labels include the request tags: `endpoint`, `expected_response`, `method`, `name`, `proto`, `scenario`, `status`, `url`, plus custom ones.

Caveats:
1. **Histogram buckets are the OTel defaults** (`le` = 0, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000 ms, +Inf). Percentiles computed in Prometheus are interpolations within those buckets. That's fine for dashboards, **not for analysis**. Analysis must use k6's raw per-request output.
2. **Names aren't prefixed** (`http_req_duration_…`). Set `K6_OTEL_METRIC_PREFIX=k6_` so they can't collide with app metrics.
3. **Cardinality:** `url` and `name` default to the full URL including query strings (`sessionId`, `itemList` …). Every request must set a `name` tag (we used `api_cart_get`, `api_checkout`, …), and `url` should be dropped with `--system-tags`.
4. Recommended path: k6 → OTLP → **Prometheus directly**, not through the demo collector. That avoids extra batching and keeps k6's own traffic out of the collector we're also observing. Decision for the Phase 1 ADR on k6 metrics storage.

**Raw per-request output:** `-o json=<file>.gz` gives one line per sample, with RFC 3339 timestamps (µs shown), the value in ms, all tags, and `metadata.trace_id` when tracing is on (example below). CSV is the alternative (`timeFormat` down to `unix_nano`).

```json
{"metric":"http_req_duration","type":"Point","data":{"time":"2026-11-19T22:49:56.17502+05:30","value":18.951,
 "tags":{"endpoint":"product_detail","expected_response":"true","method":"GET","name":"http://localhost:8080/api/products/0PUK6V6EV0?currencyCode=USD",
 "proto":"HTTP/1.1","scenario":"default","status":"200","url":"…"},"metadata":{"trace_id":"dc071818e981f06fe0f06de68ef68f4e"}}}
```

**Trace context:** in v2.3 `k6/experimental/tracing` is gone. The documented replacement is the jslib `https://jslib.k6.io/http-instrumentation-tempo/1.0.1/index.js` with `instrumentHTTP({ propagator: 'w3c' })` (`'jaeger'` also supported). **Tested:**
- k6 sent `traceparent: 00-dc071818e981f06fe0f06de68ef68f4e-2047555519d9a143-01`.
- The JSON point carried `metadata.trace_id` = `dc071818e981f06fe0f06de68ef68f4e`.
- `GET localhost:8080/jaeger/ui/api/traces/dc071818…` returned the trace (10 spans: frontend-proxy → frontend → product-catalog).
- k6's own span isn't exported, so the trace has **no root span**. That's harmless, and the Envoy span is the effective root.
- `--traces-output=otel` exists, but I didn't check whether it exports k6-side spans.
- To pin it, the jslib must be **vendored** into the repo (a remote import isn't reproducible). Sampling options weren't found in the docs.
- Because Jaeger keeps only 25,000 traces in memory, the runner should **record trace IDs for slow and failed requests** (from the raw output) and look them up during or right after the run. Alternatively we could raise `MEMORY_MAX_TRACES`, at a memory cost.

## 11. Feature flags in 3.1.0

From `src/flagd/demo.flagd.json`. Every flag defaults to `off`.

| Flag | Variants | Effect | Useful for |
|---|---|---|---|
| `adFailure` | on/off | ad service errors | errors (non-critical path) |
| `adHighCpu` | on/off | CPU burn in ad (Java) | **CPU**, bottleneck hunt |
| `adManualGc` | on/off | full GCs in ad | latency spikes / GC pauses |
| `cartFailure` | 10/25/50/75/90/100% | cart errors n% of calls | **errors**, graded |
| `emailMemoryLeak` | 1x/10x/100x/1000x/10000x | memory leak in email | **memory growth / soak** (Phase 5.4 ✔) |
| `failedReadinessProbe` | on/off | cart readiness failure | k8s-oriented; little value with Compose |
| `imageSlowLoad` | 5 s / 10 s | slow images (image-provider) | **latency**, only visible if images are in the workload (§7) |
| `intlShippingSlowdown` | 5 s / 10 s | slower shipping quote for non-US addresses | **latency on part of the traffic**: needs a share of international addresses |
| `kafkaQueueProblems` | on (100) | floods Kafka and delays consumers → lag | **queue** problems (async, invisible to k6 latency: a blind-spot candidate) |
| `loadGeneratorFloodHomepage` | on (100) | makes *Locust* flood `/` | not applicable, since the load generator is off |
| `paymentFailure` | 10/25/50/75/90/100% | charge failures → checkout 422 | **errors** at checkout. Note: the "90%" variant is actually **0.95** upstream |
| `paymentUnreachable` | on/off | payment unavailable | hard errors |
| `productCatalogFailure` | on/off | fails one specific product | partial errors (only some products) |
| `productCatalogLockContention` | on/off | DB lock contention in product-catalog (checked every 10 s) | **latency / saturation**, a good fit for open-vs-closed (Phase 4.1) |
| `recommendationCacheFailure` | on/off | recommendation cache leak | memory growth + latency |
| `emitRawPii` | on/off | PII in telemetry | not a perf flag |
| `aiSlowResponse`, `aiRunawayAgent` | | agentic stack only (not started) | n/a |

The flagd-ui **scheduler** randomly activates flags if someone starts it. The reset protocol must make sure it's stopped, and the manifest should record its state. Flags are changed with `POST /feature/api/write`, which replaces the whole file.

## 12. Port binding (rule 4)

Upstream publishes **29 ports, all on `0.0.0.0`**. Twenty-six of them, on random host ports, use the short `- "PORT"` form, including Postgres (password `changeit`), Valkey, the collector's OTLP ports and every internal service. Three are fixed: 8080 (Envoy), 10000 (Envoy admin) and 9090 (Prometheus).

Our override uses Compose's `!reset` / `!override` tags. **Verified:** after `up`, only `127.0.0.1:8080`, `127.0.0.1:10000` and `127.0.0.1:9090` are listening.

```yaml
services:
  cart:        { ports: !reset [] }   # … same for the other 24 internal services
  frontend-proxy:
    ports: !override ["127.0.0.1:8080:8080", "127.0.0.1:10000:10000"]
  prometheus:
    ports: !override ["127.0.0.1:9090:9090"]
```

This needs a lint check in CI: `docker compose config --format json` must show no published port without `host_ip: 127.0.0.1`.

## 13. Laptop conditions on macOS (no sudo)

| Signal | Command | Today |
|---|---|---|
| Power source | `pmset -g batt` → `Now drawing from 'AC Power'` | AC (battery at 12–17%, charging) |
| Low Power Mode | `pmset -g custom` → `powermode` per source (0 = automatic, 1 = low, 2 = high) and `ProcessInfo.processInfo.isLowPowerModeEnabled` (via `swift -e`) | `powermode 0`, `lowPowerMode=false` |
| Thermal state | `ProcessInfo.processInfo.thermalState` (0 nominal … 3 critical) | 0 |
| Thermal/performance warnings | `pmset -g therm` (CPU_Speed_Limit once a warning has been recorded) | "No thermal warning level has been recorded" |
| Display/system sleep | `pmset -g assertions`. The runner wraps k6 in `caffeinate -d -i` | AC `displaysleep 10`. A `caffeinate` assertion was already active from another process |
| Load and busy processes | `sysctl -n vm.loadavg`, `ps -Ao pcpu,rss,comm -r` | load ~4.6 at "idle" |
| **Not capturable without sudo** | CPU frequency, die temperature, power draw (`powermetrics` requires root) | — |

Other things running today that **would make a measured run invalid**:
- the "toolshop" Docker project (6 containers, ~1.3 GiB; one worker spiked to 66% CPU)
- Chrome
- Transmission (a BitTorrent client: network and disk activity)
- Spotlight indexing (`mdworker_shared`, `corespotlightd`)
- the Docker VM process itself at ~62% of a core with everything idle

## 14. Baseline run-to-run noise (spike only, invalid conditions)

**Why these runs are invalid for comparison:**
- The machine was not controlled: another Docker project, Chrome, Transmission and Spotlight were all running.
- The metric export interval was still upstream's 60 s.
- The journey is the throwaway spike version.

They answer "how noisy is this setup, roughly". Nothing more.

**Method:** 5 × (app-tier reset §8 → 30 s settle → k6 container, `constant-vus` 2 VUs × 90 s). Each iteration runs one home → product → add to cart → cart → checkout journey, with 1 s think time between steps, 13 requests, and timeout 10 s. Raw output is `-o json` (gzip).

Conditions per run: AC power, `powermode 0`, Low Power Mode off, thermal state 0 before and after, load average 2.3–4.0. Each reset took 30–31 s and its verification passed (0 orders, 1 Valkey key, Kafka offset 0, no flags on, no load generator).

Every run gave 44 iterations, 572 requests, **0 failures**, 220/220 checks.

Success-only latency in ms, per endpoint (n = 44 per run per endpoint; `api_cart_get` n = 88):

| Endpoint | Median range across runs | Median CV | p95 range across runs | p95 CV | Mean of per-run p95 | Pooled p95 (all 5 runs) |
|---|---|---|---|---|---|---|
| page_home | 4.2–5.5 | 11% | 8.3–12.7 | 18% | 10.3 | 11.5 |
| page_product | 4.8–5.6 | 7% | 9.3–13.3 | 16% | 11.1 | 12.0 |
| page_cart | 3.1–3.8 | 7% | 6.0–8.3 | 15% | 7.0 | 6.9 |
| api_currency | 2.8–3.8 | 12% | 5.6–8.5 | 16% | 6.9 | 7.3 |
| api_products_list | 4.1–5.2 | 10% | 7.3–16.9 | 34% | 11.8 | 14.6 |
| api_product | 6.6–7.8 | 7% | 10.1–14.6 | 15% | 12.6 | 12.8 |
| api_ads | 3.9–4.1 | 2% | 5.3–7.1 | 12% | 6.2 | 6.9 |
| api_recommendations | 18.6–22.2 | 6% | 25.2–28.4 | 5% | 26.4 | 27.0 |
| api_cart_add | 4.8–5.7 | 8% | 9.6–13.1 | 13% | 11.8 | 13.0 |
| api_cart_get | 4.2–5.0 | 6% | 10.2–13.9 | 11% | 12.3 | 12.7 |
| api_shipping | 5.0–5.8 | 6% | 7.6–23.2 | 55% | 11.7 | 23.1 |
| **api_checkout** | **30.3–38.4** | **9%** | **49.5–126.9** | **46%** | **70.4** | **126.5** |

What this shows (indicative):
- **Medians are stable** run to run: CV 2–12%.
- **p95 from 44 samples isn't**: CV 5–55%. A p95 from 44 samples rests on the top two or three values, so one slow request moves it (run 4 checkout 126.9 ms, run 1 shipping 23.2 ms). Phase 4.7 needs much larger samples per run (longer or heavier runs) before p95 comparisons mean anything, and the minimum detectable difference has to be measured, not assumed.
- **Mean of per-run p95 versus pooled p95 already differs by almost 2×** for checkout (70.4 vs 126.5 ms). That's a live example for Phase 4.3 (percentile pitfalls).
- Checkout medians climbed 30 → 38 ms across runs 1–5 despite the resets. With five runs this could be chance. The variance experiment should look for time trends (thermal state stayed at 0 throughout).
- The GC spiral from §3 didn't appear during these runs. Checkout stayed in the tens of ms with no failures, at 2 VUs.

Raw data for these runs lives in the spike scratch directory and is **not** committed. They are spike observations, not project results.

## 15. k6 behaviours to design around

- **k6 sends usage reports by default.** It reports to Grafana: anonymous installation ID, k6 version, VUs, duration, OS/arch, the modules and outputs used. Every invocation must use `K6_NO_USAGE_REPORT=true` (or `--no-usage-report`). Add a check for it.
- **Default request timeout is 60 s.** A timeout gives `status=0`, `error_code=1050`, `error="request timeout"` and counts in `http_req_failed`.
- **The default summary mixes failures into `http_req_duration`.** In the check, five requests that timed out after about 1 ms pulled overall `http_req_duration` avg/med to 6.0 / 3.4 ms, while successes alone (`{expected_response:true}`) were 10.9 / 6.8 ms. That's direct evidence for the plan's success/failure rule.
- **TypeScript runs natively** (esbuild strips types; no type checking, so `tsc --noEmit` is still needed in CI). `require()` only loads built-ins, local files and remote URLs, with no Node resolution.
- `--summary-mode` is `compact` / `full` / `disabled`. `disabled` also turns off `handleSummary`. `--no-summary` and `legacy` mode are gone in v2.
- In v2, the REST API is off unless `--address` is set.

---

## 16. Proposed plan changes

| # | Change | Why |
|---|---|---|
| C1 | **Decide how to treat the `GOMEMLIMIT=16MiB` Go services** (product-catalog, checkout) before any baseline, and add a post-reset health gate in every case | §3: observed GC spiral (1 core idle, 80 ms → 4 ms after a restart), and only about 5 MiB headroom at idle. Decided 2026-11-20: ADR 0003. |
| C2 | Pin the demo with `DEMO_VERSION=3.1.0` **and** `IMAGE_VERSION=3.1.0` in `.env.override`, plus digests in the manifest | §1: upstream defaults to `latest`, and the tag's `.env` says 3.0.0 |
| C3 | Set `OTEL_METRIC_EXPORT_INTERVAL` (10 s proposed) for all services. Rename the plan's "scrape intervals" to "metric export/collection intervals", recording the SDK, collector and k6 intervals. | §9: Prometheus scrapes nothing, and the SDK default is 60 s |
| C4 | k6 metrics → **`-o opentelemetry` → Prometheus OTLP receiver directly** (no remote write, no collector hop), prefix `k6_`, `name` tag on every request, drop `url`. Analysis uses raw `-o json` / CSV, never Prometheus percentiles. | §10: works unchanged; remote write is experimental and needs a Prometheus flag; OTel buckets are coarse |
| C5 | Trace correlation via the jslib `http-instrumentation-tempo@1.0.1`, **vendored**. The runner records trace IDs of slow and failed requests from the raw output, because Jaeger is in memory and capped at 25k traces. | §10 |
| C6 | Load generator disabled by **profile + `depends_on` override**, verified three ways (container count, `/loadgen/` 503, Envoy frontend counter). The flagd-ui scheduler is confirmed stopped. | §4, §11 |
| C7 | Port policy: `!reset` every internal port. Loopback-publish only 8080, 10000 and 9090. CI check on `docker compose config`. | §12: upstream publishes 29 ports on 0.0.0.0 |
| C8 | Reset protocol = app-tier recreate with fresh anonymous volumes + pristine flags file + verification queries + health gate (≈31 s). Observability is kept across runs. | §8 |
| C9 | `K6_NO_USAGE_REPORT=true` enforced by the runner (and checked). | §15: k6 phones home by default |
| C10 | k6 in a container, pinned by digest (ADR 0001); the guard's allowed hosts include `frontend-proxy`. | §5 |
| C11 | Docker VM memory ≥ 12 GB; stop the other project's containers for measured runs. Raise opensearch/kafka limits slightly. | §3 |
| C12 | macOS conditions: capture power source, `powermode`, Low Power Mode, thermal state, `pmset -g therm`, load average, top processes; wrap runs in `caffeinate -d -i`. **CPU frequency and temperature can't be captured without sudo**, so document that as a limitation. | §13 |
| C13 | Phase 4.7 (variance) must size runs for stable p95s. Smoke-length runs give a p95 CV of up to 55%. | §14 |
| C14 | Profiling: try the upstream eBPF profiler at the start of Phase 3 (arm64 images exist; privileged + host PID); otherwise document why not. | §9 |
| C15 | Housekeeping: the plan lives at `build-prompt.md` (not `docs/BUILD_PLAN.md`), and it still names the series "Mastering Performance Testing". The series was renamed to "Performance Testing from Zero to Production" during Part 1. | consistency |
| C16 | `failedReadinessProbe` and `loadGeneratorFloodHomepage` aren't usable here. Fault-injection candidates for Phase 5.3: `productCatalogLockContention`, `paymentFailure` (graded), `cartFailure` (graded), `adHighCpu`, `kafkaQueueProblems` (likely blind spot), `recommendationCacheFailure`, `intlShippingSlowdown` (needs international addresses in the test data), `emailMemoryLeak` for the soak test. | §11 |

## 17. Owner decisions (2026-11-20)

The owner accepted the spike's recommendations:

| Question | Decision | Record |
|---|---|---|
| Where k6 runs | In a container on the demo network, pinned by digest | [ADR 0001](decisions/0001-where-k6-runs.md), Accepted |
| Which browser traffic to reproduce | Documents, all `/api/*` calls (duplicates included) and flag evaluation. Static bundles, browser telemetry and fonts are excluded. **Images are excluded by default, with an opt-in `with-images` variant** (needed for `imageSlowLoad`). | [ADR 0002](decisions/0002-realistic-traffic.md), Accepted |
| `GOMEMLIMIT=16MiB` on product-catalog and checkout | **Raise it for the baseline** (`GOMEMLIMIT=48MiB`, `mem_limit: 64M`) and write up the upstream default as a finding. A post-reset health gate applies either way. | [ADR 0003](decisions/0003-go-memory-limits.md), Accepted |
| Repository | A git repo in this folder. `article/` and `build-prompt.md` stay out of it (`.gitignore`). | `.gitignore` |
| Docker VM memory ≥ 12 GB; stopping other apps and containers for measured runs | Recommendation stands (C11). Owner to apply in Docker Desktop; not changed by the agent. | C11 |
| CPU frequency and temperature | Not captured (they need sudo). Recorded as a limitation in every manifest. | C12 |

## Appendix A: per-container idle usage

10 samples × 30 s, 22:22:44–22:27:32 local time, first start. CPU shown is `docker stats` instantaneous, so for bursty services use the Prometheus rate figures in §3.

```
container                    cpu% med cpu% max mem MiB med  mem max limit MiB % of lim
opensearch                       1.23     3.13      1013.5   1015.0      1024      99%
kafka                            2.26     3.94       575.4    619.8       620      93%
fraud-detection                  0.38     1.15       249.2    250.9       300      83%
ad                               0.10     1.22       242.4    243.2       300      81%
otel-collector                   1.69     2.79       181.1    187.0       400      45%
flagd-ui                         0.03     1.02       170.8    171.5       200      85%
grafana                         16.38   918.20       104.0    174.9       175      59%   (startup provisioning)
frontend                         0.23     2.86        90.8     91.8       250      36%
accounting                       0.12     2.28        83.3     87.2       160      52%
email                            0.04     4.92        63.7     66.7       100      64%
flagd                            0.04     0.24        63.5     74.2        75      85%
payment                          0.24    23.74        59.1     62.8       140      42%
prometheus                       0.26     1.63        59.1     65.1       200      30%
recommendation                   0.56     3.25        50.3     50.9       500      10%
astronomy-db                     0.00     2.13        47.5     49.3        80      59%
cart                             0.04     0.97        45.0     54.4       160      28%
frontend-proxy                   0.46     1.58        26.1     30.2        90      29%
jaeger                           0.06     0.14        24.6     26.9      1200       2%
opamp-server                     0.01     1.06        13.8     15.5        65      21%
quote                            0.01     2.00        11.8     17.0        40      29%
shipping                         0.11     0.21        10.5     11.2        20      52%
product-catalog                 42.76   369.40         8.3     18.3        20      41%   (GC spiral, ~1.0 core by rate)
checkout                         0.12    64.88         8.2     17.6        20      41%   (GC spiral, ~0.5 core by rate)
telemetry-docs                   0.09     1.27         6.7      7.5       100       7%
image-provider                   0.06     0.90         5.5      5.9       120       5%
currency                         0.04     0.07         3.8      3.8        20      19%
valkey-cart                      0.08     1.01         3.7      4.0        20      18%
demo total: mem 3221 MiB          (other project's 6 containers: ~1.3 GiB more)
```

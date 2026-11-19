# ADR 0002: Which browser traffic the load tests reproduce

- Status: **Accepted** (2026-11-20, by the owner after the Phase 0 spike; images excluded by default, opt-in `with-images` variant)
- Evidence: [spike-findings.md §6–7](../spike-findings.md#6-http-entry-point-and-the-requests-behind-each-journey)

## Context

A headless Chrome capture of one journey (home → product → add to cart → cart → checkout) showed these kinds of request per page view:

- **Document**: `no-store`
- **`/api/*`**: 4–10 per step, with some duplicated (`/api/cart` and `/api/products` called twice on home, once with an empty `currencyCode`)
- **`POST /flagservice/…/ResolveAll`**: browser flag evaluation through flagd
- **`/_next/static/*`**: 16–17 JS/CSS files, `immutable`, about 260 KiB
- **Product images**: ~10 per view, 21–361 KiB, no `Cache-Control`, re-fetched by JS on every view; the bulk of bytes
- **`POST /otlp-http/v1/traces`**: browser telemetry
- **Google Fonts**: external hosts

In a real deployment, static bundles and product images would normally come from a CDN, so load on the origin is mostly documents, API calls and flag evaluation. Browser telemetry is observation traffic, not user behaviour.

## Decision

| Traffic | Default load tests | Reason |
|---|---|---|
| Documents (`/`, `/product/{id}`, `/cart`, `/cart/checkout/{orderId}`) on full page loads | **Include** | origin work (Next.js SSR) |
| `/api/*` in the browser's order and multiplicity, **including the duplicate calls** | **Include** | this is what the app really receives. Not "fixing" the client keeps the load model honest |
| `/flagservice` ResolveAll | **Include** | application traffic to flagd |
| `/_next/static/*` | **Exclude** | immutable and CDN/browser-cached. Including it measures Envoy/Node static serving, not the shop |
| Product images | **Exclude by default; opt-in `with-images` variant** | CDN-served in practice, but it's the only way the `imageSlowLoad` flag is visible. Decided: excluded by default, opt-in variant. |
| Browser `/otlp-http` telemetry | **Exclude** | observer traffic. Including it would mix observer effect into every run (that's Phase 5.2's subject) |
| External fonts | **Exclude (forbidden)** | non-local, so the local-target guard blocks it |

Think time between steps and the journey mix are Phase 2 (`workload-model.md`). Client-side navigations don't fetch documents. Whether a journey models full loads or client navigation is a workload-model decision, recorded there.

## Consequences

- Byte throughput in tests is far lower than a real page view. Docs must say that results describe the origin, not end-user page load time (browser-level testing is out of scope).
- `/flagservice` adds flagd to the critical path of every page view, which is realistic.
- Each request carries a `name` tag (e.g. `api_cart_get`), so query strings don't explode metric cardinality.

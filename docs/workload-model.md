# Workload model

How the load tests behave like shoppers, and why. There is no production traffic for the Astronomy Shop, so **many values below are assumptions**. Each one is marked **ASSUMPTION** with its reasoning, and lives in one place in the code so it can be changed and its effect measured.

Code: [`k6/journeys/`](../k6/journeys/) (demo-specific), [`k6/lib/`](../k6/lib/) (generic).

## What one session is

**One k6 iteration = one shopping session by a new user.** Each session gets a fresh browser-style UUID, used as both `sessionId` and `userId` (spike §6), so no two sessions share a cart.

A session lands on the shop with a full page load. Everything after that is a client-side navigation, exactly as the Next.js frontend behaves: no document request, only the page's API calls.

## The requests behind each page

These come from two headless-Chrome captures: the spike's full journey (spike §6) and a Phase 2 capture of direct landings on `/product/{id}` and `/cart`, which also recorded the flag-evaluation payload. Per [ADR 0002](decisions/0002-realistic-traffic.md), static bundles, images, browser telemetry and external fonts are excluded, and the duplicate calls the real client makes are kept. Those duplicates are the same API called first with an empty `currencyCode`, then with `USD`.

| Page (function in `pages.ts`) | Requests, in order | Count |
|---|---|---|
| **Land on home** `landOnHome` | `GET /` · `POST /flagservice/…/ResolveAll` · `GET /api/currency` · `GET /api/cart?…&currencyCode=` · `GET /api/products?currencyCode=` · `GET /api/cart?…USD` · `GET /api/products?currencyCode=USD` | 7 |
| **Land on a product** `landOnProduct` | `GET /product/{id}` · ResolveAll · `GET /api/products/{id}?currencyCode=` · currency · `GET /api/products/{id}?currencyCode=USD` · recommendations ×2 (empty, USD) · cart ×2 (USD, empty) · `GET /api/data?contextKeys={categories}` (ads) | 10 |
| **View a product** (client navigation) `viewProduct` | product (USD) · ads · recommendations | 3 |
| **Add to cart** (navigates to the cart page) `addToCart` | `POST /api/cart` · cart · ads · `GET /api/shipping?itemList=…&address=…` · recommendations ×2 (empty, then cart items) | 6 |
| **Place order** + confirmation page `placeOrder` | `POST /api/checkout` · cart (now empty) · ads | 3 |

ResolveAll is sent as the browser does: `Content-Type: application/json`, `Connect-Protocol-Version: 1`, body `{"context":{"targetingKey":<uid>,"userId":<uid>,"currencyCode":"USD"}}`.

Every request is checked for its expected status (200), and most also for key content:
- documents contain `__NEXT_DATA__`
- the product list isn't empty
- a product response is the product asked for
- the cart contains what was just added and is empty after checkout
- checkout returns an `orderId`
- shipping returns a USD cost
- flags returns a `flags` object

## Correlation

| Value | Comes from |
|---|---|
| `userId` / `sessionId` | generated per session (the browser does the same) |
| product ids for browsing | `GET /api/products` response (home landing), otherwise the known catalogue list |
| landing product id | the known catalogue list (a visitor arrives from a link). The smoke test checks the list against `/api/products` |
| ad `contextKeys` | the viewed product's `categories` |
| `itemList` for shipping, product ids for cart recommendations | the cart response |
| `orderId` | the checkout response (checked) |

## Journeys and mix

| Journey | Steps | Share |
|---|---|---|
| `browse` | land, then view 1–3 more products | **65%** |
| `abandon_cart` | land, view 1–2 products, add one to the cart, leave | **25%** |
| `buy` | land, view 1–2 products, add 1–2 of them (quantity 1–3 each), place the order | **10%** |

**ASSUMPTION, mix.** Real e-commerce conversion is usually a few percent of sessions, and most carts are abandoned. 10% buyers deliberately **over-weights checkout** compared with typical conversion. Checkout is the path that exercises the most services (cart, product catalog, currency, shipping, payment, email, Kafka, accounting, fraud detection), and at a realistic 2–3% a run would yield too few checkouts for a stable per-run percentile (ADR 0007). The over-weighting is a statistical choice, stated here, not a claim about shoppers.

**ASSUMPTION, landing.** 70% of sessions land on the home page, 30% directly on a product page (`LAND_ON_PRODUCT_SHARE`).

Expected from this design, not measured: a landing averages 7.9 requests (0.7 × 7 + 0.3 × 10). That gives browse about 14 requests per session, abandon about 18 and buy about 24, or **about 16 per session** across the mix. `perflab report` gives the measured numbers per journey.

## Think time and pacing

**ASSUMPTION, think time: uniform 1–5 s between pages** (`THINK_MIN_S`, `THINK_MAX_S`), so a session lasts roughly 5–20 s.

Real shoppers pause tens of seconds per page. Compressing that is deliberate:
- **It doesn't change the server's work per session.** Same requests, same order. It only changes how many sessions are open at once (Little's Law: concurrent sessions = arrival rate × session duration). The demo keeps no per-session server state between requests except the cart, which persists in Valkey either way.
- **It keeps the number of k6 VUs manageable on one laptop.** At 600 sessions/min with 60 s sessions, that would be 600 concurrent VUs; with about 12 s sessions it's about 120.
- **What it does change:** requests within one session arrive closer together. Any per-user caching or rate limiting would behave differently. The demo has neither on its request path.

**Pacing is an open model.** New sessions arrive at a set rate (`ramping-arrival-rate`, in sessions per minute) whatever the system's response time, the way independent shoppers do. A closed model (fixed VUs looping) would slow its own arrivals when the system slows down and hide the problem ([ADR 0010](decisions/0010-open-and-closed-models.md); demonstrated in Phase 4.1). The smoke test is the one exception: it's a fixed set of sessions to prove correctness, not a load model.

VU pools are sized by Little's Law (`vusFor`) with headroom, from a generous 20 s session estimate. When the system is so slow that every pre-allocated VU is busy, k6 records `dropped_iterations`, which counts as a failure signal and is reported separately.

## Load levels

All levels are expressed relative to one measured number, the **breakpoint** (`k6/scenarios/levels.ts`): the highest arrival rate at which the provisional thresholds still hold, measured by the breakpoint scenario on this machine.

| Level | Value | Basis |
|---|---|---|
| Breakpoint `B` | measured, see [scenarios.md](scenarios.md) | breakpoint scenario |
| Normal load `L` | **0.4 × B** | **ASSUMPTION:** a system normally runs with about 2.5× headroom |
| Stress steps | 0.75, 1.0, 1.25, 1.5 × B | to see behaviour just below, at and beyond the breakpoint |
| Spike | 1.25 × B, reached in 10 s, held 1 min | beyond the breakpoint, briefly |

On another machine, run the breakpoint scenario first and update `BREAKPOINT_PER_MIN`. Every other level follows from it.

## Soak duration

**60 minutes at normal load**, after a 2-minute ramp. Why this long, and why not longer, on a laptop:
- **Long enough to see trends** in server-side data at 10 s resolution (360 windows), and to compare the first and last 10 minutes with plenty of samples.
- **Long enough to show a leak.** The memory-growth fault (`emailMemoryLeak`, Phase 5.4) has to grow memory far beyond normal noise; a short load test shows nothing.
- **Long enough that Jaeger's 25,000-trace memory store** turns over many times, so any growth isn't just "the trace store filling up".
- **Not longer:** a laptop's conditions (thermal state, background activity) are harder to hold steady over many hours, and every extra hour costs real time for whoever reproduces the lab. Longer soaks belong on dedicated hardware (see `docs/out-of-scope.md`, Phase 6).

## Test data

| Data | Value |
|---|---|
| User | new UUID per session, `shopper-<uuid>@example.com` (reserved domain; the demo's email service sends nothing externally) |
| Products | random, from the catalogue (10 products), without repeats within a session |
| Quantity | 1–3 per item |
| Address | **ASSUMPTION: 20% international** (Berlin, Tokyo, Toronto), otherwise one of four US addresses including the form's default. Included in the baseline so the `intlShippingSlowdown` fault (Phase 5) hits a known share of orders without changing the workload between baseline and fault runs |
| Card | the checkout form's prefilled test card (VISA, valid Luhn, expiry 2030) |
| Currency | **ASSUMPTION: USD only**, the demo's default |

Test data is randomised, so repeated runs have the same workload distribution but not the same request sequence.

## Not modelled

- currency switching
- product images, static bundles, browser telemetry and fonts (ADR 0002; images will be an opt-in variant)
- logged-in or returning users (the demo has neither)
- browser rendering time: out of scope, since k6 measures the origin, not the page load users see

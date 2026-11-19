/**
 * SMOKE: does every journey work end to end, with zero errors, before anything heavier?
 *
 * Load: closed model, 1 VU running each journey twice in a fixed order (6 sessions), think time
 * included. About 1 to 2 minutes.
 * Pass: no failed requests, every check passes, provisional latency thresholds hold.
 */

import exec from "k6/execution";

import { checkJson } from "../lib/checks.ts";
import { labOptions } from "../lib/options.ts";
import { PROVISIONAL_THRESHOLDS } from "../lib/thresholds.ts";
import { KNOWN_PRODUCT_IDS, type JourneyName } from "../journeys/journeys.ts";
import { client, config, handleSummaryWithPlan, runSession, setupClock } from "./common.ts";

const ORDER: readonly JourneyName[] = ["browse", "abandon_cart", "buy"];

export const options = labOptions(config, {
  scenarios: {
    smoke: {
      executor: "per-vu-iterations",
      vus: 1,
      iterations: ORDER.length * 2,
      maxDuration: "5m",
    },
  },
  thresholds: {
    ...PROVISIONAL_THRESHOLDS,
    http_req_failed: ["rate==0"],
    checks: ["rate==1"],
  },
});

export function setup(): ReturnType<typeof setupClock> {
  // The journeys pick landing products from a fixed list; make sure it matches the catalogue.
  const res = client.get("/api/products?currencyCode=USD", {
    name: "api_products_list",
    group: "api",
    tags: { journey: "setup", step: "catalogue" },
  });
  checkJson(res, "api_products_list", "matches KNOWN_PRODUCT_IDS", (b) => {
    const ids = Array.isArray(b) ? b.map((p) => (p as { id: string }).id).sort() : [];
    return JSON.stringify(ids) === JSON.stringify([...KNOWN_PRODUCT_IDS].sort());
  });
  return setupClock();
}

export default function (): void {
  runSession(ORDER[exec.scenario.iterationInTest % ORDER.length]);
}

export const handleSummary = handleSummaryWithPlan(null);

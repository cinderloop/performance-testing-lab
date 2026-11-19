/**
 * Foundation check (Phase 1). Proves the pipeline end to end: guard, config, tagging, timeouts,
 * success/failure separation, handleSummary and the runner's manifest. It is NOT a workload
 * model and its numbers mean nothing. Phase 2 adds the real journeys and scenarios.
 *
 * Load: 1 VU, 10 iterations, 1 s pause. About 40 requests in about 15 s.
 */

import { sleep } from "k6";

import { checkJson, checkStatus } from "../lib/checks.ts";
import { loadConfig } from "../lib/config.ts";
import { createClient } from "../lib/http.ts";
import { labOptions } from "../lib/options.ts";
import { makeHandleSummary } from "../lib/summary.ts";

const config = loadConfig(__ENV);
const client = createClient(config);

export const options = labOptions(config, {
  scenarios: {
    foundation_check: { executor: "per-vu-iterations", vus: 1, iterations: 10, maxDuration: "2m" },
  },
});

interface Product {
  id: string;
}

function isProductList(body: unknown): body is Product[] {
  return (
    Array.isArray(body) &&
    body.length > 0 &&
    body.every((p) => typeof (p as Product).id === "string")
  );
}

export default function (): void {
  const home = client.get("/", { name: "page_home", group: "page" });
  checkStatus(home, "page_home");

  const currency = client.get("/api/currency", { name: "api_currency", group: "api" });
  checkStatus(currency, "api_currency");

  const products = client.get("/api/products?currencyCode=USD", {
    name: "api_products_list",
    group: "api",
  });
  checkStatus(products, "api_products_list");
  checkJson(products, "api_products_list", "has products", isProductList);

  const list: unknown = products.status === 200 ? products.json() : [];
  const first = isProductList(list) ? list[0] : undefined;
  if (first !== undefined) {
    const detail = client.get(`/api/products/${encodeURIComponent(first.id)}?currencyCode=USD`, {
      name: "api_product",
      group: "api",
    });
    checkStatus(detail, "api_product");
  }
  sleep(1);
}

export const handleSummary = makeHandleSummary(config);

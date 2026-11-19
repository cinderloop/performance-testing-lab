/**
 * The three user journeys and the session mix (docs/workload-model.md).
 * One k6 iteration = one shopping session by a new user.
 */

import { sleep } from "k6";

import type { Client } from "../lib/http.ts";
import { pick, randomBetween, randomInt, sample, weighted } from "../lib/random.ts";
import { newShopper } from "./data.ts";
import {
  addToCart,
  type Ctx,
  landOnHome,
  landOnProduct,
  placeOrder,
  type Product,
  viewProduct,
} from "./pages.ts";

export type JourneyName = "browse" | "abandon_cart" | "buy";

/** ASSUMPTION: session mix (see the workload model for the reasoning). */
export const MIX: Readonly<Record<JourneyName, number>> = {
  browse: 0.65,
  abandon_cart: 0.25,
  buy: 0.1,
};

/** ASSUMPTION: share of sessions that land on a product page instead of the home page. */
export const LAND_ON_PRODUCT_SHARE = 0.3;

/** ASSUMPTION: think time between pages, uniform, in seconds (compressed; see workload model). */
export const THINK_MIN_S = 1;
export const THINK_MAX_S = 5;

/**
 * The catalogue's product ids, used only to pick a landing product before any response has been
 * seen (a real visitor arrives from a link). Everything later uses ids from API responses.
 * Checked against /api/products by the smoke scenario.
 */
export const KNOWN_PRODUCT_IDS: readonly string[] = [
  "OLJCESPC7Z",
  "66VCHSJNUP",
  "1YMWWN1N4O",
  "L9ECAV7KIM",
  "2ZYFJ3GM2N",
  "0PUK6V6EV0",
  "LS4PSXUNUM",
  "9SIQT8TOJO",
  "6E92ZMYYFZ",
  "HQTGWGPNH4",
];

export function think(): void {
  sleep(randomBetween(THINK_MIN_S, THINK_MAX_S));
}

/** Land on home or a product page, then browse `extraViews` more products. */
function arriveAndBrowse(c: Ctx, extraViews: number): Product[] {
  const seen: Product[] = [];
  let catalogueIds: string[] = [...KNOWN_PRODUCT_IDS];
  c.step = "land";
  if (Math.random() < LAND_ON_PRODUCT_SHARE) {
    const p = landOnProduct(c, pick(KNOWN_PRODUCT_IDS));
    if (p) seen.push(p);
  } else {
    const catalogue = landOnHome(c);
    if (catalogue.length > 0) catalogueIds = catalogue.map((p) => p.id);
  }
  const already = new Set(seen.map((p) => p.id));
  for (const id of sample(
    catalogueIds.filter((x) => !already.has(x)),
    extraViews,
  )) {
    think();
    c.step = "view_product";
    const p = viewProduct(c, id);
    if (p) seen.push(p);
  }
  return seen;
}

function fillCart(c: Ctx, products: readonly Product[], items: number): void {
  for (const p of products.slice(0, items)) {
    think();
    c.step = "add_to_cart";
    addToCart(c, p, randomInt(1, 3));
  }
}

export function browse(c: Ctx): void {
  arriveAndBrowse(c, randomInt(1, 3));
}

export function abandonCart(c: Ctx): void {
  const seen = arriveAndBrowse(c, randomInt(1, 2));
  fillCart(c, seen, 1);
}

export function buy(c: Ctx): void {
  const seen = arriveAndBrowse(c, randomInt(1, 2));
  fillCart(c, seen, randomInt(1, 2));
  if (seen.length === 0) return;
  think();
  c.step = "checkout";
  placeOrder(c, seen[seen.length - 1]?.categories ?? []);
}

const JOURNEYS: Readonly<Record<JourneyName, (c: Ctx) => void>> = {
  browse,
  abandon_cart: abandonCart,
  buy,
};

/** Run one session. `journey` forces a journey (smoke); otherwise it's drawn from MIX. */
export function session(client: Client, journey?: JourneyName): void {
  const name = journey ?? weighted(MIX);
  const c: Ctx = { client, shopper: newShopper(), journey: name, step: "start" };
  JOURNEYS[name](c);
}

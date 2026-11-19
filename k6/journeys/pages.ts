/**
 * What the Astronomy Shop's browser sends for each page, request for request (ADR 0002,
 * spike §6 and the Phase 2 capture in docs/workload-model.md). Static bundles, images, browser
 * telemetry and external fonts are excluded. Duplicate calls the real client makes (empty
 * `currencyCode` first, then `USD`) are kept on purpose.
 *
 * Every page function returns the values later pages need (correlation) and checks the
 * responses' status and key content.
 */

import { checkBodyIncludes, checkJson, checkStatus, checkValue, jsonBody } from "../lib/checks.ts";
import type { Client, RequestSpec, Response } from "../lib/http.ts";
import type { Shopper } from "./data.ts";
import { CREDIT_CARD } from "./data.ts";

export interface Product {
  id: string;
  name: string;
  categories: string[];
}

export interface CartItem {
  productId: string;
  quantity: number;
}

/** Per-session context: who is shopping, which journey and step we're in. */
export interface Ctx {
  client: Client;
  shopper: Shopper;
  journey: string;
  step: string;
}

function spec(c: Ctx, name: string, group: RequestSpec["group"], expected?: number[]): RequestSpec {
  return {
    name,
    group,
    tags: { journey: c.journey, step: c.step },
    ...(expected ? { expected } : {}),
  };
}

const q = encodeURIComponent;

function isProduct(x: unknown): x is Product {
  const p = x as Partial<Product> | null;
  return (
    typeof p === "object" && p !== null && typeof p.id === "string" && Array.isArray(p.categories)
  );
}

function isProductList(x: unknown): x is Product[] {
  return Array.isArray(x) && x.length > 0 && x.every(isProduct);
}

function getOk(c: Ctx, path: string, name: string, group: RequestSpec["group"]): Response {
  const res = c.client.get(path, spec(c, name, group));
  checkStatus(res, name);
  return res;
}

// --- shared fragments ----------------------------------------------------------------------

function document(c: Ctx, path: string, name: string): void {
  const res = getOk(c, path, name, "page");
  checkBodyIncludes(res, name, "__NEXT_DATA__");
}

/** Browser feature-flag evaluation through flagd (OFREP over Connect), on every full page load. */
function resolveFlags(c: Ctx): void {
  const res = c.client.postJson(
    "/flagservice/flagd.evaluation.v1.Service/ResolveAll",
    {
      context: {
        targetingKey: c.shopper.userId,
        userId: c.shopper.userId,
        currencyCode: c.shopper.currency,
      },
    },
    { ...spec(c, "flags_resolve_all", "flags"), headers: { "Connect-Protocol-Version": "1" } },
  );
  checkStatus(res, "flags_resolve_all");
  checkJson(
    res,
    "flags_resolve_all",
    "has flags",
    (b) => typeof (b as { flags?: unknown } | null)?.flags === "object",
  );
}

function currency(c: Ctx): void {
  const res = getOk(c, "/api/currency", "api_currency", "api");
  checkJson(res, "api_currency", "lists USD", (b) => Array.isArray(b) && b.includes("USD"));
}

function cart(c: Ctx, currencyCode: string): CartItem[] {
  const path = `/api/cart?sessionId=${q(c.shopper.userId)}&currencyCode=${currencyCode}`;
  const res = getOk(c, path, "api_cart_get", "api");
  const body = jsonBody(res) as { items?: CartItem[] } | undefined;
  return Array.isArray(body?.items) ? body.items : [];
}

function productList(c: Ctx, currencyCode: string): Product[] {
  const res = getOk(c, `/api/products?currencyCode=${currencyCode}`, "api_products_list", "api");
  checkJson(res, "api_products_list", "has products", isProductList);
  const body = jsonBody(res);
  return isProductList(body) ? body : [];
}

function product(c: Ctx, id: string, currencyCode: string): Product | undefined {
  const res = getOk(c, `/api/products/${q(id)}?currencyCode=${currencyCode}`, "api_product", "api");
  checkJson(res, "api_product", "is the requested product", (b) => isProduct(b) && b.id === id);
  const body = jsonBody(res);
  return isProduct(body) ? body : undefined;
}

function ads(c: Ctx, categories: readonly string[]): void {
  const res = getOk(c, `/api/data?contextKeys=${q(categories.join(","))}`, "api_ads", "api");
  checkJson(res, "api_ads", "is a list", Array.isArray);
}

function recommendations(c: Ctx, productIds: readonly string[], currencyCode: string): void {
  const path =
    `/api/recommendations?productIds=${q(productIds.join(","))}` +
    `&sessionId=${q(c.shopper.userId)}&currencyCode=${currencyCode}`;
  const res = getOk(c, path, "api_recommendations", "api");
  checkJson(res, "api_recommendations", "is a list", Array.isArray);
}

function shippingQuote(c: Ctx, items: readonly CartItem[]): void {
  const path =
    `/api/shipping?itemList=${q(JSON.stringify(items))}&currencyCode=USD` +
    `&address=${q(JSON.stringify(c.shopper.address))}`;
  const res = getOk(c, path, "api_shipping", "api");
  checkJson(
    res,
    "api_shipping",
    "has a USD cost",
    (b) => (b as { currencyCode?: unknown } | null)?.currencyCode === "USD",
  );
}

// --- pages ---------------------------------------------------------------------------------

/** Full page load of `/` (a session landing on the home page). Returns the catalogue. */
export function landOnHome(c: Ctx): Product[] {
  document(c, "/", "page_home");
  resolveFlags(c);
  currency(c);
  cart(c, "");
  productList(c, "");
  cart(c, "USD");
  return productList(c, "USD");
}

/** Full page load of `/product/{id}` (a session landing from, say, a search result). */
export function landOnProduct(c: Ctx, id: string): Product | undefined {
  document(c, `/product/${q(id)}`, "page_product");
  resolveFlags(c);
  product(c, id, "");
  currency(c);
  const p = product(c, id, "USD");
  recommendations(c, [id], "");
  recommendations(c, [id], "USD");
  cart(c, "USD");
  cart(c, "");
  ads(c, p?.categories ?? []);
  return p;
}

/** Client-side navigation to a product page (no document request). */
export function viewProduct(c: Ctx, id: string): Product | undefined {
  const p = product(c, id, "USD");
  ads(c, p?.categories ?? []);
  recommendations(c, [id], "USD");
  return p;
}

/** "Add to cart" on a product page, which navigates (client-side) to the cart page. */
export function addToCart(c: Ctx, p: Product, quantity: number): CartItem[] {
  const res = c.client.postJson(
    "/api/cart?currencyCode=USD",
    { item: { productId: p.id, quantity }, userId: c.shopper.userId },
    spec(c, "api_cart_add", "api"),
  );
  checkStatus(res, "api_cart_add");
  const items = cart(c, "USD");
  checkValue(
    items.some((i) => i.productId === p.id),
    "api_cart_get",
    "contains the added product",
  );
  ads(c, p.categories);
  shippingQuote(c, items);
  recommendations(c, [], "USD");
  recommendations(
    c,
    items.map((i) => i.productId),
    "USD",
  );
  return items;
}

/** "Place order" on the cart page, then the order confirmation page. Returns the order id. */
export function placeOrder(c: Ctx, lastCategories: readonly string[]): string | undefined {
  const res = c.client.postJson(
    "/api/checkout?currencyCode=USD",
    {
      userId: c.shopper.userId,
      email: c.shopper.email,
      address: c.shopper.address,
      userCurrency: c.shopper.currency,
      creditCard: CREDIT_CARD,
    },
    spec(c, "api_checkout", "api"),
  );
  checkStatus(res, "api_checkout");
  checkJson(
    res,
    "api_checkout",
    "has an orderId",
    (b) => typeof (b as { orderId?: unknown } | null)?.orderId === "string",
  );
  const body = jsonBody(res) as { orderId?: string } | undefined;
  // Confirmation page (client-side navigation to /cart/checkout/{orderId})
  const after = cart(c, "USD");
  checkValue(after.length === 0, "api_cart_get", "is empty after checkout");
  ads(c, lastCategories);
  return body?.orderId;
}

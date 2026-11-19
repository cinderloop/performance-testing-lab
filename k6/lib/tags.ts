/**
 * Tagging conventions (docs/environment.md, "Tags").
 *
 * - `name`: a stable endpoint id such as `api_products_list`. Always set, so the URL (with its
 *   per-user query strings) never becomes a tag value (spike §10, cardinality).
 * - `endpoint_group`: `page` (HTML document), `api` (/api/*), `flags` (/flagservice), `image`.
 * - `journey` and `step`: set by journey code from Phase 2 on.
 * - `run_id`: on every sample, so raw output and any metrics store can be split by run.
 *
 * `expected_response` (k6 system tag) separates successes from failures everywhere.
 */

export type EndpointGroup = "page" | "api" | "flags" | "image";

/** System tags kept on every sample. `url`, `subproto`, `tls_version` and `service` are dropped. */
export const SYSTEM_TAGS: readonly string[] = [
  "proto",
  "status",
  "method",
  "name",
  "group",
  "check",
  "error",
  "error_code",
  "scenario",
  "expected_response",
];

const ENDPOINT_NAME_RE = /^[a-z][a-z0-9_]*$/;

export function assertEndpointName(name: string): void {
  if (!ENDPOINT_NAME_RE.test(name)) {
    throw new Error(`endpoint name ${JSON.stringify(name)} must be snake_case, e.g. api_cart_get`);
  }
}

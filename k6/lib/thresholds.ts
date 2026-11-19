/**
 * PROVISIONAL thresholds (docs/thresholds.md). Phase 4.8 replaces them with SLO-based values
 * derived from measured baseline and variance. Latency thresholds apply to successful requests
 * only; failures are covered by the error-rate threshold.
 */

export const PROVISIONAL_THRESHOLDS: Readonly<Record<string, string[]>> = {
  // Errors and checks
  http_req_failed: ["rate<0.01"],
  checks: ["rate>0.99"],
  // Latency of successes, per endpoint group (ms)
  "http_req_duration{endpoint_group:page,expected_response:true}": ["p(95)<1000"],
  "http_req_duration{endpoint_group:api,expected_response:true}": ["p(95)<500"],
  "http_req_duration{endpoint_group:flags,expected_response:true}": ["p(95)<500"],
  // Checkout does the most work per request (payment, shipping, email, Kafka), so it gets its own.
  "http_req_duration{name:api_checkout,expected_response:true}": ["p(95)<2000"],
};

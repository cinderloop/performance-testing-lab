/**
 * Typed run configuration from the environment (k6 `__ENV`). Pure, so it's unit-tested under Node.
 * The runner (`perflab run`) sets every value explicitly and records them in the manifest.
 */

import { assertLocalTarget } from "./guard.ts";

/** Explicit request timeout (ADR 0008). k6's own default is 60 s. */
export const DEFAULT_TIMEOUT_MS = 10_000;
export const MIN_TIMEOUT_MS = 100;
export const MAX_TIMEOUT_MS = 60_000;

/** In-network address of the demo's Envoy proxy (ADR 0001). */
export const DEFAULT_BASE_URL = "http://frontend-proxy:8080";

export interface LabConfig {
  /** Base URL without a trailing slash, already checked by the local-target guard. */
  baseUrl: string;
  runId: string;
  /** Directory where handleSummary writes (inside the k6 container: /results). */
  resultsDir: string;
  timeoutMs: number;
}

export type Env = Readonly<Record<string, string | undefined>>;

function intInRange(name: string, raw: string, min: number, max: number): number {
  if (!/^\d+$/.test(raw)) {
    throw new Error(`${name} must be a whole number of milliseconds, got ${JSON.stringify(raw)}`);
  }
  const n = Number(raw);
  if (n < min || n > max) {
    throw new Error(`${name} must be between ${min} and ${max} ms, got ${n}`);
  }
  return n;
}

export function loadConfig(env: Env): LabConfig {
  const baseUrl = (env.BASE_URL ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
  assertLocalTarget(baseUrl);
  return {
    baseUrl,
    runId: env.RUN_ID ?? "adhoc",
    resultsDir: (env.RESULTS_DIR ?? "results").replace(/\/+$/, ""),
    timeoutMs:
      env.TIMEOUT_MS === undefined
        ? DEFAULT_TIMEOUT_MS
        : intInRange("TIMEOUT_MS", env.TIMEOUT_MS, MIN_TIMEOUT_MS, MAX_TIMEOUT_MS),
  };
}

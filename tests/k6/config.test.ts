import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { DEFAULT_BASE_URL, DEFAULT_TIMEOUT_MS, loadConfig } from "../../k6/lib/config.ts";
import { TargetNotAllowedError } from "../../k6/lib/guard.ts";

describe("loadConfig", () => {
  it("uses the in-network demo address and the explicit timeout by default", () => {
    const c = loadConfig({});
    assert.equal(c.baseUrl, DEFAULT_BASE_URL);
    assert.equal(c.timeoutMs, DEFAULT_TIMEOUT_MS);
    assert.equal(c.runId, "adhoc");
  });

  it("strips trailing slashes", () => {
    assert.equal(
      loadConfig({ BASE_URL: "http://localhost:8080//" }).baseUrl,
      "http://localhost:8080",
    );
  });

  it("refuses a non-local BASE_URL before anything else happens", () => {
    assert.throws(() => loadConfig({ BASE_URL: "https://example.com" }), TargetNotAllowedError);
  });

  it("validates TIMEOUT_MS", () => {
    assert.equal(loadConfig({ TIMEOUT_MS: "2500" }).timeoutMs, 2500);
    for (const bad of ["0", "99", "60001", "1.5", "10s", "-1", ""]) {
      assert.throws(() => loadConfig({ TIMEOUT_MS: bad }), /TIMEOUT_MS/, bad);
    }
  });
});

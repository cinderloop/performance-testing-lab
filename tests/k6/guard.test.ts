import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { assertLocalTarget, parseTarget, TargetNotAllowedError } from "../../k6/lib/guard.ts";

describe("assertLocalTarget allows the local demo", () => {
  for (const url of [
    "http://localhost:8080",
    "http://localhost:8080/api/products?currencyCode=USD",
    "http://127.0.0.1:8080/",
    "http://frontend-proxy:8080",
    "http://frontend-proxy:8080/api/cart?sessionId=x#frag",
    "https://localhost",
    "HTTP://LOCALHOST:8080/",
  ]) {
    it(url, () => {
      assert.doesNotThrow(() => assertLocalTarget(url));
    });
  }
});

describe("assertLocalTarget blocks everything else", () => {
  const blocked: [string, string][] = [
    ["public host", "https://example.com/"],
    ["hosted demo lookalike", "https://opentelemetry.io/"],
    ["suffix trick", "http://localhost.example.com:8080/"],
    ["prefix trick", "http://evil-localhost:8080/"],
    ["DNS rebinding style name", "http://127.0.0.1.nip.io/"],
    ["user-info pointing elsewhere", "http://localhost@example.com/"],
    ["user-info hiding the host", "http://example.com@localhost/"],
    ["backslash confusion", "http://localhost\\@example.com/"],
    ["other loopback address", "http://127.0.0.2:8080/"],
    ["IPv6 loopback", "http://[::1]:8080/"],
    ["all interfaces", "http://0.0.0.0:8080/"],
    ["private network", "http://192.168.1.10:8080/"],
    ["Docker host gateway", "http://host.docker.internal:8080/"],
    ["trailing dot", "http://localhost.:8080/"],
    ["percent-encoded host", "http://local%68ost:8080/"],
    ["empty host", "http:///path"],
    ["relative URL", "/api/products"],
    ["no scheme", "localhost:8080"],
    ["other scheme", "ftp://localhost/"],
    ["websocket scheme", "ws://localhost:8080/"],
    ["bad port", "http://localhost:99999/"],
    ["non-numeric port", "http://localhost:80a/"],
    ["whitespace", "http://local host/"],
    ["empty string", ""],
  ];
  for (const [why, url] of blocked) {
    it(`${why}: ${url}`, () => {
      assert.throws(() => assertLocalTarget(url), TargetNotAllowedError);
    });
  }
});

describe("allowlist is exact", () => {
  it("only the given hosts pass when a custom allowlist is used", () => {
    assert.throws(() => assertLocalTarget("http://frontend-proxy:8080", ["localhost"]));
    assert.doesNotThrow(() => assertLocalTarget("http://localhost:8080", ["localhost"]));
  });
});

describe("parseTarget", () => {
  it("lowercases the host and parses the port", () => {
    assert.deepEqual(parseTarget("http://Frontend-Proxy:8080/x"), {
      scheme: "http",
      host: "frontend-proxy",
      port: 8080,
    });
  });
  it("returns null port when absent", () => {
    assert.equal(parseTarget("https://localhost/").port, null);
  });
});

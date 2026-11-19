import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { peakPerMin, plan, stages, vusFor } from "../../k6/lib/phases.ts";
import { randomInt, sample, weighted } from "../../k6/lib/random.ts";

describe("plan", () => {
  const p = plan("stress", "ramping-arrival-rate", 0, [
    { name: "ramp", durationS: 60, targetPerMin: 100 },
    { name: "hold", durationS: 120, targetPerMin: 100 },
    { name: "drop", durationS: 10, targetPerMin: 20 },
  ]);

  it("computes start/end times and the rate each phase starts from", () => {
    assert.deepEqual(
      p.phases.map((ph) => [ph.name, ph.startS, ph.endS, ph.startPerMin, ph.targetPerMin]),
      [
        ["ramp", 0, 60, 0, 100],
        ["hold", 60, 180, 100, 100],
        ["drop", 180, 190, 100, 20],
      ],
    );
    assert.equal(p.totalS, 190);
  });

  it("produces k6 stages and the peak", () => {
    assert.deepEqual(stages(p), [
      { duration: "60s", target: 100 },
      { duration: "120s", target: 100 },
      { duration: "10s", target: 20 },
    ]);
    assert.equal(peakPerMin(p), 100);
  });

  it("rejects bad phases", () => {
    const bad = (ph: { name: string; durationS: number; targetPerMin: number }[]) => () =>
      plan("x", "e", 0, ph);
    assert.throws(bad([{ name: "a", durationS: 0, targetPerMin: 1 }]));
    assert.throws(bad([{ name: "a", durationS: 1, targetPerMin: 1.5 }]));
    assert.throws(
      bad([
        { name: "a", durationS: 1, targetPerMin: 1 },
        { name: "a", durationS: 1, targetPerMin: 1 },
      ]),
    );
  });
});

describe("vusFor (Little's Law)", () => {
  it("is rate x time in system x headroom, rounded up", () => {
    // 600/min = 10/s, 20 s sessions -> 200 concurrent; x2 headroom -> 400
    assert.equal(vusFor(600, 20, 2), 400);
    assert.equal(vusFor(1, 20, 1), 1); // 0.33 -> 1
    assert.equal(vusFor(0, 20), 1);
  });
});

describe("weighted", () => {
  const w = { browse: 0.65, abandon_cart: 0.25, buy: 0.1 };
  it("maps the unit interval onto cumulative weights", () => {
    assert.equal(weighted(w, 0), "browse");
    assert.equal(weighted(w, 0.6499), "browse");
    assert.equal(weighted(w, 0.65), "abandon_cart");
    assert.equal(weighted(w, 0.8999), "abandon_cart");
    assert.equal(weighted(w, 0.9), "buy");
    assert.equal(weighted(w, 0.99999), "buy");
  });
  it("normalises weights that don't sum to 1", () => {
    assert.equal(weighted({ a: 1, b: 3 }, 0.3), "b");
  });
  it("rejects invalid weights", () => {
    assert.throws(() => weighted({ a: 0, b: 0 }));
    assert.throws(() => weighted({ a: -1, b: 2 }));
  });
});

describe("randomInt and sample", () => {
  it("stay within bounds and don't repeat", () => {
    for (let i = 0; i < 1000; i++) {
      const n = randomInt(1, 3);
      assert.ok(n >= 1 && n <= 3 && Number.isInteger(n));
    }
    const s = sample([1, 2, 3, 4, 5], 3);
    assert.equal(s.length, 3);
    assert.equal(new Set(s).size, 3);
    assert.deepEqual(sample([1, 2], 5).sort(), [1, 2]);
  });
});

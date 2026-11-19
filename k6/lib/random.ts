/**
 * Randomised test data helpers. Each session gets fresh values, so no two virtual users share a
 * cart or session (docs/workload-model.md, "Test data"). Math.random isn't seeded, and arrival-rate
 * scheduling isn't deterministic anyway: the workload's *distribution* is reproducible, the exact
 * request sequence isn't.
 */

/** k6 provides the Web Crypto `crypto` global at run time; neither es2022 nor @types/k6 declares it. */
declare const crypto: { randomUUID(): string };

export function uuid(): string {
  return crypto.randomUUID();
}

/** Uniform integer in [min, max], both inclusive. */
export function randomInt(min: number, max: number): number {
  return min + Math.floor(Math.random() * (max - min + 1));
}

/** Uniform float in [min, max). */
export function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

export function pick<T>(items: readonly T[]): T {
  if (items.length === 0) {
    throw new Error("pick() from an empty list");
  }
  return items[Math.floor(Math.random() * items.length)] as T;
}

/** Pick `n` distinct items (or all of them if there are fewer). */
export function sample<T>(items: readonly T[], n: number): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j] as T, copy[i] as T];
  }
  return copy.slice(0, Math.max(0, n));
}

/** Choose a key by weight. Weights needn't sum to 1. `roll` in [0, 1) is injectable for tests. */
export function weighted<K extends string>(
  weights: Readonly<Record<K, number>>,
  roll: number = Math.random(),
): K {
  const entries = Object.entries(weights) as [K, number][];
  const total = entries.reduce((s, [, w]) => s + w, 0);
  if (!(total > 0) || entries.some(([, w]) => w < 0)) {
    throw new Error("weights must be non-negative and not all zero");
  }
  let acc = 0;
  for (const [key, w] of entries) {
    acc += w / total;
    if (roll < acc) {
      return key;
    }
  }
  return (entries[entries.length - 1] as [K, number])[0];
}

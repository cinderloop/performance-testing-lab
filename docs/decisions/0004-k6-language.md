# ADR 0004: k6 scripts are written in TypeScript

- Status: **Accepted** (2026-11-20, Phase 1)
- Evidence: [spike-findings.md §15](../spike-findings.md#15-k6-behaviours-to-design-around), k6 v2.3.x docs ("JavaScript and TypeScript compatibility mode")

## Context

The plan allows TypeScript only if the pinned k6 version runs it natively. k6 2.3.0 does: TypeScript is on by default, and k6 uses esbuild to strip types from `.ts` files. It doesn't type-check, so type safety has to come from a separate `tsc` run. k6 resolves imports literally, with no Node module resolution, so relative imports need their `.ts` extension.

## Decision

All k6 code is TypeScript (`k6/**/*.ts`), type-checked in CI with `tsc --noEmit` (TypeScript 6.0.3, `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`) against `@types/k6` 2.3.1, which matches the pinned k6 minor version.

- Imports use explicit `.ts` extensions (`allowImportingTsExtensions`).
- Only erasable syntax (`erasableSyntaxOnly`): no enums, namespaces or parameter properties. esbuild and Node's type stripping both handle that safely.
- Code with no k6 imports (`k6/lib/guard.ts`, `k6/lib/config.ts`) is unit-tested with Node's built-in test runner, which runs `.ts` directly. That avoids a separate test framework; Vitest 5 doesn't support the pinned Node 25.
- ESLint (typescript-eslint `strictTypeChecked`) and Prettier run in CI. `k6 inspect` runs on every script, in the pinned k6 image.

## Consequences

- Type errors are caught in CI, not at run time. A script that passes `tsc` can still fail in k6 if it uses a Node or browser API, which is why `k6 inspect` also runs.
- `skipLibCheck` is on, because `@types/k6` 2.3.1 has an internal error under `exactOptionalPropertyTypes`. Our own code is still fully checked.
- One lint rule is off (`no-unsafe-class-instance-assignment`). `@types/k6` declares scenario configs as classes, but k6 expects plain objects.

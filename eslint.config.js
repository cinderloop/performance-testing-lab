// @ts-check
import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["node_modules/", "demo/.upstream/", "results/", ".venv/", "k6/vendor/"] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        project: ["./tsconfig.json", "./tests/k6/tsconfig.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      "@typescript-eslint/restrict-template-expressions": ["error", { allowNumber: true }],
      // @types/k6 declares scenario configs as classes, but k6 takes plain objects.
      "@typescript-eslint/no-unsafe-class-instance-assignment": "off",
    },
  },
  {
    // node:test's describe/it return promises the runner tracks itself.
    files: ["tests/**/*.ts"],
    rules: { "@typescript-eslint/no-floating-promises": "off" },
  },
  { files: ["**/*.js"], ...tseslint.configs.disableTypeChecked },
  prettier,
);

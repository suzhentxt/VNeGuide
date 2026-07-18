import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    ".next-*/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Playwright output is generated evidence, not application source.
    "blob-report/**",
    "playwright-report/**",
    "test-results/**",
    // Saved browser captures are reference data, not application source.
    "_DataURI/**",
    "dichvucong.gov.vn/**",
    "tong/**",
  ]),
]);

export default eslintConfig;

import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const config = [
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts", "src/lib/api/schema.d.ts", "coverage/**"] },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // As fixtures de src/testes só servem aos testes (T-126): o app fala com a API real.
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/testes/**", "src/**/*.test.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { patterns: [{ group: ["@/testes/*", "**/testes/*"], message: "Fixtures de teste não entram no app." }] }],
    },
  },
];

export default config;

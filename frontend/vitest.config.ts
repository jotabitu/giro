import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

const src = (p: string) => fileURLToPath(new URL(`./src/${p}`, import.meta.url));

export default defineConfig({
  esbuild: { jsx: "automatic" },
  resolve: {
    alias: [
      // As telas importam "@/lib/api"; nos testes isso é a camada de fixtures (src/testes), não a API real.
      { find: /^@\/lib\/api$/, replacement: src("testes/api-falsa.ts") },
      { find: "@", replacement: src("") },
    ],
  },
  test: { include: ["src/**/*.test.{ts,tsx}"], environment: "node" },
});

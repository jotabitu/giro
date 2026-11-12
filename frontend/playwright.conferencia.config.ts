import { defineConfig } from "@playwright/test";

// T-425 · Conferência lado a lado (e2e/conferencia). Config própria: o `npm run e2e` não a roda e ela não toca no banco.
// Porta e subdomínio como em playwright.config.ts (E2E_PORTA_FRONTEND, E2E_SUBDOMINIO).
const porta = process.env.E2E_PORTA_FRONTEND ?? "3000";
const subdominio = process.env.E2E_SUBDOMINIO ?? "motorapida";

export default defineConfig({
  testDir: "./e2e/conferencia",
  testMatch: "**/*.spec.ts",
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  outputDir: "test-results/conferencia",
  use: { baseURL: `http://${subdominio}.localhost:${porta}`, locale: "pt-BR", timezoneId: "America/Sao_Paulo", actionTimeout: 15_000, navigationTimeout: 30_000 },
});

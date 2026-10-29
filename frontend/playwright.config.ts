import { defineConfig, devices } from "@playwright/test";

// E2E do fluxo de locação (T-025). Roda contra o compose de verdade com o seed da Moto Rápida.
// Variáveis (todas opcionais, os padrões são os do .env.example):
//   E2E_PORTA_FRONTEND   porta do frontend no host (padrão 3000)
//   E2E_SUBDOMINIO       subdomínio da empresa (padrão motorapida)
// O relógio e o banco são controlados por e2e/suporte/ambiente.ts (ADR 0021) e nunca valem fora do desenvolvimento.
const porta = process.env.E2E_PORTA_FRONTEND ?? "3000";
const subdominio = process.env.E2E_SUBDOMINIO ?? "motorapida";
const baseURL = `http://${subdominio}.localhost:${porta}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",
  // O fluxo atravessa dois dias e muda o relógio do backend: um teste por vez, na ordem dos arquivos.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 6 * 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  outputDir: "test-results",
  use: {
    baseURL,
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "desktop",
      testMatch: ["**/desktop.spec.ts", "**/falhas.spec.ts", "**/fechamento.spec.ts", "**/fechamento-visual.spec.ts"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "celular",
      testMatch: ["**/celular.spec.ts", "**/fechamento-visual.spec.ts"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 },
    },
  ],
});

// Compra pública a partir da landing (T-490). A API da compra é simulada: o teste confere só a tela.
//   npx playwright test --project=compra   (com o frontend de pé em localhost:E2E_PORTA_FRONTEND)
import { expect, test, type Page } from "@playwright/test";

const CATALOGO = {
  planos: [
    { codigo: "essencial", nome: "Essencial", descricao: "Para quem está começando a frota.", mensal_centavos: 13000, anual_centavos: 130000, limites: { veiculos: 30, filiais: 1, usuarios: 3 }, inclui: ["Locação, vistoria e contas a receber"], destaque: false },
    { codigo: "profissional", nome: "Profissional", descricao: "Para locadoras com equipe e mais de uma loja.", mensal_centavos: 16000, anual_centavos: 160000, limites: { veiculos: 150, filiais: 3, usuarios: 10 }, inclui: ["Tudo do Essencial, mais despesas", "Pix e boleto automáticos"], destaque: true },
  ],
  teste: { dias: 14, inicio: "2026-10-07", fim: "2026-10-21", lembrete: "2026-10-19", primeira_fatura: "2026-10-22" },
};

async function simularApi(page: Page) {
  await page.route("**/api/publico/compra/planos/", (r) => r.fulfill({ json: CATALOGO }));
  await page.route("**/api/publico/compra/subdominio/", (r) => r.fulfill({ json: { subdominio: "motorapida", disponivel: true, endereco: "motorapida.giro.ceo" } }));
}

test("cartão do plano na landing abre a criação da conta com o plano escolhido", async ({ page }) => {
  await simularApi(page);
  await page.goto("/");
  await page.locator("#planos").getByRole("link", { name: "Começar teste grátis" }).first().click();
  await expect(page).toHaveURL(/\/compra\?plano=essencial$/);
  await expect(page.getByRole("heading", { name: "Crie sua conta" })).toBeVisible();
  await expect(page.getByText("R$ 130,00 por mês")).toBeVisible();
});

test("botão geral desce para os planos da página, com o foco no título, sem abrir a /compra", async ({ page }) => {
  await simularApi(page);
  await page.goto("/");
  await page.locator("header").getByRole("link", { name: "Começar teste grátis" }).click();
  await expect(page).toHaveURL(/\/#planos$/);
  await expect(page.locator("#planos-titulo")).toBeFocused();
  await expect(page.locator("#planos-titulo")).toBeInViewport();
});

test("plano inválido na URL volta para a escolha dos planos", async ({ page }) => {
  await simularApi(page);
  await page.goto("/compra?plano=completo");
  await expect(page.getByRole("heading", { name: "Escolha o plano da sua locadora" })).toBeVisible();
});

test("Trocar abre o pop-up, troca o plano e o ciclo sem perder o que foi preenchido", async ({ page }) => {
  await simularApi(page);
  await page.goto("/compra?plano=essencial");
  const nome = page.getByLabel("Nome completo");
  await nome.fill("Mariana Costa");

  const trocar = page.getByRole("button", { name: "Trocar" });
  await trocar.click();
  const popup = page.getByRole("dialog", { name: "Trocar o plano" });
  await expect(popup).toBeVisible();
  await expect(popup.getByText("Pix e boleto automáticos")).toBeVisible();
  await expect(popup.getByRole("button", { name: "Plano escolhido" })).toBeDisabled();

  // Esc fecha e o foco volta ao botão.
  await page.keyboard.press("Escape");
  await expect(popup).toBeHidden();
  await expect(trocar).toBeFocused();

  await trocar.click();
  await popup.getByRole("button", { name: /Anual/ }).click();
  await popup.getByRole("button", { name: "Escolher este plano" }).click();
  await expect(popup).toBeHidden();
  await expect(page.getByText("R$ 1.600,00 por ano")).toBeVisible();
  await expect(nome).toHaveValue("Mariana Costa");
});

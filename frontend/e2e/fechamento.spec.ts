// T-375 parte 2 · E2E do fechamento da fase 1: 2 etapas, modo suporte e controle do suporte (PLT-07, AUD-09, USR-02).
import { expect, test, type Page } from "@playwright/test";
import { definirData, executarNoBackend, restaurarSeed } from "./suporte/ambiente";
import { novaSessao, SENHA, visivel } from "./suporte/tela";


function codigoDe2fa(email: string): string {
  const saida = executarNoBackend(`
from seed.moto_rapida import codigo_de_2fa
print("CODIGO=" + codigo_de_2fa("${email}"))
`);
  expect(saida.CODIGO).toMatch(/^\d{6}$/);
  return saida.CODIGO as string;
}

/** O JWT do suporte vence pelo relógio real, e `fim` sai do relógio simulado: com 07 out o token nasce vencido (achado da T-375). Por isso o dia vira o de hoje. */
async function relogioNoDiaReal() {
  const hoje = new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo" }).format(new Date());
  await definirData(hoje);
}

function abrirSuporte(permissao: "ver" | "ver_editar"): string {
  const saida = executarNoBackend(`
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from apps.plataforma.models import Empresa
from apps.plataforma import services
empresa = Empresa.objects.get(subdominio="motorapida")
with schema_context("public"):
    dono = get_user_model().objects.get(email="dono@giro.example")
    acesso, token = services.abrir_acesso_suporte(empresa, dono, motivo="Chamado #1042", duracao_minutos=30, permissao="${permissao}")
print("TOKEN=" + token)
`);
  expect(saida.TOKEN).toBeTruthy();
  return saida.TOKEN as string;
}

test("2 etapas: Mariana (administradora) precisa do código; Rodrigo (gerente) não", async ({ browser }, info) => {
  await restaurarSeed();
  const { page, vigia } = await novaSessao(browser, info);
  vigia.esperar(401, /\/api\/auth\//);
  await page.goto("/entrar");
  await page.locator("input[name=email]").fill("mariana@motorapida.com.br");
  await page.locator("input[name=senha]").fill(SENHA);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Código de verificação" })).toBeVisible();
  await page.getByLabel("Dígito 1 de 6").click();
  await page.keyboard.type("000000");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).not.toHaveURL(/\/inicio/);
  await page.getByLabel("Dígito 1 de 6").click();
  for (let i = 0; i < 6; i++) await page.keyboard.press("Backspace");
  await page.keyboard.type(codigoDe2fa("mariana@motorapida.com.br"));
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/inicio/);

  const outra = await novaSessao(browser, info);
  await outra.page.goto("/entrar");
  await outra.page.locator("input[name=email]").fill("rodrigo@motorapida.com.br");
  await outra.page.locator("input[name=senha]").fill(SENHA);
  await outra.page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(outra.page).toHaveURL(/\/inicio/);
  vigia.verificar();
});

async function entrarComo2fa(page: Page, email: string) {
  await page.goto("/entrar");
  await page.locator("input[name=email]").fill(email);
  await page.locator("input[name=senha]").fill(SENHA);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await page.getByLabel("Dígito 1 de 6").click();
  await page.keyboard.type(codigoDe2fa(email));
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/inicio/);
}

test("modo suporte: entrada pelo link, faixa e Sair do suporte (PLT-07)", async ({ browser }, info) => {
  await restaurarSeed();
  await relogioNoDiaReal();
  const token = abrirSuporte("ver");
  const suporte = await novaSessao(browser, info);
  const p = suporte.page;
  await p.goto(`/suporte/entrar#${token}`);
  await expect(p).toHaveURL(/\/inicio/);
  expect(p.url()).not.toContain(token);
  await expect(p.getByText("Modo suporte").first()).toBeVisible();
  await expect(p.getByText("Chamado #1042").first()).toBeVisible();
  await expect(p.getByRole("button", { name: "Sair do suporte" })).toBeVisible();
  await p.getByRole("button", { name: "Sair do suporte" }).click();
  // Contrato (docs/api/contas.md): depois de Sair o suporte vê "Você saiu do modo suporte", não a tela de login da empresa.
  await expect.soft(p).toHaveURL(/\/suporte\/entrar/);
  await expect.soft(p.getByText("Você saiu do modo suporte")).toBeVisible();
  await p.goto("/inicio");
  await expect(p.getByRole("button", { name: "Sair do suporte" })).toHaveCount(0);
});

test("controle do suporte em Configurações: abrir, ver o acesso, bloquear e liberar (PLT-07)", async ({ browser }, info) => {
  await restaurarSeed();
  await relogioNoDiaReal();
  const { page } = await novaSessao(browser, info);
  await entrarComo2fa(page, "mariana@motorapida.com.br");
  await page.goto("/admin/configuracoes");
  await visivel(page.getByRole("link", { name: /Suporte/ })).click();
  await expect(page).toHaveURL(/\/admin\/suporte/);
  await expect(page.getByRole("alert").filter({ hasText: "Seu perfil não tem acesso" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Controle do suporte" })).toBeVisible();
  await expect(page.getByText("Liberado").first()).toBeVisible();
  const token = abrirSuporte("ver");
  const suporte = await novaSessao(browser, info);
  await suporte.page.goto(`/suporte/entrar#${token}`);
  await suporte.page.getByRole("button", { name: "Sair do suporte" }).click();
  await page.reload();
  await expect(page.getByText("Chamado #1042").first()).toBeVisible();
  await page.getByRole("button", { name: "Bloquear suporte Giro" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Bloquear suporte", exact: true }).click();
  await expect(page.getByText("Bloqueado").first()).toBeVisible();
  await page.getByRole("button", { name: "Liberar suporte Giro" }).click();
  const dialogo = page.getByRole("dialog");
  if (await dialogo.count()) await dialogo.getByRole("button", { name: /Liberar/ }).click();
  await expect(page.getByText("Liberado").first()).toBeVisible();
});

function codigoDe2faDaEmpresa(subdominio: string, email: string): string {
  const saida = executarNoBackend(`
from django_tenants.utils import tenant_context
from apps.plataforma.models import Empresa
from apps.contas.models import Autenticador
e = Empresa.objects.get(subdominio="${subdominio}")
with tenant_context(e):
    d = Autenticador.objects.get(user__email="${email}", confirmed=True)
    print("CODIGO=" + f"{d.totp().token():0{d.DIGITOS}d}")
`);
  return saida.CODIGO as string;
}

test("implantação do zero (Pedalada, Essencial): marca, filial, ramo, preços, contrato, equipe (IMP-01, IMP-04, IMP-07)", async ({ browser }, info) => {
  await restaurarSeed();
  const { page, vigia } = await novaSessao(browser, info);
  const B = "http://pedalada.localhost:3100";
  await page.goto(`${B}/entrar`);
  await page.locator("input[name=email]").fill("admin@pedalada.example");
  await page.locator("input[name=senha]").fill(SENHA);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await page.getByLabel("Dígito 1 de 6").click();
  await page.keyboard.type(codigoDe2faDaEmpresa("pedalada", "admin@pedalada.example"));
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/inicio/);

  await test.step("Marca: continua com a cor padrão", async () => {
    await page.goto(`${B}/implantacao`);
    await expect(page).toHaveURL(/\/implantacao\/marca/);
    await page.getByRole("button", { name: "Continuar" }).click();
  });
  await test.step("Primeira filial: a matriz já existe (IMP-07)", async () => {
    await expect(page).toHaveURL(/\/implantacao\/filial/);
    await expect(page.getByText("Filial Matriz")).toBeVisible();
    await page.getByRole("button", { name: "Continuar" }).click();
  });
  await test.step("Ramo", async () => {
    await expect(page).toHaveURL(/\/implantacao\/ramo/);
    await page.screenshot({ path: "test-results/impl-ramo.png" });
    await page.getByRole("button", { name: "Continuar" }).click();
  });
  await test.step("Tabela de preços: sem categoria não segue; cria uma", async () => {
    await expect(page).toHaveURL(/\/implantacao\/precos/);
    await expect(page.getByText("Para continuar, crie ao menos uma categoria com preço.")).toBeVisible();
    await page.getByRole("button", { name: "Nova categoria" }).click();
    const d = page.getByRole("dialog");
    await d.getByLabel("Nome da categoria").fill("Urbana 110");
    await d.getByLabel("Diária").fill("44,90");
    await d.getByLabel("Semanal").fill("299,40");
    await d.getByLabel("Mensal").fill("1090");
    await d.getByLabel("Caução").fill("300");
    await d.getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByText("Urbana 110").first()).toBeVisible();
    // Achado: depois de salvar, o aviso e o "Continuar" desabilitado não se atualizam sem recarregar.
    await expect.soft(page.getByText("Para continuar, crie ao menos uma categoria com preço."), "sem recarregar").toHaveCount(0, { timeout: 5000 });
    await page.reload();
    await expect(page.getByText("Para continuar, crie ao menos uma categoria com preço."), "depois de recarregar").toHaveCount(0);
    await page.getByRole("button", { name: "Continuar" }).click();
  });
  await test.step("Modelo de contrato", async () => {
    await expect(page).toHaveURL(/\/implantacao\/contrato/);
    await page.getByRole("button", { name: "Novo modelo" }).click();
    await page.screenshot({ path: "test-results/impl-contrato.png" });
    const dm = page.getByRole("dialog");
    await expect(dm.getByRole("button", { name: "Criar modelo" })).toBeVisible();
    await dm.getByLabel("Nome do modelo").fill("Locação diária de moto");
    await dm.getByRole("button", { name: "Criar modelo" }).click();
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "test-results/impl-contrato2.png" });
    await page.getByRole("button", { name: /Publicar versão/ }).click();
    await expect(page.getByText(/Publicado/).first()).toBeVisible();
    await page.reload();
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page).toHaveURL(/\/implantacao\/importar/);
    await page.goto(`${B}/implantacao/equipe`);
    await expect(page).toHaveURL(/\/implantacao\/equipe/);
    await page.getByRole("button", { name: /Convidar/ }).first().click();
    const convite = page.getByRole("dialog");
    await convite.getByLabel("E-mail").fill("vendas@pedalada.example");
    await convite.getByLabel("Nome (opcional)").fill("Vendas Pedalada");
    await convite.getByRole("button", { name: "Enviar convite" }).click();
    await expect(page.getByText("vendas@pedalada.example").first()).toBeVisible();
    await page.getByRole("button", { name: "Concluir" }).click();
    await expect(page).toHaveURL(/\/inicio/);
  });
  await test.step("Em Usuários o convite aparece pendente (IMP-07: passo feito)", async () => {
    await page.goto(`${B}/admin/usuarios`);
    await expect(page.getByText("vendas@pedalada.example").first()).toBeVisible();
    await page.screenshot({ path: "test-results/impl-fim.png" });
  });
  vigia.verificar();
});

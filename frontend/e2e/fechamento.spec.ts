// T-375 parte 2 · E2E do fechamento da fase 1: 2 etapas, modo suporte e controle do suporte (PLT-07, AUD-09, USR-02).
import { expect, test, type Page } from "@playwright/test";
import { createHmac } from "node:crypto";
import { executarNoBackend, restaurarSeed } from "./suporte/ambiente";
import { novaSessao, SENHA, visivel } from "./suporte/tela";


function codigoDe2fa(email: string): string {
  const saida = executarNoBackend(`
from seed.moto_rapida import codigo_de_2fa
print("CODIGO=" + codigo_de_2fa("${email}"))
`);
  expect(saida.CODIGO).toMatch(/^\d{6}$/);
  return saida.CODIGO as string;
}

/** TOTP (RFC 6238, SHA-1, 6 dígitos, 30 s) a partir da chave em base32 que a tela mostra. */
function totp(chave: string): string {
  const alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of chave.replace(/=+$/, "")) bits += alfabeto.indexOf(c).toString(2).padStart(5, "0");
  const bytes = Buffer.from((bits.match(/.{8}/g) ?? []).map((b) => parseInt(b, 2)));
  const contador = Buffer.alloc(8);
  contador.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 1000 / 30)));
  const h = createHmac("sha1", bytes).update(contador).digest();
  const o = (h[h.length - 1] as number) & 0xf;
  const n = (((h[o] as number) & 0x7f) << 24) | (((h[o + 1] as number) & 0xff) << 16) | (((h[o + 2] as number) & 0xff) << 8) | ((h[o + 3] as number) & 0xff);
  return String(n % 1_000_000).padStart(6, "0");
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
  await expect(p).toHaveURL(/\/suporte\/entrar/);
  await expect(p.getByText("Você saiu do modo suporte")).toBeVisible();
  await p.goto("/inicio");
  await expect(p.getByRole("button", { name: "Sair do suporte" })).toHaveCount(0);
});

test("controle do suporte em Configurações: abrir, ver o acesso, bloquear e liberar (PLT-07)", async ({ browser }, info) => {
  await restaurarSeed();
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
    await expect(page.getByText("Para continuar, crie ao menos uma categoria com preço.")).toHaveCount(0);
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
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page).toHaveURL(/\/implantacao\/importar/);
    await page.goto(`${B}/implantacao/equipe`);
    await expect(page).toHaveURL(/\/implantacao\/equipe/);
    await page.getByRole("button", { name: /Convidar/ }).first().click();
    const convite = page.getByRole("dialog");
    await convite.getByLabel("E-mail").fill("financeiro@pedalada.example");
    await convite.getByLabel("Nome (opcional)").fill("Financeiro Pedalada");
    await convite.getByLabel("Perfil").selectOption({ label: "Financeiro" });
    await convite.getByRole("button", { name: "Enviar convite" }).click();
    await expect(page.getByText("financeiro@pedalada.example").first()).toBeVisible();
    await page.getByRole("button", { name: "Concluir" }).click();
    await expect(page).toHaveURL(/\/inicio/);
  });
  await test.step("Em Usuários o convite aparece pendente (IMP-07: passo feito)", async () => {
    await page.goto(`${B}/admin/usuarios`);
    await expect(page.getByText("financeiro@pedalada.example").first()).toBeVisible();
    await page.screenshot({ path: "test-results/impl-fim.png" });
  await test.step("A pessoa convidada aceita o convite, cria a senha e ativa as 2 etapas pela tela (USR-01, USR-02)", async () => {
    const saida = executarNoBackend(`
from django_tenants.utils import tenant_context
from apps.plataforma.models import Empresa
from apps.contas.models import Usuario
from apps.contas import services
from django.db import transaction
e = Empresa.objects.get(subdominio="pedalada")
with tenant_context(e):
    convidada = Usuario.objects.get(email="financeiro@pedalada.example")
    admin = Usuario.objects.get(email="admin@pedalada.example")
    with transaction.atomic():
        resultado = services.gerar_link_convite(convidada, admin)
    print("TOKEN=" + str(resultado[2]))
`);
    const token = saida.TOKEN ?? "";
    expect(token).toBeTruthy();
    const nova = await novaSessao(browser, info);
    const p = nova.page;
    await p.goto(`${B}/convite#${token}`);
    await expect(p.getByText("Financeiro").first()).toBeVisible();
    await p.getByLabel("Seu nome").fill("Financeiro Pedalada");
    await p.getByLabel("Senha").first().fill("Giro-dev-2026-nova!");
    await p.getByRole("button", { name: "Criar acesso e entrar" }).click();
    await expect(p.getByText("Seu perfil exige a verificação em 2 etapas")).toBeVisible();
    const chave = (await p.locator("span.wl-mono").first().innerText()).replace(/\s/g, "");
    expect(chave).toMatch(/^[A-Z2-7]{16,}$/);
    await p.getByLabel("Dígito 1 de 6").click();
    await p.keyboard.type(totp(chave));
    await p.getByRole("button", { name: "Ativar verificação" }).click();
    await expect(p.getByText("Guarde os códigos de recuperação")).toBeVisible();
    await p.getByRole("checkbox").check();
    await p.getByRole("button", { name: /Concluir|Continuar|Entrar/ }).last().click();
    await expect(p).toHaveURL(/\/inicio/);
  });
  });
  vigia.verificar();
});

test("Reembolsos e Pendências do pagamento com dados do seed: Marcar como feito e Baixar a conta (DEV-02, AUT-05)", async ({ browser }, info) => {
  await restaurarSeed();
  const { page, vigia } = await novaSessao(browser, info);
  await entrarComo2fa(page, "mariana@motorapida.com.br");

  await test.step("Reembolso da Patrícia: R$ 286,20 a fazer, marca como feito", async () => {
    await page.goto("/financeiro/reembolsos");
    await expect(page.getByText("Patrícia Gomes").first()).toBeVisible();
    await expect(page.getByText("R$ 286,20").first()).toBeVisible();
    await page.getByRole("button", { name: "Marcar como feito" }).first().click();
    await page.screenshot({ path: "test-results/reembolso-dialogo.png" });
    const d = page.getByRole("dialog");
    await d.getByRole("button", { name: /Marcar como feito|Confirmar/ }).click();
    await expect(page.getByText("Nenhum reembolso a fazer.")).toBeVisible();
    await page.getByRole("tab", { name: /Feitos/ }).click().catch(async () => page.getByText(/^Feitos/).first().click());
    await expect(page.getByText("Patrícia Gomes").first()).toBeVisible();
  });

  await test.step("Pendência do Carlos: R$ 299,40 aberta, baixa a conta", async () => {
    await page.goto("/financeiro/pendencias-pagamento");
    await expect(page.getByText("Carlos Menezes").first()).toBeVisible();
    await page.getByRole("button", { name: /Resolver/ }).first().click();
    await page.screenshot({ path: "test-results/pendencia-dialogo.png" });
    const d = page.getByRole("dialog");
    await expect(d.getByText("Resolver pendência")).toBeVisible();
    await d.getByText("Baixar a conta", { exact: true }).click();
    await d.getByLabel("Motivo").fill("Cliente pagou R$ 299,40 e a diferença foi dispensada");
    await page.screenshot({ path: "test-results/pendencia-dialogo1b.png" });
    await d.getByRole("button").filter({ hasText: /Resolver|Confirmar|Salvar|Baixar/ }).last().click();
    await expect(page.getByText("Nenhuma pendência aberta.")).toBeVisible();
    await page.screenshot({ path: "test-results/pendencia-dialogo2.png" });
  });
  vigia.verificar();
});

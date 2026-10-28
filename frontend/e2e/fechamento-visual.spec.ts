// T-375 parte 2 · Passada visual do fechamento da fase 1 (1440 e 390 px): Reembolsos, Pendências do pagamento,
// Recebimentos da implantação e Controle do suporte. Confere que carrega, sem erro de API, sem rolagem lateral, e guarda a captura.
import { expect, test } from "@playwright/test";
import { executarNoBackend, restaurarSeed } from "./suporte/ambiente";
import { novaSessao, semRolagemLateral, SENHA } from "./suporte/tela";

const TELAS = [
  { rota: "/financeiro/reembolsos", titulo: /Reembolsos/, arquivo: "reembolsos" },
  { rota: "/financeiro/pendencias-pagamento", titulo: /Pendências do pagamento/, arquivo: "pendencias-pagamento" },
  { rota: "/implantacao/recebimentos", titulo: /Recebimentos|Conectar recebimentos/, arquivo: "implantacao-recebimentos" },
  { rota: "/admin/suporte", titulo: /Controle do suporte/, arquivo: "controle-do-suporte" },
];

test("passada visual das telas novas da fase 1", async ({ browser }, info) => {
  await restaurarSeed();
  executarNoBackend(`
from django_tenants.utils import schema_context
from apps.plataforma.models import UsoEmpresa, Empresa
e = Empresa.objects.get(subdominio="motorapida")
with schema_context("public"):
    u = UsoEmpresa.objects.get(empresa=e)
    u.passos_implantacao = {k: v for k, v in u.passos_implantacao.items() if k != "recebimentos"}
    u.save()
from seed.moto_rapida import codigo_de_2fa
print("CODIGO=" + codigo_de_2fa("mariana@motorapida.com.br"))
`);
  const codigo = executarNoBackend(`
from seed.moto_rapida import codigo_de_2fa
print("CODIGO=" + codigo_de_2fa("mariana@motorapida.com.br"))
`).CODIGO as string;
  const { page, vigia } = await novaSessao(browser, info);
  // Achado: o backend não manda `reembolsos` nem `pendencias_pagamento` no menu (docs/api/contas.md, linhas 202-203),
  // e a guarda de rota bloqueia as duas telas. Para ver as telas mesmo assim, o teste acrescenta os itens à resposta de auth/eu/.
  const menu = { vinham: new Set<string>() };
  await page.route("**/api/auth/eu/", async (rota) => {
    const resposta = await rota.fetch();
    const corpo = (await resposta.json()) as { navegacao?: { menu_completo: { itens: { chave: string; rotulo: string }[]; rotulo?: string }[] } };
    const grupos = corpo.navegacao?.menu_completo ?? [];
    for (const g of grupos) for (const i of g.itens) menu.vinham.add(i.chave);
    const financeiro = grupos.find((g) => g.itens.some((i) => i.chave === "caixa"));
    for (const [chave, rotulo] of [["reembolsos", "Reembolsos"], ["pendencias_pagamento", "Pendências do pagamento"]] as const) {
      if (financeiro && !menu.vinham.has(chave)) financeiro.itens.push({ chave, rotulo });
    }
    await rota.fulfill({ response: resposta, json: corpo });
  });
  await page.goto("/entrar");
  await page.locator("input[name=email]").fill("mariana@motorapida.com.br");
  await page.locator("input[name=senha]").fill(SENHA);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await page.getByLabel("Dígito 1 de 6").click();
  await page.keyboard.type(codigo);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/inicio/);

  const largura = info.project.name === "celular" ? "390" : "1440";
  for (const t of TELAS) {
    await test.step(`${t.rota} a ${largura} px`, async () => {
      await page.goto(t.rota);
      await page.waitForLoadState("networkidle");
      await expect.soft(page.getByRole("heading", { name: t.titulo }).first(), `${t.rota}: título`).toBeVisible();
      await semRolagemLateral(page, `${t.rota} a ${largura} px`);
      await page.screenshot({ path: `../docs/qa/fechamento-fase-1/${t.arquivo}-${largura}.png`, fullPage: true });
    });
  }
  expect.soft([...menu.vinham].filter((c) => c === "reembolsos" || c === "pendencias_pagamento"), "o menu da API traz Reembolsos e Pendências do pagamento").toHaveLength(2);
  vigia.verificar();
});

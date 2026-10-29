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
      await expect(page.getByText(/^Carregando/)).toHaveCount(0);
      await expect.soft(page.getByRole("heading", { name: t.titulo }).first(), `${t.rota}: título`).toBeVisible();
      await semRolagemLateral(page, `${t.rota} a ${largura} px`);
      await page.screenshot({ path: `../docs/qa/fechamento-fase-1/${t.arquivo}-${largura}.png`, fullPage: true });
    });
  }
  vigia.verificar();
});

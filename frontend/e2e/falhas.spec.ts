// T-025 · CA-025-11: falhas que o teste tem que pegar. Desktop, seed novo.
import { expect, test } from "@playwright/test";
import { restaurarSeed } from "./suporte/ambiente";
import { cadastrarClienteSemFotos, criarLocacao, receberEmDinheiro } from "./suporte/passos";
import { entrar, exigirHoraSegura, horaDeAgora, novaSessao, visivel } from "./suporte/tela";

test("cliente sem fotos: a retirada não é liberada e o pagamento sozinho não ativa a locação", async ({ browser }, info) => {
  exigirHoraSegura();
  await restaurarSeed();
  const { page, vigia } = await novaSessao(browser, info);
  await entrar(page, "bruna");

  const clienteId = await cadastrarClienteSemFotos(page);
  const locacao = await criarLocacao(page, clienteId, horaDeAgora());

  await test.step("CLI-03: na vistoria de saída a retirada não está liberada", async () => {
    await expect(visivel(page.getByText("Retirada"))).toBeVisible();
    await expect(page.getByText("Liberada", { exact: true }).filter({ visible: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Continuar para assinatura" })).toBeDisabled();
  });

  await test.step("Pagamento antes da vistoria e da assinatura deixa a locação aguardando retirada", async () => {
    await page.goto("/financeiro/caixa");
    await receberEmDinheiro(page, locacao.codigo, /R\$ 329,00/);
    await page.goto(`/locacoes/${locacao.id}`);
    await expect(visivel(page.getByText("Aguardando assinatura"))).toBeVisible();
    await expect(page.getByText("Ativa", { exact: true }).filter({ visible: true })).toHaveCount(0);
  });

  vigia.verificar();
});

// T-025 · Desktop (1440 × 900): Bruna faz tudo, de 07 a 14 out (docs/qa/criterios/T-025.md, CA-025-01 a CA-025-09).
import { expect, test } from "@playwright/test";
import { definirData, restaurarSeed } from "./suporte/ambiente";
import {
  abrirCaixaDe14Out,
  acertarEEncerrar,
  assinarPeloLink,
  cadastrarCliente,
  caixaMostra,
  contaDoAcertoPaga,
  criarLocacao,
  gerarContratoEPegarToken,
  receberCaucaoPeloBackend,
  receberEmDinheiro,
  recusarCpfJaCadastrado,
  situacaoNaFrota,
  vistoriaDeChegada,
  vistoriaDeSaida,
  vistoriaFechadaParaEdicao,
} from "./suporte/passos";
import { defeitoConhecido, entrar, exigirHoraSegura, horaDeAgora, novaSessao, semRolagemLateral, SENHA, visivel } from "./suporte/tela";

test.describe.configure({ mode: "serial" });

test("locação completa no desktop: login, cliente, locação, vistoria, assinatura, caixa, devolução e baixa", async ({ browser }, info) => {
  exigirHoraSegura();
  await restaurarSeed();
  const { page, vigia } = await novaSessao(browser, info);
  const hora = horaDeAgora();

  await test.step("CA-025-01 · Entrar: senha errada não entra; a certa cai no início da vendedora", async () => {
    vigia.esperar(401, /\/api\/auth\//);
    await page.goto("/entrar");
    await page.locator("input[name=email]").fill("bruna@motorapida.com.br");
    await page.locator("input[name=senha]").fill(`${SENHA}-errada`);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/entrar/);
    await entrar(page, "bruna");
    await expect(page.getByText("Boa", { exact: false }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Locações" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Clientes" }).first()).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Menu principal" }).getByRole("link", { name: /Usuários|Auditoria|Marca/ })).toHaveCount(0);
  });

  let clienteId = 0;
  await test.step("CA-025-02 · Cliente novo: CPF repetido é recusado; o cadastro sai completo com as fotos", async () => {
    vigia.esperar(409, /\/api\/clientes\//);
    await recusarCpfJaCadastrado(page);
    clienteId = await cadastrarCliente(page);
  });

  const locacao = await test.step("CA-025-03 · Passo 1: R$ 629,00 na retirada e a locação nasce aguardando retirada", async () => {
    const criada = await criarLocacao(page, clienteId, hora);
    await page.goto(`/locacoes/${criada.id}`);
    await expect(visivel(page.getByText("Aguardando assinatura"))).toBeVisible();
    await expect(visivel(page.getByRole("link", { name: "Fazer vistoria de saída" }))).toBeVisible();
    return criada;
  });
  expect(locacao.codigo).toBe("LOC-2866");

  await test.step("CA-025-04 · Passo 2: vistoria de saída", async () => {
    await vistoriaDeSaida(page, locacao.id, { verValores: true });
    vigia.esperar(409, /\/api\/locacoes\/\d+\/vistorias\//);
    await vistoriaFechadaParaEdicao(page, locacao.id);
  });

  await test.step("Com a vistoria feita e sem assinatura nem pagamento, a locação segue aguardando retirada (CA-025-11)", async () => {
    await page.goto(`/locacoes/${locacao.id}`);
    await expect(visivel(page.getByText("Aguardando assinatura"))).toBeVisible();
    await expect(page.getByText("Ativa", { exact: true }).filter({ visible: true })).toHaveCount(0);
  });

  await test.step("CA-025-05 · Passo 3: o cliente assina pelo link", async () => {
    const token = gerarContratoEPegarToken(locacao.codigo);
    await assinarPeloLink(browser, info, token);
    await page.goto(`/locacoes/${locacao.id}`);
    await expect(visivel(page.getByText("Aguardando pagamento"))).toBeVisible();
    await expect(visivel(page.getByText("Assinado", { exact: true }))).toBeVisible();
  });

  await test.step("CA-025-06 · Caixa de 07 out: parcela 1 e caução em dinheiro", async () => {
    await page.goto("/financeiro/caixa");
    await expect(page.getByText("R$ 281,00").first()).toBeVisible();
    await receberEmDinheiro(page, locacao.codigo, /R\$ 329,00/);
    // D-01: a busca do caixa não traz a caução (a API só a inclui por cliente ou origem, e a tela busca por texto).
    const achou = await defeitoConhecido("D-01", "a caução não aparece na busca por locação do caixa (FIN-15, CA-023-15)", async () => {
      await receberEmDinheiro(page, locacao.codigo, /R$ 300,00/);
    });
    if (!achou) receberCaucaoPeloBackend(locacao.id, 30_000);
    await caixaMostra(page, { entrou: "R$ 1.740,90", recebimentos: "7 recebimentos", gaveta: "R$ 910,00" });
  });

  await test.step("CA-025-07 · Locação ativa", async () => {
    await page.goto(`/locacoes/${locacao.id}`);
    await expect(visivel(page.getByText("Ativa", { exact: true }))).toBeVisible();
    await expect(visivel(page.getByText("saiu com 28.420 km"))).toBeVisible();
    await situacaoNaFrota(page, "HUG-1S04", "Alugado");
    await semRolagemLateral(page, "ficha da locação");
  });

  await definirData("2026-10-14");
  // Uma semana depois a sessão de 07 out já expirou no relógio simulado: a Bruna entra de novo.
  vigia.esperar(401, /\/api\/auth\//);

  await test.step("CA-025-08 · Devolução em 14 out: vistoria de chegada e acerto de R$ 80,00 a cobrar", async () => {
    await entrar(page, "bruna");
    await vistoriaDeChegada(page, locacao.id);
    await acertarEEncerrar(page, locacao.id);
    await situacaoNaFrota(page, "HUG-1S04", "Disponível");
  });

  await test.step("CA-025-09 · Baixa do acerto no caixa de 14 out: R$ 80,00, gaveta de R$ 280,00", async () => {
    await abrirCaixaDe14Out(page);
    await receberEmDinheiro(page, locacao.codigo, /R$ 80,00/);
    await caixaMostra(page, { entrou: "R$ 80,00", recebimentos: "1 recebimento", gaveta: "R$ 280,00" });
    await contaDoAcertoPaga(page, locacao.id, locacao.codigo);
  });

  vigia.verificar();
});

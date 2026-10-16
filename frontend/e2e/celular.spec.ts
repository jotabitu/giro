// T-025 · Celular (390 × 844, toque): o mesmo fluxo dividido como na loja (CA-025-10).
// Bruna cadastra, cria a locação e recebe no caixa; João (vistoriador) faz as duas vistorias pela agenda.
import { expect, test } from "@playwright/test";
import { definirData, restaurarSeed } from "./suporte/ambiente";
import {
  abrirCaixaDe14Out,
  abrirPelaAgenda,
  acertarEEncerrar,
  assinarPeloLink,
  cadastrarCliente,
  caixaMostra,
  contaDoAcertoPaga,
  criarLocacao,
  gerarContratoEPegarToken,
  menuDoVistoriador,
  receberEmDinheiro,
  vistoriaDeChegada,
  vistoriaDeSaida,
} from "./suporte/passos";
import { entrar, exigirHoraSegura, horaDeAgora, novaSessao, semRolagemLateral, visivel } from "./suporte/tela";

test("locação completa no celular: Bruna na frente, João nas vistorias", async ({ browser }, info) => {
  exigirHoraSegura();
  await restaurarSeed();
  const bruna = await novaSessao(browser, info);
  const joao = await novaSessao(browser, info);
  const hora = horaDeAgora();

  await entrar(bruna.page, "bruna");
  await entrar(joao.page, "joao");

  const clienteId = await test.step("Bruna cadastra o cliente com as fotos", async () => {
    const id = await cadastrarCliente(bruna.page);
    await semRolagemLateral(bruna.page, "ficha do cliente");
    return id;
  });

  const locacao = await test.step("Bruna cria a locação: R$ 629,00 na retirada", async () => {
    const criada = await criarLocacao(bruna.page, clienteId, hora);
    await semRolagemLateral(bruna.page, "nova locação");
    return criada;
  });
  expect(locacao.codigo).toBe("LOC-2866");

  await test.step("João vê só o menu dele e faz a vistoria de saída pela agenda, sem valores", async () => {
    await menuDoVistoriador(joao.page);
    await abrirPelaAgenda(joao.page, "vistoria", locacao.id);
    joao.vigia.esperar(422, /\/api\/vistorias\/\d+\/concluir\//); // km menor que o do veículo (VEI-01)
    await vistoriaDeSaida(joao.page, locacao.id, { verValores: false });
    await semRolagemLateral(joao.page, "vistoria de saída");
  });

  await test.step("O cliente assina pelo link e Bruna recebe no caixa", async () => {
    await assinarPeloLink(browser, info, gerarContratoEPegarToken(locacao.codigo));
    await bruna.page.goto("/financeiro/caixa");
    await receberEmDinheiro(bruna.page, locacao.codigo, /R\$ 329,00/);
    await receberEmDinheiro(bruna.page, locacao.codigo, /R\$ 300,00/);
    await caixaMostra(bruna.page, { entrou: "R$ 1.740,90", recebimentos: "7 recebimentos", gaveta: "R$ 910,00", movimentos: 9 });
    await semRolagemLateral(bruna.page, "caixa do dia");
    await bruna.page.goto(`/locacoes/${locacao.id}`);
    await expect(visivel(bruna.page.getByText("Ativa", { exact: true }))).toBeVisible();
  });

  // Sem página aberta durante a troca do relógio: as telas consultam a API e pegariam o backend reiniciando.
  await bruna.page.goto("about:blank");
  await joao.page.goto("about:blank");
  await definirData("2026-10-14");

  await test.step("14 out: João faz a vistoria de chegada pela agenda; Bruna fecha o acerto", async () => {
    await entrar(joao.page, "joao");
    await vistoriaDeChegada(joao.page, locacao.id, { pelaAgenda: true });
    await expect(visivel(joao.page.getByText(/R\$ \d/))).toHaveCount(0);
    await entrar(bruna.page, "bruna");
    await acertarEEncerrar(bruna.page, locacao.id);
    await semRolagemLateral(bruna.page, "devolução");
  });

  await test.step("Bruna abre o caixa e recebe os R$ 80,00", async () => {
    await abrirCaixaDe14Out(bruna.page);
    await receberEmDinheiro(bruna.page, locacao.codigo, /R\$ 80,00/);
    await caixaMostra(bruna.page, { entrou: "R$ 80,00", recebimentos: "1 recebimento", gaveta: "R$ 280,00", movimentos: 1 });
    await contaDoAcertoPaga(bruna.page, locacao.id, locacao.codigo);
  });

  bruna.vigia.verificar();
  joao.vigia.verificar();
});

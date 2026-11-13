// T-420 · Locação com intenção de compra (LOC-16, VEN-11) contra docs/telas/html/Locacao-Compra-*, Locacao-Detalhe-Compra-* e Vendas-*.
// Os textos de andamento, as recusas e as ações vêm da API (aqui, o falso que imita docs/api/locacoes.md e vendas.md); a tela só mostra.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { clientes, contas, ErroApi, locacoes, vendas, veiculos } from "@/lib/api";
import { corpoDaLocacao, valoresIniciais } from "@/lib/locacao-form";
import { textoDaTransferencia } from "@/lib/locacao-compra";
import { modeloDeCompra } from "@/testes/falsos/falso-locacoes";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes", useSearchParams: () => new URLSearchParams() }));

import { DetalheDaLocacao } from "./DetalheDaLocacao";
import { NovaLocacao } from "./NovaLocacao";
import { ListaDeVendas } from "../vendas/ListaDeVendas";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const falha = async (p: Promise<unknown>) => {
  try {
    await p;
  } catch (e) {
    return e as ErroApi;
  }
  throw new Error("esperava erro");
};

async function ficha(id: number): Promise<{ desktop: string; celular: string }> {
  const cache = new QueryClient();
  cache.setQueryData(["locacao", id], await locacoes.obter(id));
  cache.setQueryData(["locacao", id, "historico"], await locacoes.historico(id));
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDaLocacao id={id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = html.match(/^<div class="hidden flex-col gap-6 md:flex">(.*)<\/div><div class="flex flex-col gap-4 md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop: texto(desktop), celular: texto(celular) };
}

describe("T-420 vendedora: sem ações de gerente", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));

  it("test_ven_11_vendedora_nao_registra_transferencia_nem_encerra_por_atraso", async () => {
    const { desktop } = await ficha(2870);
    expect(desktop).not.toContain("Encerrar por atraso");
    expect(desktop).toContain("não se renova nem troca de veículo");
    const quitada = await ficha(2901);
    expect(quitada.desktop).toContain("Pendente");
    expect(quitada.desktop).not.toContain("Data da transferência");
  });
});

describe("T-420 ficha da locação com intenção de compra, gerente", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("test_loc_16_ficha_mostra_a_parcela_paga_com_a_caucao_sem_conta_e_a_caucao_abatida", async () => {
    const l = await locacoes.obter(2870);
    const zero = l.parcelas?.find((p) => p.paga_com_caucao);
    expect(zero).toMatchObject({ id: null, conta_id: null, valor_centavos: 0, observacao: "paga com a caução" });
    const { desktop, celular } = await ficha(2870);
    for (const t of [desktop, celular]) {
      expect(t).toContain("paga com a caução");
      expect(t).toContain("caução abatida");
    }
    // Sem conta: o botão de pagamento só existe nas parcelas com conta.
    expect(texto(desktop)).not.toContain("Registrar pagamento: Parcela 5");
    expect(desktop).not.toContain('aria-label="Registrar pagamento: Parcela 5"');
  });

  it("test_loc_16_ficha_mostra_o_tipo_o_andamento_e_a_parcela_atrasada", async () => {
    const { desktop, celular } = await ficha(2870);
    for (const t of [desktop, celular]) {
      expect(t).toContain("Com intenção de compra");
      expect(t).toContain("Andamento da compra");
      expect(t).toContain("Parcela 2 de 24 · faltam 22 para a transferência");
      expect(t).toContain("Parcela 6 atrasada");
      expect(t).toContain("Compra Street 24 meses");
    }
    expect(desktop).toContain("2 de 24 parcelas pagas");
  });

  it("test_loc_16_sem_renovar_nem_trocar_e_com_encerrar_por_atraso", async () => {
    const { desktop, celular } = await ficha(2870);
    for (const t of [desktop, celular]) {
      // D3 do #568: os botões ficam desligados, com a explicação embaixo.
      expect(t).toContain("A locação com intenção de compra não se renova nem troca de veículo. Encerre esta e abra outra.");
      expect(t).toContain("Encerrar por atraso");
      expect(t).toContain("Cancelar locação");
    }
  });

  it("test_loc_16_resumo_com_a_ultima_parcela_da_api", async () => {
    const { desktop } = await ficha(2870);
    expect(desktop).toContain("Última parcela");
    expect(desktop).toContain("R$ 890,00");
    expect(desktop).toContain("R$ 1.190,00 · mensal");
    expect(desktop).toContain("Caução");
  });

  it("test_ven_11_quitada_mostra_a_venda_e_a_transferencia_pendente", async () => {
    const { desktop, celular } = await ficha(2901);
    for (const t of [desktop, celular]) {
      expect(t).toContain("Quitada em 10/10/2028 · falta a transferência no Detran");
      expect(t).toContain("Transferência no Detran");
      expect(t).toContain("Pendente");
      expect(t).toContain("Fazer a transferência no Detran: RTA-2C55 para Lucas Ferreira. LOC-2901 quitada em 10/10/2028.");
      expect(t).toContain("Transferência feita");
      expect(t).toContain("VEN-0178");
      expect(t).toContain("Quitação de locação");
      expect(t).not.toContain("Encerrar por atraso");
    }
  });

  it("test_ven_11_texto_da_transferencia", async () => {
    expect(textoDaTransferencia(await locacoes.obter(2901))).toBe("Fazer a transferência no Detran: RTA-2C55 para Lucas Ferreira. LOC-2901 quitada em 10/10/2028.");
  });

  it("test_ven_11_registrar_transferencia_tira_o_botao_e_uma_segunda_vez_e_recusada", async () => {
    const l = await locacoes.registrarTransferencia(2901, { feita_em: "2028-10-15" });
    expect(l.compra?.andamento).toBe("Quitada em 10/10/2028 · transferência feita em 15/10/2028");
    expect(l.compra?.venda?.acoes.registrar_transferencia).toBe(false);
    const { desktop } = await ficha(2901);
    expect(desktop).toContain("Transferência feita em 15/10/2028 · Rodrigo Pinheiro");
    expect(desktop).not.toContain("Data da transferência");
    const erro = await falha(locacoes.registrarTransferencia(2901, { feita_em: "2028-10-16" }));
    expect(erro.status).toBe(409);
    expect(erro.codigo).toBe("VEN-11");
    expect(erro.message).toBe("A transferência desta venda já foi registrada.");
  });

  it("test_loc_16_recusas_de_renovar_e_trocar_com_o_texto_da_regra", async () => {
    expect((await falha(locacoes.simularRenovacao(2870, { periodos: 1 }))).message).toBe("A locação com intenção de compra não se renova.");
    expect((await falha(locacoes.trocarVeiculo(2870, { veiculo_novo_id: 501, motivo: "x" }))).message).toBe("A locação com intenção de compra não troca de veículo. Encerre esta e abra outra.");
  });

  it("test_loc_16_encerrar_por_atraso_so_com_data_de_hoje", async () => {
    const e = await falha(locacoes.encerrarPorAtraso(2870, { motivo: "Parcela 6 com 16 dias de atraso", data: "2026-10-01" }));
    expect(e.status).toBe(400);
    const l = await locacoes.encerrarPorAtraso(2870, { motivo: "Parcela 6 com 16 dias de atraso", data: "2026-10-07" });
    expect(l.cancelamento?.por_atraso).toBe(true);
    expect(l.cancelamento?.multa_centavos).toBe(0);
  });

  it("test_loc_16_encerrar_por_atraso_sem_parcela_atrasada_e_recusado", async () => {
    const e = await falha(locacoes.encerrarPorAtraso(2901, { motivo: "x" }));
    expect(e.codigo).toBe("LOC-16");
    expect(e.message).toBe("Esta locação não tem parcela atrasada. Para encerrar a pedido do cliente, use Cancelar locação.");
  });
});

describe("T-420 nova locação com intenção de compra", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));
  afterEach(() => vi.useRealTimers());
  const AGORA = new Date("2026-10-07T12:20:00Z");

  it("test_loc_16_corpo_leva_o_tipo_e_o_plano_sem_desconto_nem_extras", async () => {
    const { resultados } = await locacoes.planosDeCompra();
    const v = { ...valoresIniciais(1206, 504, AGORA), tipo: "intencao_compra" as const, plano_compra_id: 3, desconto: "10", extras: [1] };
    expect(corpoDaLocacao(v, [], resultados)).toMatchObject({ tipo: "intencao_compra", plano_compra_id: 3, periodicidade: "mensal", desconto_pct: "0", extras: [] });
    expect(corpoDaLocacao({ ...v, plano_compra_id: null }, [], resultados)).toBeNull();
  });

  it("test_loc_16_simulacao_traz_parcelas_e_a_ultima_com_a_caucao_abatida", async () => {
    const { resultados } = await locacoes.planosDeCompra();
    const corpo = corpoDaLocacao({ ...valoresIniciais(1206, 504, AGORA), tipo: "intencao_compra", plano_compra_id: 3 }, [], resultados)!;
    const sim = await locacoes.simular(corpo);
    expect(sim.parcelas_previstas).toHaveLength(24);
    expect(sim.parcelas_previstas[0]?.valor_centavos).toBe(119000);
    expect(sim.parcelas_previstas[23]?.valor_centavos).toBe(89000);
    expect(sim.compra?.ultima_parcela_centavos).toBe(89000);
    expect(sim.hoje_na_retirada_centavos).toBe(149000);
  });

  it("test_loc_16_sem_modelo_publicado_a_confirmacao_e_recusada_com_o_atalho", async () => {
    const { resultados } = await locacoes.planosDeCompra();
    const corpo = corpoDaLocacao({ ...valoresIniciais(1206, 504, AGORA), tipo: "intencao_compra", plano_compra_id: 3 }, [], resultados)!;
    modeloDeCompra.publicado = false;
    try {
      expect((await locacoes.simular(corpo)).avisos[0]).toMatchObject({ codigo: "LOC-16", link: "/admin/contratos" });
      const rascunho = await locacoes.criar(corpo);
      const erro = await falha(locacoes.confirmar(rascunho.id));
      expect(erro.status).toBe(422);
      expect(erro.codigo).toBe("LOC-16");
      expect(erro.message).toBe("Publique o modelo de contrato da locação com intenção de compra antes de confirmar.");
      expect(erro.detalhes?.link).toBe("/admin/contratos");
    } finally {
      modeloDeCompra.publicado = true;
    }
  });

  it("test_loc_16_tela_escolhe_o_tipo_e_o_plano_e_esconde_desconto_e_extras", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(AGORA);
    const { resultados } = await locacoes.planosDeCompra();
    const corpo = corpoDaLocacao({ ...valoresIniciais(1206, 504, AGORA), tipo: "intencao_compra", plano_compra_id: 3 }, [], resultados)!;
    const cache = new QueryClient();
    cache.setQueryData(["cliente", 1206], await clientes.obter(1206));
    cache.setQueryData(["veiculo", 504], await veiculos.obter(504));
    cache.setQueryData(["extras"], await locacoes.extras());
    cache.setQueryData(["planos-especiais"], await locacoes.planosEspeciais());
    cache.setQueryData(["planos-compra"], { resultados });
    cache.setQueryData(["locacao-simulacao", JSON.stringify(corpo)], await locacoes.simular(corpo));
    const t = texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <NovaLocacao clienteInicial={1206} veiculoInicial={504} tipoInicial="intencao_compra" planoDeCompraInicial={3} />
        </QueryClientProvider>,
      ),
    );
    for (const trecho of ["Tipo de locação", "Comum", "Com intenção de compra", "Plano de compra", "Compra Street 24 meses", "24 parcelas de R$ 1.190,00 · mensal", "Fim previsto", "o veículo passa ao cliente na última parcela", "Abatida na última parcela", "24 parcelas mensais × R$ 1.190,00", "Última parcela", "R$ 890,00", "R$ 1.490,00", "Ao quitar a última parcela, o veículo passa ao cliente sem valor extra."]) {
      expect(t, trecho).toContain(trecho);
    }
    for (const fora of ["Desconto (%)", "Adicionais", "Plano e período", "Parcelamento"]) expect(t, fora).not.toContain(fora);
  });

  it("test_loc_16_locacao_comum_continua_com_desconto_e_adicionais", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(AGORA);
    const cache = new QueryClient();
    cache.setQueryData(["extras"], await locacoes.extras());
    cache.setQueryData(["planos-especiais"], await locacoes.planosEspeciais());
    const t = texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <NovaLocacao />
        </QueryClientProvider>,
      ),
    );
    expect(t).toContain("Tipo de locação");
    expect(t).toContain("Plano e período");
    expect(t).toContain("Adicionais");
    expect(t).not.toContain("Plano de compra");
  });
});

describe("T-420 vendas: a venda da quitação", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("test_ven_11_lista_com_transferencia_pendente_e_o_rotulo_quitacao_de_locacao", async () => {
    const cache = new QueryClient();
    cache.setQueryData(["vendas", "pendentes"], await vendas.listar({ transferencia_pendente: true }));
    cache.setQueryData(["vendas", "lista", null], await vendas.listar());
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <ListaDeVendas />
      </QueryClientProvider>,
    );
    const t = texto(html);
    for (const trecho of ["Vendas", "Transferências pendentes", "1 no Detran", "Lucas Ferreira", "VEN-0178 · LOC-2901", "Honda CG 160 Fan", "RTA-2C55", "Quitação de locação", "Falta a transferência no Detran", "Abrir locação", "R$ 0,00"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(html).toContain('href="/locacoes/2901"');
    // Os dois formatos: tabela no desktop e cartões no celular.
    expect(html).toContain("hidden overflow-x-auto md:block");
    expect(html).toContain("flex flex-col gap-3 md:hidden");
  });

  it("test_ven_11_vistoriador_nao_ve_vendas", async () => {
    await entrarComo("joao@motorapida.com.br");
    expect((await falha(vendas.listar())).status).toBe(403);
  });
});

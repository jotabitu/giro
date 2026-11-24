// T-486 e T-487 · Blocos do início (VEI-18, VEI-19, VEI-20, VEN-12) com os números de docs/regras/dados-de-teste.md
// (Filial Centro em 07 out). Tudo vem da API; a tela só mostra.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu, EstoqueAVenda, InicioDe, ParadosAVenda, TicketMedio } from "@/lib/api";
import { BlocoEstoqueAVenda, BlocoParadosAVenda, BlocoTicketMedio } from "./EstoqueAVenda";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { InicioGerente } from "./InicioGerente";

const html = (el: ReactElement) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

const ESTOQUE: EstoqueAVenda = {
  quantidade: 12,
  subtitulo: "12 veículos à venda · Filial Centro",
  capital_imobilizado_centavos: 3950000,
  veiculos_na_conta: 3,
  legenda_capital: "compra e despesas de 3 veículos",
  custo_medio_centavos: 1316667,
  legenda_custo_medio: "3 veículos na conta",
  margem_centavos: 210000,
  margem_pct: "5.05",
  margem_negativa: false,
  margem_texto: "R$ 2.100,00",
  legenda_margem: "5,05% sobre o valor de venda",
  sem_valor_compra: 9,
  sem_valor_venda: 0,
  avisos: ["9 veículos sem valor de compra não entram na conta."],
};

const PARADOS: ParadosAVenda = {
  limite_dias_parado: 30,
  acima_do_limite: 2,
  subtitulo: "2 acima de 30 dias",
  itens: [
    { id: 1, placa: "PVE1A07", veiculo: "Honda Biz 125", dias_em_estoque: 53, parado: true },
    { id: 2, placa: "PVF2B18", veiculo: "Honda CG 160 Fan", dias_em_estoque: 31, parado: true },
    { id: 3, placa: "PVG3C29", veiculo: "Yamaha Factor 150", dias_em_estoque: 30, parado: false },
    { id: 4, placa: "QYB5H60", veiculo: "Honda CB 300F Twister", dias_em_estoque: 0, parado: false },
    { id: 5, placa: "QZD6B02", veiculo: "Honda Pop 110i", dias_em_estoque: 0, parado: false },
  ],
};

const SEM_VENDAS: TicketMedio = {
  mes: "novembro",
  vendas: 0,
  soma_centavos: 0,
  ticket_centavos: null,
  subtitulo: "Vendas de novembro · Filial Centro",
  rotulo: "Ticket médio de novembro",
  resumo: null,
  vazio: "Sem vendas em novembro.",
  mes_anterior: { mes: "outubro", vendas: 0, soma_centavos: 0, ticket_centavos: null },
  variacao_pct: null,
  comparacao: null,
};

describe("Estoque à venda (VEI-20)", () => {
  it("test_vei_20_capital_custo_medio_e_margem_como_a_api_manda", () => {
    const t = texto(html(<BlocoEstoqueAVenda e={ESTOQUE} />));
    for (const esperado of [
      "Estoque à venda",
      "12 veículos à venda · Filial Centro",
      "Capital imobilizado",
      "R$ 39.500,00",
      "compra e despesas de 3 veículos",
      "Custo médio por unidade",
      "R$ 13.166,67",
      "3 veículos na conta",
      "Margem potencial",
      "R$ 2.100,00",
      "5,05% sobre o valor de venda",
      "9 veículos sem valor de compra não entram na conta.",
      "Ver na lista",
    ])
      expect(t).toContain(esperado);
  });

  it("test_vei_20_margem_negativa_com_sinal_e_tom_critico", () => {
    const negativa = { ...ESTOQUE, capital_imobilizado_centavos: 1395000, custo_medio_centavos: 1395000, margem_centavos: -75000, margem_pct: "-5.68", margem_negativa: true, margem_texto: "−R$ 750,00", legenda_margem: "−5,68% sobre o valor de venda" };
    const h = html(<BlocoEstoqueAVenda e={negativa} />);
    expect(texto(h)).toContain("−R$ 750,00");
    expect(texto(h)).toContain("−5,68% sobre o valor de venda");
    expect(h).toContain("color:var(--critical-ink)");
  });

  it("test_vei_20_nenhum_com_valor_de_compra", () => {
    const vazio = {
      ...ESTOQUE,
      capital_imobilizado_centavos: 0,
      veiculos_na_conta: 0,
      custo_medio_centavos: null,
      legenda_custo_medio: null,
      margem_centavos: null,
      margem_pct: null,
      margem_texto: null,
      legenda_margem: null,
      legenda_capital: "Nenhum veículo à venda com valor de compra.",
      sem_valor_compra: 12,
      avisos: ["12 veículos sem valor de compra não entram na conta."],
    };
    const t = texto(html(<BlocoEstoqueAVenda e={vazio} />));
    expect(t).toContain("R$ 0,00");
    expect(t).toContain("Nenhum veículo à venda com valor de compra.");
    expect(t).not.toContain("Custo médio por unidade");
    expect(t).not.toContain("Margem potencial");
  });
});

describe("Parados à venda (VEI-18, VEI-19)", () => {
  it("test_vei_18_os_cinco_mais_parados_com_o_destaque_do_parado", () => {
    const h = html(<BlocoParadosAVenda p={PARADOS} />);
    const t = texto(h);
    expect(t).toContain("2 acima de 30 dias");
    expect(t).toContain("Ver todos");
    expect(t).toMatch(/PVE-1A07\|Honda Biz 125\|53 dias\|PVF-2B18\|Honda CG 160 Fan\|31 dias\|PVG-3C29\|Yamaha Factor 150\|30 dias\|QYB-5H60/);
    expect(t).toContain("Hoje");
    expect(h.match(/wl-badge--warning/g)).toHaveLength(2); // só os parados
    expect(h).toContain('href="/veiculos?status=a_venda"');
    expect(h).toContain('href="/veiculos/1"');
  });

  it("test_vei_18_filial_sem_veiculo_a_venda", () => {
    const t = texto(html(<BlocoParadosAVenda p={{ ...PARADOS, acima_do_limite: 0, subtitulo: "Nenhum acima de 30 dias", itens: [] }} />));
    expect(t).toContain("Nenhum veículo à venda nesta filial.");
  });
});

describe("Ticket médio do mês (VEN-12)", () => {
  it("test_ven_12_sem_vendas_ate_o_fluxo_de_venda", () => {
    const t = texto(html(<BlocoTicketMedio t={SEM_VENDAS} />));
    expect(t).toContain("Vendas de novembro · Filial Centro");
    expect(t).toContain("Sem vendas em novembro.");
    expect(t).not.toContain("R$");
  });

  it("test_ven_12_ticket_e_comparacao_como_a_api_manda", () => {
    const outubro = {
      ...SEM_VENDAS,
      mes: "outubro",
      vendas: 4,
      soma_centavos: 3120000,
      ticket_centavos: 780000,
      subtitulo: "Vendas de outubro · Filial Centro",
      rotulo: "Ticket médio de outubro",
      resumo: "4 vendas · R$ 31.200,00",
      vazio: null,
      comparacao: "−43,27% em relação a setembro (R$ 13.750,00)",
      variacao_pct: "-43.27",
    };
    const t = texto(html(<BlocoTicketMedio t={outubro} />));
    expect(t).toContain("Ticket médio de outubro");
    expect(t).toContain("R$ 7.800,00");
    expect(t).toContain("4 vendas · R$ 31.200,00");
    expect(t).toContain("−43,27% em relação a setembro (R$ 13.750,00)");
  });
});

describe("início do gerente com os blocos", () => {
  sessao.eu = { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { locacoes_criar: true } };
  const base = { variante: "gerente", saudacao: "Bom dia, Rodrigo", atualizado_em: "2026-10-07T12:00:00Z", aprovacoes: { total: 0, mais_antigo: null, itens: [] }, kpis: [], equipe_hoje: [], frota_filial: { total: 0, segmentos: [] } };

  it("test_vei_20_blocos_aparecem_quando_a_api_manda", () => {
    const d = { ...base, estoque_a_venda: ESTOQUE, parados_a_venda: PARADOS, ticket_medio: SEM_VENDAS } as unknown as InicioDe<"gerente">;
    const t = texto(html(<InicioGerente d={d} />));
    expect(t).toContain("Estoque à venda");
    expect(t).toContain("Parados à venda");
    expect(t).toContain("Ticket médio do mês");
  });

  it("test_vei_20_sem_os_blocos_nada_aparece", () => {
    const t = texto(html(<InicioGerente d={base as unknown as InicioDe<"gerente">} />));
    expect(t).not.toContain("Estoque à venda");
    expect(t).not.toContain("Parados à venda");
    expect(t).not.toContain("Ticket médio");
  });
});

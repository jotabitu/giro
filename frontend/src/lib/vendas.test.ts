// T-503 · Vendas: só formatação. As contas são da API (VEN-0177 de docs/regras/dados-de-teste.md).
import { describe, expect, it } from "vitest";
import { campoDoPct, codigoEVendedor, comPorcento, linhasDoResumo, linkDoWhatsApp, mesDoDia, mesPorExtenso, pctDoCampo, pctTexto, tomDaVenda, ultimoContato } from "./vendas";

const VEN_0177 = {
  preco_tabela_centavos: 2290000,
  desconto_pct: "8.00",
  desconto_centavos: 183200,
  preco_final_centavos: 2106800,
  forma: "entrada_parcelas",
  entrada_centavos: 500000,
  num_parcelas: 12,
  parcela_centavos: 133900,
  ultima_parcela_centavos: 133900,
  comissao_centavos: 63204,
};

describe("resumo da proposta", () => {
  it("test_ven_02_ven_04_resumo_da_ven_0177_como_a_api_calcula", () => {
    expect(linhasDoResumo(VEN_0177)).toEqual([
      { rotulo: "Preço de tabela", valor: "R$ 22.900,00" },
      { rotulo: "Desconto 8%", valor: "− R$ 1.832,00" },
      { rotulo: "Preço final", valor: "R$ 21.068,00" },
      { rotulo: "Entrada", valor: "R$ 5.000,00" },
      { rotulo: "Saldo", valor: "12 × R$ 1.339,00" },
      { rotulo: "Comissão", valor: "R$ 632,04" },
    ]);
  });

  it("test_ven_03_a_vista_sem_desconto_nao_mostra_entrada_nem_saldo", () => {
    const linhas = linhasDoResumo({ ...VEN_0177, forma: "a_vista", desconto_pct: "0.00", desconto_centavos: 0, preco_final_centavos: 1320000, entrada_centavos: 1320000, num_parcelas: null, parcela_centavos: null, ultima_parcela_centavos: null, comissao_centavos: 39600 });
    expect(linhas.map((l) => l.rotulo)).toEqual(["Preço de tabela", "Preço final", "Comissão"]);
  });

  it("test_ven_04_diferenca_de_centavos_na_ultima_parcela_vem_da_api", () => {
    const linhas = linhasDoResumo({ ...VEN_0177, parcela_centavos: 133900, ultima_parcela_centavos: 133901 });
    expect(linhas.find((l) => l.rotulo === "Saldo")?.valor).toBe("12 × R$ 1.339,00");
    expect(linhas.find((l) => l.rotulo === "Última parcela")?.valor).toBe("R$ 1.339,01");
  });
});

describe("campos e textos", () => {
  it("test_ven_02_desconto_digitado_vai_com_duas_casas", () => {
    expect(pctDoCampo("8")).toBe("8.00");
    expect(pctDoCampo("7,5")).toBe("7.50");
    expect(pctDoCampo("")).toBe("0");
    expect(pctDoCampo("8%")).toBe("8.00");
    expect(campoDoPct("8.00")).toBe("8%");
    expect(campoDoPct("7.50")).toBe("7,5%");
    expect(campoDoPct("0.00")).toBe("");
    expect(pctTexto("5.00")).toBe("5%");
    expect(pctTexto("7.50")).toBe("7,5%");
    expect(comPorcento("8")).toBe("8%");
    expect(comPorcento("7,5%")).toBe("7,5%");
    expect(comPorcento("")).toBe("");
  });


  it("test_ven_16_ultimo_contato", () => {
    const agora = new Date("2026-10-07T15:00:00-03:00");
    expect(ultimoContato("2026-10-07T14:40:00-03:00", agora)).toBe("há 20 min");
    expect(ultimoContato("2026-10-07T14:00:00-03:00", agora)).toBe("há 1 h");
    expect(ultimoContato("2026-10-06T09:00:00-03:00", agora)).toBe("ontem");
    expect(ultimoContato("2026-09-29T09:00:00-03:00", agora)).toBe("há 8 dias");
    expect(ultimoContato(null, agora)).toBe("—");
  });

  it("test_ven_19_tom_da_situacao_e_codigo", () => {
    expect(tomDaVenda("aguardando_aprovacao")).toBe("alerta");
    expect(tomDaVenda("vendida")).toBe("sucesso");
    expect(tomDaVenda("perdida")).toBe("neutro");
    expect(codigoEVendedor({ codigo: "VEN-0177", vendedor: { id: 3, nome: "Bruna Alves" }, locacao: null })).toBe("VEN-0177 · Bruna");
    expect(codigoEVendedor({ codigo: "VEN-0178", vendedor: { id: 3, nome: "Bruna Alves" }, locacao: { id: 2901, codigo: "LOC-2901" } } as never)).toBe("VEN-0178 · LOC-2901");
    expect(mesPorExtenso("2026-10-07")).toBe("outubro");
    expect(mesDoDia("2026-10-07")).toBe("2026-10");
    expect(linkDoWhatsApp("85988771100")).toBe("https://wa.me/5585988771100");
  });
});

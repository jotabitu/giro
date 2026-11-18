// T-496: preços por veículo (VEI-12 a VEI-17). A tela só lê o que se digita e monta o corpo; o cálculo é da API.
import { describe, expect, it } from "vitest";
import { PRECOS_POP } from "@/testes/falsos/falso-precos-veiculo";
import {
  centavosDoCampo,
  corpoDaCompra,
  corpoDaDiferenca,
  corpoDoPlano,
  custosParaCorpo,
  custosParaRascunho,
  ehOUltimoLigado,
  errosDaApi,
  inteiroDoCampo,
  percentualDoCampo,
  rascunhoDoDocumento,
  textoDasFormas,
  textoDoAgendado,
  textoDoPagamento,
} from "./precos-veiculo";

describe("leitura do que se digita", () => {
  it("vei_12_valor_em_reais_vira_centavos", () => {
    expect(centavosDoCampo("R$ 1.250,50")).toBe(125050);
    expect(centavosDoCampo("R$ 0,35 por km")).toBe(35);
    expect(centavosDoCampo("269")).toBe(26900);
    expect(centavosDoCampo("")).toBeUndefined();
    expect(centavosDoCampo("abc")).toBeUndefined();
  });
  it("vei_12_inteiros_e_percentuais", () => {
    expect(inteiroDoCampo("1.000 km")).toBe(1000);
    expect(inteiroDoCampo("até 3 dias")).toBe(3);
    expect(percentualDoCampo("1,00%")).toBe("1.00");
    expect(percentualDoCampo("até 10%")).toBe("10.00");
    expect(percentualDoCampo("85,5")).toBe("85.50");
    expect(percentualDoCampo("1,234")).toBeUndefined();
  });
});

describe("rascunho e corpo", () => {
  const base = rascunhoDoDocumento(PRECOS_POP);

  it("vei_12_rascunho_traz_os_textos_da_tela", () => {
    const semanal = base.planos.find((p) => p.tipo === "semanal");
    expect(semanal?.valor).toBe("R$ 269,00");
    expect(semanal?.franquia).toBe("1.000 km");
    expect(base.regras.kmExcedente).toBe("R$ 0,35 por km");
    expect(base.regras.descontoPct).toBe("até 10%");
    expect(base.regras.prazoCaucao).toBe("até 3 dias");
    expect(base.compra.juros).toBe("1,00%");
  });

  it("vei_12_sem_mudanca_nao_manda_nada", () => {
    const m = corpoDaDiferenca(base, base);
    expect(m.mudou).toBe(false);
    expect(m.corpo).toEqual({ confirmar_juros: false });
  });

  it("vei_12_so_o_plano_mudado_vai_no_corpo", () => {
    const r = { ...base, planos: base.planos.map((p) => (p.tipo === "mensal" ? { ...p, valor: "R$ 1.050,00" } : p)) };
    const m = corpoDaDiferenca(r, base);
    expect(m.mudou).toBe(true);
    expect(m.planosEnviados).toEqual(["32"]);
    expect(m.corpo.planos).toHaveLength(1);
    expect(m.corpo.planos?.[0]).toMatchObject({ id: 32, valor_centavos: 105000, como_paga: "mes_quatro_semanais", caucao_centavos: 50000 });
    expect(m.corpo.plano_compra).toBeUndefined();
    expect(m.corpo.regras).toBeUndefined();
  });

  it("vei_16_compra_mudada_vai_inteira_e_em_calcular_ignora_a_parcela", () => {
    const m = corpoDaDiferenca({ ...base, compra: { ...base.compra, parcelas: "52", juros: "1,46%" } }, base, { confirmarJuros: true });
    expect(m.corpo.confirmar_juros).toBe(true);
    expect(m.corpo.plano_compra).toMatchObject({ ligado: true, periodicidade: "semanal", parcelas: 52, juros_mes_pct: "1.46", modo: "calcular", parcela_moto_centavos: 0, entrada_centavos: 100000 });
  });

  it("vei_16_digitar_manda_a_parcela_digitada", () => {
    const m = corpoDaDiferenca({ ...base, compra: { ...base.compra, modo: "digitar", parcelaMoto: "R$ 170,00" } }, base);
    expect(m.corpo.plano_compra).toMatchObject({ modo: "digitar", parcela_moto_centavos: 17000 });
  });

  it("vei_12_texto_que_nao_e_valor_vira_erro_do_campo_e_nao_vai", () => {
    const r = { ...base, valorVenda: "muito", planos: base.planos.map((p) => (p.tipo === "diaria" ? { ...p, valor: "x" } : p)) };
    const m = corpoDaDiferenca(r, base);
    expect(m.erros["valor_venda_centavos"]).toBe("Informe um valor em reais, como 54,90.");
    expect(m.erros["plano.30.valor_centavos"]).toBeDefined();
  });

  it("vei_12_ligar_plano_sem_cadastro_manda_o_tipo_e_o_periodo", () => {
    const entregador = base.planos.find((p) => p.tipo === "entregador");
    expect(entregador?.id).toBeNull();
    const m = corpoDoPlano({ ...(entregador as NonNullable<typeof entregador>), ligado: true, valor: "R$ 279,00", caucao: "R$ 0,00", formas: ["pix"] });
    expect(m.corpo.planos?.[0]).toMatchObject({ tipo: "entregador", periodo: "semana", ligado: true, valor_centavos: 27900, caucao_centavos: 0, formas_aceitas: ["pix"], como_paga: "semana_adiantado" });
    expect(m.corpo.planos?.[0]).not.toHaveProperty("id");
  });

  it("vei_12_franquia_livre_e_prazo_vazio_vao_nulos", () => {
    const semanal = base.planos.find((p) => p.tipo === "semanal") as NonNullable<(typeof base.planos)[number]>;
    const m = corpoDoPlano({ ...semanal, franquia: "livre", prazoMinimo: "" });
    expect(m.corpo.planos?.[0]).toMatchObject({ franquia_km: null, prazo_minimo_periodos: null });
  });

  it("vei_16_compra_sem_cadastro_tem_rascunho_vazio_e_nao_vai_se_nao_mexeu", () => {
    const sem = rascunhoDoDocumento({ ...PRECOS_POP, plano_compra: null });
    expect(sem.compra.ligado).toBe(false);
    expect(corpoDaDiferenca(sem, sem).mudou).toBe(false);
    expect(corpoDaCompra({ ...sem.compra, ligado: true }).corpo.plano_compra).toMatchObject({ ligado: true, parcelas: 0 });
  });
});

describe("erros da API", () => {
  it("vei_12_erro_pontuado_do_plano_cai_no_campo_do_plano_certo", () => {
    const e = errosDaApi({ "planos.1.valor_centavos": "Informe um valor maior que zero para ligar o plano.", "planos.0.formas_aceitas": "Escolha ao menos uma forma de pagamento para ligar o plano." }, ["31", "entregador"]);
    expect(e["plano.entregador.valor_centavos"]).toBe("Informe um valor maior que zero para ligar o plano.");
    expect(e["plano.31.formas_aceitas"]).toBe("Escolha ao menos uma forma de pagamento para ligar o plano.");
  });
  it("vei_16_erros_da_compra_e_da_venda", () => {
    const e = errosDaApi({ "plano_compra.entrada_centavos": "A entrada precisa ser menor que o valor de venda.", valor_venda_centavos: "Informe o valor de venda para ligar a locação com compra." }, []);
    expect(e["compra.entrada_centavos"]).toBe("A entrada precisa ser menor que o valor de venda.");
    expect(e["valor_venda_centavos"]).toBe("Informe o valor de venda para ligar a locação com compra.");
  });
  it("vei_12_erro_do_agendamento_vai_para_a_linha", () => {
    expect(errosDaApi({ "planos.0.agendado.a_partir_de": "Escolha uma data a partir de amanhã." }, ["31"])["plano.31.agendado"]).toBe("Escolha uma data a partir de amanhã.");
  });
});

describe("custos mensais", () => {
  it("vei_13_custos_voltam_com_a_revenda_que_ja_estava", () => {
    const r = custosParaRascunho(PRECOS_POP.custos);
    expect(r.ipvaAno).toBe("R$ 1.200,00");
    expect(r.ocupacao).toBe("85,00%");
    const { custos, erros } = custosParaCorpo({ ...r, seguro: "R$ 90,00" }, PRECOS_POP.custos);
    expect(erros).toEqual({});
    expect(custos).toMatchObject({ seguro_mes_centavos: 9000, ipva_ano_centavos: 120000, ocupacao_esperada_pct: "85.00", revenda_estimada_centavos: 900000 });
  });
});

describe("textos e o último plano", () => {
  it("vei_12_ultimo_plano_ligado", () => {
    const compra = PRECOS_POP.plano_compra as NonNullable<typeof PRECOS_POP.plano_compra>;
    const so = { ...PRECOS_POP, plano_compra: { ...compra, ligado: false }, planos: PRECOS_POP.planos.map((p) => ({ ...p, ligado: p.id === 31 })) };
    expect(ehOUltimoLigado(so, "31")).toBe(true);
    expect(ehOUltimoLigado(so, "30")).toBe(false);
    expect(ehOUltimoLigado(PRECOS_POP, "31")).toBe(false);
    expect(ehOUltimoLigado({ ...so, plano_compra: { ...compra, ligado: true } }, "31")).toBe(false);
  });
  it("vei_12_rotulos", () => {
    expect(textoDasFormas(["boleto", "pix"])).toBe("Pix ou boleto");
    expect(textoDasFormas(["pix", "boleto", "cartao"])).toBe("Pix, boleto ou cartão");
    expect(textoDoPagamento("mes_quatro_semanais", { parcelas: 4, parcela_centavos: 24750, ultima_parcela_centavos: 24750 })).toBe("4 semanais de R$ 247,50");
    expect(textoDoPagamento("mes_uma_parcela")).toBe("1 parcela no mês");
    expect(textoDoAgendado({ valor_centavos: 28900, a_partir_de: "2026-12-01" })).toBe("R$ 289,00 a partir de 01 dez");
  });
});

import { describe, expect, it } from "vitest";
import { dataHoraCompleta, instanteDeLocal, localDeInstante } from "./formatos";
import type { PlanoDoVeiculo } from "@/lib/api";
import { PLANOS_DA_TABELA } from "@/testes/falsos/falso-precos-veiculo";
import { corpoDaLocacao, descontoValido, formasDoPlano, linhasDoPlano, periodicidadeDoPlano, retiradaPadrao, valoresIniciais, valorDoPlano, type ValoresLocacao } from "./locacao-form";

describe("datas do formulário (hora de Brasília)", () => {
  it("datetime-local vira instante UTC e volta", () => {
    expect(instanteDeLocal("2026-10-07T09:30")).toBe("2026-10-07T12:30:00.000Z");
    expect(localDeInstante("2026-10-07T12:30:00Z")).toBe("2026-10-07T09:30");
    expect(instanteDeLocal("")).toBeNull();
    expect(instanteDeLocal("07/10/2026")).toBeNull();
  });
  it("meia-noite não vira 24:00", () => {
    expect(localDeInstante("2026-10-07T03:00:00Z")).toBe("2026-10-07T00:00");
  });
  it("texto de formulário", () => {
    expect(dataHoraCompleta("2026-10-07T12:30:00Z")).toBe("07/10/2026 09:30");
  });
  it("a retirada padrão é a próxima meia hora", () => {
    expect(retiradaPadrao(new Date("2026-10-07T12:20:00Z"))).toBe("2026-10-07T09:30");
    expect(retiradaPadrao(new Date("2026-10-07T12:31:00Z"))).toBe("2026-10-07T10:00");
  });
});

describe("corpo da locação (LOC-01, ADR 0041: só o id do plano do veículo vai)", () => {
  const semanal = PLANOS_DA_TABELA.find((p) => p.tipo === "semanal") as PlanoDoVeiculo;
  const base: ValoresLocacao = { ...valoresIniciais(1206, 504, new Date("2026-10-07T12:20:00Z")), plano_veiculo_id: semanal.id };

  it("semanal com 1 período, sem desconto, sem periodicidade nem parcelamento", () => {
    expect(corpoDaLocacao(base, semanal)).toEqual({
      tipo: "comum",
      cliente_id: 1206,
      veiculo_id: 504,
      plano_veiculo_id: 7002,
      inicio: "2026-10-07T12:30:00.000Z",
      periodos: 1,
      fim_previsto: null,
      extras: [],
      desconto_pct: "0",
      forma_pagamento: "pix_automatico",
    });
  });

  it("vei_12_prazo_minimo_do_plano_e_o_periodo_de_partida", () => {
    expect(corpoDaLocacao(base, { id: 7004, prazo_minimo_periodos: 4 })?.periodos).toBe(4);
  });

  it("devolução informada troca os períodos pelo fim previsto; a API devolve os dois", () => {
    const c = corpoDaLocacao({ ...base, fim: "2026-10-14T09:30" }, semanal);
    expect(c?.periodos).toBeNull();
    expect(c?.fim_previsto).toBe("2026-10-14T12:30:00.000Z");
  });

  it("extras escolhidos e desconto com vírgula", () => {
    const c = corpoDaLocacao({ ...base, extras: [1, 3], desconto: "2,5" }, semanal);
    expect(c?.extras).toEqual([{ extra_id: 1, quantidade: 1 }, { extra_id: 3, quantidade: 1 }]);
    expect(c?.desconto_pct).toBe("2.5");
  });

  it("sem cliente, sem veículo, sem plano, sem data ou com desconto inválido não há o que simular", () => {
    expect(corpoDaLocacao({ ...base, cliente_id: null }, semanal)).toBeNull();
    expect(corpoDaLocacao({ ...base, veiculo_id: null }, semanal)).toBeNull();
    expect(corpoDaLocacao({ ...base, plano_veiculo_id: null })).toBeNull();
    expect(corpoDaLocacao({ ...base, inicio: "" }, semanal)).toBeNull();
    expect(corpoDaLocacao({ ...base, desconto: "abc" }, semanal)).toBeNull();
  });

  it("loc_16_compra_nao_manda_plano_nem_periodicidade", () => {
    const c = corpoDaLocacao({ ...base, tipo: "intencao_compra", plano_veiculo_id: null, desconto: "10", extras: [1] });
    expect(c).toEqual({ tipo: "intencao_compra", cliente_id: 1206, veiculo_id: 504, inicio: "2026-10-07T12:30:00.000Z", extras: [], desconto_pct: "0", forma_pagamento: "pix_automatico" });
  });

  it("desconto válido tem até 2 casas", () => {
    expect(["0", "5", "2,5", "10.25"].every(descontoValido)).toBe(true);
    expect(["", "-1", "1,234", "a"].some(descontoValido)).toBe(false);
  });
});

describe("o que o cartão do plano mostra (VEI-12)", () => {
  const por = (tipo: string) => PLANOS_DA_TABELA.find((p) => p.tipo === tipo) as PlanoDoVeiculo;

  it("valor e período vêm do plano", () => {
    expect(valorDoPlano(por("diaria"))).toBe("R$ 54,90 / dia");
    expect(valorDoPlano(por("semanal"))).toBe("R$ 329,00 / semana");
    expect(valorDoPlano(por("mensal"))).toBe("R$ 1.190,00 / mês");
  });

  it("linhas: como paga, caução, franquia e prazo mínimo", () => {
    expect(linhasDoPlano(por("semanal"))).toEqual(["Toda semana, adiantado", "Caução R$ 300,00 à vista", "Km livre"]);
    expect(linhasDoPlano(por("entregador"))).toEqual(["Toda semana, adiantado", "Caução R$ 300,00 à vista", "1.200 km por semana", "Mínimo de 4 semanas"]);
    expect(linhasDoPlano({ ...por("semanal"), caucao_parcelas: 2 })[1]).toBe("Caução R$ 300,00 em 2x");
  });

  it("o período do plano vira a periodicidade da locação", () => {
    expect(periodicidadeDoPlano("dia")).toBe("diaria");
    expect(periodicidadeDoPlano("semana")).toBe("semanal");
    expect(periodicidadeDoPlano("mes")).toBe("mensal");
  });

  it("formas de pagamento: só as que o plano aceita; Pix automático conta como Pix", () => {
    expect(formasDoPlano(por("entregador")).map((f) => f.valor)).toEqual(["pix_automatico", "pix", "boleto"]);
    expect(formasDoPlano(por("semanal")).map((f) => f.valor)).toEqual(["pix_automatico", "pix", "cartao", "boleto", "dinheiro"]);
  });
});

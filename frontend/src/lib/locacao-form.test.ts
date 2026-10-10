import { describe, expect, it } from "vitest";
import { dataHoraCompleta, instanteDeLocal, localDeInstante } from "./formatos";
import { corpoDaLocacao, descontoValido, opcoesDeParcelamento, retiradaPadrao, valoresIniciais, type ValoresLocacao } from "./locacao-form";

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

describe("corpo da locação", () => {
  const base: ValoresLocacao = { ...valoresIniciais(1206, 504, new Date("2026-10-07T12:20:00Z")) };

  it("semanal com 1 período, sem desconto", () => {
    expect(corpoDaLocacao(base, [])).toEqual({
      cliente_id: 1206,
      veiculo_id: 504,
      periodicidade: "semanal",
      plano_especial_id: null,
      inicio: "2026-10-07T12:30:00.000Z",
      periodos: 1,
      fim_previsto: null,
      extras: [],
      desconto_pct: "0",
      forma_pagamento: "pix_automatico",
      parcelamento_mensal: null,
    });
  });

  it("devolução informada troca os períodos pelo fim previsto; a API devolve os dois", () => {
    const c = corpoDaLocacao({ ...base, fim: "2026-10-14T09:30" }, []);
    expect(c?.periodos).toBeNull();
    expect(c?.fim_previsto).toBe("2026-10-14T12:30:00.000Z");
  });

  it("plano especial leva a periodicidade do plano; mensal leva o parcelamento", () => {
    const planos = [{ id: 1, periodicidade: "semanal" }, { id: 2, periodicidade: "mensal" }] as never;
    expect(corpoDaLocacao({ ...base, modalidade: "especial:1" }, planos)).toMatchObject({ periodicidade: "semanal", plano_especial_id: 1 });
    expect(corpoDaLocacao({ ...base, modalidade: "especial:2", parcelamento_mensal: "quatro_semanais" }, planos)).toMatchObject({ periodicidade: "mensal", plano_especial_id: 2, parcelamento_mensal: "quatro_semanais" });
    expect(corpoDaLocacao({ ...base, modalidade: "mensal" }, [])?.parcelamento_mensal).toBe("a_vista");
  });

  it("extras escolhidos e desconto com vírgula", () => {
    const c = corpoDaLocacao({ ...base, extras: [1, 3], desconto: "2,5" }, []);
    expect(c?.extras).toEqual([{ extra_id: 1, quantidade: 1 }, { extra_id: 3, quantidade: 1 }]);
    expect(c?.desconto_pct).toBe("2.5");
  });

  it("sem cliente, sem veículo, sem data ou com desconto inválido não há o que simular", () => {
    expect(corpoDaLocacao({ ...base, cliente_id: null }, [])).toBeNull();
    expect(corpoDaLocacao({ ...base, veiculo_id: null }, [])).toBeNull();
    expect(corpoDaLocacao({ ...base, inicio: "" }, [])).toBeNull();
    expect(corpoDaLocacao({ ...base, desconto: "abc" }, [])).toBeNull();
  });

  it("desconto válido tem até 2 casas", () => {
    expect(["0", "5", "2,5", "10.25"].every(descontoValido)).toBe(true);
    expect(["", "-1", "1,234", "a"].some(descontoValido)).toBe(false);
  });

  it("opções de parcelamento por modalidade", () => {
    expect(opcoesDeParcelamento("semanal").map((o) => o.rotulo)).toEqual(["Semanal · cobra a cada 7 dias"]);
    expect(opcoesDeParcelamento("mensal").map((o) => o.valor)).toEqual(["a_vista", "quatro_semanais"]);
  });
});

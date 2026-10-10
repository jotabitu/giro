import { describe, expect, it } from "vitest";
import { periodoDaLocacao, rotaDaAcaoLocacao, rotuloDaParcela, seloDaParcela, textoDaEstimativa, textoDoPeriodo, textoFaltam } from "./locacoes";

const sinais = { pagamento_atrasado: false, devolve_hoje: false, cancelamento_pendente: false };

describe("textoFaltam (só formata o que a API mandou)", () => {
  it("dias, horas e minutos, no singular e no plural", () => {
    expect(textoFaltam(10190)).toBe("faltam 7 dias");
    expect(textoFaltam(1500)).toBe("falta 1 dia");
    expect(textoFaltam(360)).toBe("faltam 6 horas");
    expect(textoFaltam(60)).toBe("falta 1 hora");
    expect(textoFaltam(20)).toBe("faltam 20 minutos");
    expect(textoFaltam(0)).toBe("no prazo da devolução");
  });
});

describe("periodoDaLocacao", () => {
  const agora = new Date("2026-10-07T15:30:00Z");
  it("mostra as duas datas curtas", () => {
    expect(periodoDaLocacao({ inicio: "2026-09-05T12:00:00Z", fim_previsto: "2026-09-12T12:00:00Z", sinais }, agora)).toBe("05 set → 12 set");
  });
  it("o dia de hoje vira 'hoje' e a hora da devolução aparece quando a API diz que devolve hoje", () => {
    expect(periodoDaLocacao({ inicio: "2026-10-07T12:30:00Z", fim_previsto: "2026-10-14T12:30:00Z", sinais }, agora)).toBe("hoje → 14 out");
    expect(periodoDaLocacao({ inicio: "2026-09-30T12:10:00Z", fim_previsto: "2026-10-07T21:00:00Z", sinais: { ...sinais, devolve_hoje: true } }, agora)).toBe("30 set → hoje 18:00");
  });
});

describe("parcelas", () => {
  it("selo de parcela paga leva a forma; caução paga mostra a observação", () => {
    expect(seloDaParcela({ tipo: "parcela", status: "paga", forma: "pix", observacao: null })).toEqual({ texto: "Pago · Pix", tom: "sucesso" });
    expect(seloDaParcela({ tipo: "caucao", status: "paga", forma: "pix", observacao: "Devolver na entrega" })).toEqual({ texto: "Devolver na entrega", tom: "info" });
    expect(seloDaParcela({ tipo: "parcela", status: "atrasada", forma: null, observacao: null })).toEqual({ texto: "Atrasada", tom: "critico" });
  });
  it("coluna Parcela", () => {
    expect(rotuloDaParcela({ tipo: "parcela", numero: 2 })).toBe("2");
    expect(rotuloDaParcela({ tipo: "caucao", numero: null })).toBe("Caução");
  });
});

describe("textos", () => {
  it("estimativa do encerramento (T-116)", () => {
    expect(textoDaEstimativa("2026-10-07")).toBe("Estimativa para 07 out. O valor final sai na devolução.");
  });
  it("período", () => {
    expect(textoDoPeriodo(2, "semanal")).toBe("2 semanas");
    expect(textoDoPeriodo(1, "mensal")).toBe("1 mês");
  });
  it("ação principal da linha", () => {
    expect(rotaDaAcaoLocacao({ id: 7, acao_principal: { codigo: "cobrar", rotulo: "Cobrar" } })).toBe("/financeiro/receber");
    expect(rotaDaAcaoLocacao({ id: 7, acao_principal: { codigo: "receber_devolucao", rotulo: "Receber devolução" } })).toBe("/locacoes/7/devolucao");
    expect(rotaDaAcaoLocacao({ id: 7, acao_principal: { codigo: "abrir", rotulo: "Abrir" } })).toBe("/locacoes/7");
  });
});

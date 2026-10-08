import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Kpi } from "@/lib/api";
import { KpisDoPainel } from "./comuns";

const KPIS: Kpi[] = [
  { chave: "ocupacao", rotulo: "Ocupação", valor: { tipo: "pct", valor: "71.00" }, contexto: "meta de 80%" },
  { chave: "receita_semana", rotulo: "Receita da semana", valor: { tipo: "centavos", valor: 1_840_000 }, contexto: "6% a mais que a anterior", tendencia: "sobe" },
  { chave: "em_manutencao", rotulo: "Em manutenção", valor: null, contexto: null },
];

describe("KpisDoPainel (USR-08)", () => {
  const html = renderToStaticMarkup(<KpisDoPainel kpis={KPIS} />);

  it("formata o valor tipado sem calcular nada", () => {
    expect(html).toContain("71%");
    expect(html).toContain("R$ 18,4 mil");
  });

  it("não mostra o cartão de módulo que ainda não existe", () => {
    expect(html).not.toContain("Em manutenção");
  });

  it("mostra o contexto que a API mandou", () => {
    expect(html).toContain("meta de 80%");
    expect(html).toContain("6% a mais que a anterior");
  });
});

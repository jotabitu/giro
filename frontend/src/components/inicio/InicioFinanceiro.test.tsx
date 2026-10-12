import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { InicioDe } from "@/lib/api";
import { InicioFinanceiro } from "./InicioFinanceiro";

const BASE: InicioDe<"financeiro"> = {
  variante: "financeiro",
  saudacao: "Bom dia, Marta",
  atualizado_em: "2026-10-07T12:00:00Z",
  kpis: [
    { chave: "entra_hoje", rotulo: "Entra hoje", valor: { tipo: "centavos", valor: 262_580 }, contexto: "6 parcelas" },
    { chave: "saldo_em_contas", rotulo: "Saldo em contas", valor: null, contexto: null },
  ],
  caixas_do_dia: null,
  para_hoje: [],
  fluxo_previsto: null,
  conciliacao: null,
};

describe("início do financeiro: blocos null não aparecem (USR-08)", () => {
  it("esconde o bloco Caixas do dia enquanto a API manda null e o cartão de KPI sem valor", () => {
    const html = renderToStaticMarkup(<InicioFinanceiro d={BASE} />);
    expect(html).not.toContain("Caixas do dia");
    expect(html).not.toContain("Saldo em contas");
    expect(html).toContain("R$ 2.625,80");
  });

  it("mostra Caixas do dia quando vem a lista", () => {
    const html = renderToStaticMarkup(<InicioFinanceiro d={{ ...BASE, caixas_do_dia: [{ filial: "Filial Centro", status: "aberto", aberto_por: "Bruna Alves", esperado_gaveta_centavos: 28_100 }] }} />);
    expect(html).toContain("Caixas do dia");
    expect(html).toContain("Aberto por Bruna Alves");
  });
});

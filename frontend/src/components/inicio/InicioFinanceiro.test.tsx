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

describe("início do financeiro (USR-08)", () => {
  it("esconde o cartão de KPI sem valor e mostra Caixas do dia vazio", () => {
    const html = renderToStaticMarkup(<InicioFinanceiro d={BASE} />);
    expect(html).toContain("Nenhum caixa aberto hoje.");
    expect(html).not.toContain("Saldo em contas");
    expect(html).toContain("R$ 2.625,80");
    expect(html).toContain("Quarta, 07 out · todas as filiais");
  });

  it("mostra Caixas do dia quando vem a lista", () => {
    const html = renderToStaticMarkup(<InicioFinanceiro d={{ ...BASE, caixas_do_dia: [{ filial: "Filial Centro", status: "aberto", aberto_por: "Bruna Alves", esperado_gaveta_centavos: 28_100 }] }} />);
    expect(html).toContain("Caixas do dia");
    expect(html).toContain("Aberto por Bruna Alves");
  });
});

describe("início sem blocos (campo null da API, USR-08)", () => {
  const nulos = (o: object) => o as never;
  it("financeiro: para_hoje e caixas_do_dia null mostram os vazios e mantêm entra hoje", () => {
    const html = renderToStaticMarkup(<InicioFinanceiro d={nulos({ ...BASE, para_hoje: null, caixas_do_dia: null })} />);
    expect(html).toContain("Nada para pagar ou devolver hoje.");
    expect(html).toContain("Nenhum caixa aberto hoje.");
    expect(html).toContain("R$ 2.625,80");
  });
});

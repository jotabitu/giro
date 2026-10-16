// Rotas das Movimentações no menu (T-289, MOV-02, USR-05): valem para quem tem o item `movimentacoes`, não para quem só tem Veículos.
import { describe, expect, it } from "vitest";
import { contas, type Eu } from "@/lib/api";
import { hrefDoDestino, montarMenu, rotaPermitida } from "./menu";

async function euDe(email: string): Promise<Eu> {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
  return r.usuario;
}

const comItem = (eu: Eu, tem: boolean): Eu => ({
  ...eu,
  navegacao: {
    ...eu.navegacao,
    menu_completo: [{ grupo: "Operação", itens: [{ chave: "veiculos", rotulo: "Veículos", contador: null }, ...(tem ? [{ chave: "movimentacoes", rotulo: "Movimentações", contador: null }] : [])] }],
  },
});

describe("rotas das Movimentações", () => {
  const rotas = ["/veiculos/movimentacoes", "/veiculos/movimentacoes/nova", "/veiculos/movimentacoes/2/chegada"];

  it("quem tem o item abre o quadro, a Nova movimentação e a chegada", async () => {
    const eu = comItem(await euDe("rodrigo@motorapida.com.br"), true);
    for (const rota of rotas) expect(rotaPermitida(eu, rota), rota).toBe(true);
  });

  it("quem tem só Veículos não abre nenhuma delas", async () => {
    const eu = comItem(await euDe("bruna@motorapida.com.br"), false);
    expect(rotaPermitida(eu, "/veiculos")).toBe(true);
    for (const rota of rotas) expect(rotaPermitida(eu, rota), rota).toBe(false);
  });

  it("o item do menu vira Movimentações com a rota do quadro", async () => {
    const eu = comItem(await euDe("rodrigo@motorapida.com.br"), true);
    const itens = montarMenu(eu.navegacao.menu_completo, "/veiculos/movimentacoes").flatMap((g) => g.itens);
    expect(itens.find((i) => i.chave === "movimentacoes")).toMatchObject({ rotulo: "Movimentações", href: "/veiculos/movimentacoes" });
    expect(hrefDoDestino("movimentacoes")).toBe("/veiculos/movimentacoes");
  });

  it("em /veiculos/movimentacoes só Movimentações fica ativo, e em /veiculos só Veículos", async () => {
    const eu = comItem(await euDe("rodrigo@motorapida.com.br"), true);
    const ativos = (rota: string) => montarMenu(eu.navegacao.menu_completo, rota).flatMap((g) => g.itens).filter((i) => i.ativo).map((i) => i.chave);
    expect(ativos("/veiculos/movimentacoes")).toEqual(["movimentacoes"]);
    expect(ativos("/veiculos/movimentacoes/2/chegada")).toEqual(["movimentacoes"]);
    expect(ativos("/veiculos")).toEqual(["veiculos"]);
    expect(ativos("/veiculos/12")).toEqual(["veiculos"]);
  });
});

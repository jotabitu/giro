import { describe, expect, it } from "vitest";
import { dependeDaFilial, escolhaValida, nomeDaEscolha, TODAS } from "./filial";

const CENTRO = { id: 1, nome: "Filial Centro", matriz: true, cidade: "Fortaleza", uf: "CE" };
const ALDEOTA = { id: 2, nome: "Filial Aldeota", matriz: false, cidade: "Fortaleza", uf: "CE" };
const admin = { pode_escolher_todas: true, resultados: [ALDEOTA, CENTRO] };
const gerente = { pode_escolher_todas: false, resultados: [ALDEOTA] };

describe("escolha da filial (USR-07)", () => {
  it("sem escolha guardada, usa a matriz e depois a primeira", () => {
    expect(escolhaValida(admin, null)).toBe("1");
    expect(escolhaValida(gerente, null)).toBe("2");
  });
  it("mantém a guardada quando ainda vale", () => {
    expect(escolhaValida(admin, "2")).toBe("2");
    expect(escolhaValida(admin, TODAS)).toBe(TODAS);
  });
  it("quem não pode escolher todas cai na própria filial", () => {
    expect(escolhaValida(gerente, TODAS)).toBe("2");
  });
  it("filial que saiu do escopo ou foi desativada é descartada", () => {
    expect(escolhaValida(gerente, "1")).toBe("2");
    expect(escolhaValida(admin, "9")).toBe("1");
  });
  it("pessoa sem filial fica sem escolha", () => {
    expect(escolhaValida({ pode_escolher_todas: false, resultados: [] }, "1")).toBeNull();
  });
  it("nome para o cabeçalho das telas", () => {
    expect(nomeDaEscolha(admin, TODAS)).toBe("Todas as filiais");
    expect(nomeDaEscolha(admin, "2")).toBe("Filial Aldeota");
    expect(nomeDaEscolha(admin, null)).toBeNull();
  });
  it("trocar de filial refaz tudo, menos a conta, a lista de filiais e a marca", () => {
    expect(dependeDaFilial(["contas-receber", {}])).toBe(true);
    expect(dependeDaFilial(["caixa", "hoje"])).toBe(true);
    expect(dependeDaFilial(["eu"])).toBe(false);
    expect(dependeDaFilial(["filiais-minhas"])).toBe(false);
    expect(dependeDaFilial(["marca"])).toBe(false);
  });
});

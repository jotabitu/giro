import { describe, expect, it } from "vitest";
import { dataCompleta, dataCurta, dinheiro, saudacao } from "./formatos";

describe("formatos", () => {
  it("dinheiro em centavos", () => {
    expect(dinheiro(125000)).toBe("R$ 1.250,00");
  });

  it("data curta de lista e completa de formulário", () => {
    expect(dataCurta("2026-10-06")).toBe("06 out");
    expect(dataCompleta("2026-10-06")).toBe("06/10/2026");
  });

  it("saudação pela hora de Brasília", () => {
    expect(saudacao(new Date("2026-10-07T12:00:00Z"))).toBe("Bom dia");
    expect(saudacao(new Date("2026-10-07T18:00:00Z"))).toBe("Boa tarde");
    expect(saudacao(new Date("2026-10-07T23:00:00Z"))).toBe("Boa noite");
  });
});

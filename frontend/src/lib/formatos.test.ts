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

import { celular, km, mascaraCnpj, mascaraCpf, mascaraCelular, mesAno, percentual, placa } from "./formatos";

describe("formatos de lista", () => {
  it("km, placa e mês", () => {
    expect(km(12430)).toBe("12.430 km");
    expect(placa("SAK1D39")).toBe("SAK-1D39");
    expect(mesAno("2026-03-04")).toBe("mar 2026");
    expect(percentual("86.00")).toBe("86%");
  });

  it("máscaras de documento e celular", () => {
    expect(mascaraCpf("12345678909")).toBe("123.456.789-09");
    expect(mascaraCnpj("11222333000181")).toBe("11.222.333/0001-81");
    expect(mascaraCelular("85988771203")).toBe("(85) 98877-1203");
    expect(celular("85988771203")).toBe("(85) 98877-1203");
  });
});

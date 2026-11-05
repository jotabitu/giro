import { describe, expect, it } from "vitest";
import { diaEMes, mascararCelular, mascararCnpj, reais, reaisInteiros } from "./compra";

describe("compra pública", () => {
  it("mascara o CNPJ enquanto a pessoa digita", () => {
    expect(mascararCnpj("12345678000195")).toBe("12.345.678/0001-95");
    expect(mascararCnpj("1234")).toBe("12.34");
    expect(mascararCnpj("12.345.678/0001-95999")).toBe("12.345.678/0001-95");
  });

  it("mascara o celular com DDD", () => {
    expect(mascararCelular("85998124410")).toBe("(85) 99812-4410");
    expect(mascararCelular("8532124410")).toBe("(85) 3212-4410");
    expect(mascararCelular("85")).toBe("(85");
  });

  it("mostra os valores que a API manda em centavos (Moto Rápida: R$ 449,00)", () => {
    expect(reaisInteiros(44900)).toBe("R$ 449");
    expect(reais(44900)).toBe("R$ 449,00");
    expect(reais(449000)).toBe("R$ 4.490,00");
  });

  it("escreve a data do teste como na tela", () => {
    expect(diaEMes("2026-10-22")).toBe("22 out");
  });
});

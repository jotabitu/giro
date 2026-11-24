// T-486 · VEI-18: o texto dos dias em estoque. A conta é da API; aqui só o plural e o "Hoje".
import { describe, expect, it } from "vitest";
import { diasEmEstoque } from "./frota";

describe("diasEmEstoque", () => {
  it("test_vei_18_textos_dos_dias", () => {
    expect(diasEmEstoque(53)).toBe("53 dias");
    expect(diasEmEstoque(1)).toBe("1 dia");
    expect(diasEmEstoque(0)).toBe("Hoje");
    expect(diasEmEstoque(null)).toBe("—");
    expect(diasEmEstoque(undefined)).toBe("—");
  });
});

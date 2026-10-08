import { describe, expect, it } from "vitest";
import { atualizadoHa, dinheiroCurto, formatarValor, horarioDaAgenda, percentual, rotuloDoPerfil, tomDoStatus } from "./painel";

describe("formatação do painel (a API calcula, a tela só formata)", () => {
  it("percentual com 2 casas da API", () => {
    expect(percentual("71.00")).toBe("71%");
    expect(percentual("66.67")).toBe("66,67%");
    expect(percentual("12.50")).toBe("12,5%");
  });

  it("dinheiro curto a partir de R$ 10 mil, inteiro abaixo", () => {
    expect(dinheiroCurto(1_840_000)).toBe("R$ 18,4 mil");
    expect(dinheiroCurto(2_000_000)).toBe("R$ 20 mil");
    expect(dinheiroCurto(164_640)).toBe("R$ 1.646,40");
    expect(dinheiroCurto(0)).toBe("R$ 0,00");
  });

  it("valor tipado por tipo", () => {
    expect(formatarValor({ tipo: "numero", valor: 86 })).toBe("86");
    expect(formatarValor({ tipo: "numero", valor: 12430 })).toBe("12.430");
    expect(formatarValor({ tipo: "centavos", valor: 189_000 })).toBe("R$ 1.890,00");
    expect(formatarValor({ tipo: "pct", valor: "71.00" })).toBe("71%");
  });

  it("tom da API vira tom do StatusBadge", () => {
    expect(tomDoStatus("perigo")).toBe("critico");
    expect(tomDoStatus("sucesso")).toBe("sucesso");
  });

  it("atualizado há N min", () => {
    const agora = new Date("2026-10-07T12:00:00Z");
    expect(atualizadoHa("2026-10-07T11:54:00Z", agora)).toBe("há 6 min");
    expect(atualizadoHa("2026-10-07T09:00:00Z", agora)).toBe("há 3 h");
    expect(atualizadoHa("2026-10-07T12:00:00Z", agora)).toBe("agora");
  });
});

describe("agenda e perfil", () => {
  it("horário de hoje só com a hora; de outro dia, com a data", () => {
    const agora = new Date("2026-10-07T12:00:00Z");
    expect(horarioDaAgenda("2026-10-07T12:30:00Z", agora)).toBe("09:30");
    expect(horarioDaAgenda("2026-10-06T21:00:00Z", agora)).toBe("06 out 18:00");
  });

  it("rótulo do perfil", () => {
    expect(rotuloDoPerfil("vistoriador")).toBe("Vistoriador");
  });
});

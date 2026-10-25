// T-359 · Tabelas de preço (LOC-01, LOC-02, LOC-15): só formata e converte o que a pessoa digita.
import { describe, expect, it } from "vitest";
import { avisoDePrecoGravado, contratos, precoDosTextos, precoIgual, reaisDoCentavos, textosDoPreco, valorDoPlano } from "./precos";

describe("lib/precos", () => {
  it("loc_01_reais_e_centavos: 5490 vira 54,90 e volta", () => {
    expect(reaisDoCentavos(5490)).toBe("54,90");
    expect(reaisDoCentavos(30000)).toBe("300,00");
    const t = textosDoPreco({ diaria_centavos: 5490, semanal_centavos: 32900, mensal_centavos: 119000, caucao_centavos: 30000 });
    expect(precoDosTextos(t)).toEqual({ preco: { diaria_centavos: 5490, semanal_centavos: 32900, mensal_centavos: 119000, caucao_centavos: 30000 } });
  });

  it("texto que não é valor volta erro no campo, sem chamar a API", () => {
    const r = precoDosTextos({ diaria_centavos: "abc", semanal_centavos: "329,00", mensal_centavos: "", caucao_centavos: "300" });
    expect(r).toHaveProperty("erros");
    if ("erros" in r) expect(Object.keys(r.erros).sort()).toEqual(["diaria_centavos", "mensal_centavos"]);
  });

  it("precoIgual compara os quatro valores", () => {
    const a = { diaria_centavos: 1, semanal_centavos: 2, mensal_centavos: 3, caucao_centavos: 4 };
    expect(precoIgual(a, { ...a })).toBe(true);
    expect(precoIgual(a, { ...a, caucao_centavos: 5 })).toBe(false);
  });

  it("loc_01_valor_do_plano: preço fixo por período e desconto, como a lista mostra", () => {
    expect(valorDoPlano({ regra: "preco_fixo", preco_centavos: 27900, desconto_pct: null, periodicidade: "semanal" })).toBe("R$ 279,00/sem");
    expect(valorDoPlano({ regra: "desconto", preco_centavos: null, desconto_pct: "10.00", periodicidade: "mensal" })).toBe("−10%");
  });

  it("contratos no singular e no plural", () => {
    expect(contratos(1)).toBe("1 contrato");
    expect(contratos(18)).toBe("18 contratos");
  });

  it("loc_15_aviso: usa o número que a API devolve", () => {
    expect(avisoDePrecoGravado(0)).toBe("Preço salvo. Vale para os contratos novos.");
    expect(avisoDePrecoGravado(1)).toContain("1 locação em andamento mantém");
    expect(avisoDePrecoGravado(12)).toContain("12 locações em andamento mantêm");
  });
});

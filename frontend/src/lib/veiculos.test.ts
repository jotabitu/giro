import { describe, expect, it } from "vitest";
import type { LeituraCrlv } from "@/lib/api";
import { centavosDoTexto, esquemaVeiculo, paraCorpoVeiculo, valoresDaLeitura, VALORES_INICIAIS_VEICULO } from "./veiculos";

describe("centavosDoTexto", () => {
  it.each([
    ["13.490,00", 1349000],
    ["R$ 13.490,00", 1349000],
    ["44,9", 4490],
    ["300", 30000],
  ])("%s", (texto, centavos) => expect(centavosDoTexto(texto)).toBe(centavos));

  it("texto que não é valor volta null", () => expect(centavosDoTexto("abc")).toBeNull());
});

describe("paraCorpoVeiculo (VEI-01)", () => {
  const v = { ...VALORES_INICIAIS_VEICULO, placa: "tbc-5h21", marca: " Honda ", modelo: "Pop 110i ES", ano_fabricacao: "2026", ano_modelo: "2026", chassi: "9c2jc7500tr012345", cor: "Preta", km_atual: "0", filial_id: "1", categoria_id: "1" };

  it("manda placa e chassi limpos e em maiúsculas, números como número", () => {
    expect(paraCorpoVeiculo(v)).toEqual({ placa: "TBC5H21", chassi: "9C2JC7500TR012345", marca: "Honda", modelo: "Pop 110i ES", ano_fabricacao: 2026, ano_modelo: 2026, cor: "Preta", km_atual: 0, categoria_id: 1, filial_id: 1 });
  });

  it("opcionais preenchidos entram; valor de compra vira centavos", () => {
    const c = paraCorpoVeiculo({ ...v, renavam: "013.987.654-32", valor_compra: "R$ 13.490,00", data_compra: "2026-10-08", capacidade_tanque_litros: "12,5" });
    expect(c).toMatchObject({ renavam: "01398765432", valor_compra_centavos: 1349000, data_compra: "2026-10-08", capacidade_tanque_litros: "12.5" });
  });
});

describe("esquemaVeiculo", () => {
  it("exige os campos obrigatórios e deixa o formato para a API", () => {
    const r = esquemaVeiculo.safeParse(VALORES_INICIAIS_VEICULO);
    expect(r.success).toBe(false);
    const campos = r.success ? [] : r.error.issues.map((i) => i.path[0]);
    expect(campos).toEqual(expect.arrayContaining(["placa", "marca", "modelo", "chassi", "cor", "filial_id", "categoria_id"]));
    expect(esquemaVeiculo.safeParse({ ...VALORES_INICIAIS_VEICULO, placa: "x", marca: "x", modelo: "x", ano_fabricacao: "1", ano_modelo: "1", chassi: "curto", cor: "x", filial_id: "1", categoria_id: "1" }).success).toBe(true);
  });

  it("valor de compra que não é valor é recusado no campo", () => {
    const r = esquemaVeiculo.safeParse({ ...VALORES_INICIAIS_VEICULO, valor_compra: "muito" });
    expect(!r.success && r.error.issues.some((i) => i.path[0] === "valor_compra")).toBe(true);
  });
});

describe("valoresDaLeitura (VEI-08)", () => {
  const leitura = (campos: Partial<LeituraCrlv["campos"]>, lidos: string[]): LeituraCrlv => ({
    documento: "crlv",
    campos: { placa: null, chassi: null, renavam: null, marca: null, modelo: null, ano_fabricacao: null, ano_modelo: null, cor: null, combustivel: null, ...campos },
    lidos,
    quantidade: lidos.length,
    rotulo: "CRLV-e lido",
    exercicio: 2026,
    dicas: { marca_modelo: null },
    leitura: "c",
  });

  it("copia só o que está em lidos, como texto, e deixa o resto da tela como está", () => {
    const r = valoresDaLeitura(leitura({ placa: "TBC5H21", ano_fabricacao: 2025, ano_modelo: 2026, cor: "vermelha", combustivel: "gasolina" }, ["placa", "ano_fabricacao", "ano_modelo", "cor", "combustivel"]));
    expect(r.valores).toEqual({ placa: "TBC5H21", ano_fabricacao: "2025", ano_modelo: "2026", cor: "vermelha" });
    expect(r.lidos).toEqual(["placa", "ano_fabricacao", "ano_modelo", "cor"]);
  });

  it("marca e modelo fora de lidos não entram, mesmo com texto", () => {
    const r = valoresDaLeitura(leitura({ placa: "TBC5H21", marca: "Honda", modelo: "Pop" }, ["placa"]));
    expect(r.valores).toEqual({ placa: "TBC5H21" });
  });
});

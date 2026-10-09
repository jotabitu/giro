// O falso de veículos tem que responder como docs/api/veiculos.md (T-095): VEI-01, VEI-02 e PLT-03.
import { beforeAll, describe, expect, it } from "vitest";
import { contas, ErroApi, type NovoVeiculo } from "@/lib/api";
import { definirLimiteDoPlanoFalso, veiculosFalso } from "./falso-frota";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

const NOVO: NovoVeiculo = {
  placa: "TBC5H21",
  chassi: "9C2JC7500TR012345",
  marca: "Honda",
  modelo: "Pop 110i ES",
  ano_fabricacao: 2026,
  ano_modelo: 2026,
  cor: "Preta",
  km_atual: 0,
  categoria_id: 1,
  filial_id: 1,
};

async function falha(p: Promise<unknown>): Promise<ErroApi> {
  try {
    await p;
  } catch (e) {
    if (e instanceof ErroApi) return e;
  }
  throw new Error("esperava um ErroApi");
}

describe("POST /api/veiculos/ no falso", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("test_vei_01_cria_disponivel_e_aparece_na_frota", async () => {
    const criado = await veiculosFalso.criar({ ...NOVO, placa: "tbc-5h21", valor_compra_centavos: 1349000 });
    expect(criado.placa).toBe("TBC5H21");
    expect(criado.status).toBe("disponivel");
    expect(criado.categoria.nome).toBe("Urbana 110");
    expect(criado.preco_vigente.diaria_centavos).toBe(3990);
    expect(criado.valor_compra_centavos).toBe(1349000);
    const lista = await veiculosFalso.listar({ busca: "TBC5H21" });
    expect(lista.resultados.map((x) => x.id)).toContain(criado.id);
    expect((await veiculosFalso.obter(criado.id)).km_atual).toBe(0);
  });

  it("test_vei_01_placa_unica_409_com_o_veiculo_existente", async () => {
    const e = await falha(veiculosFalso.criar({ ...NOVO, chassi: "9C2JC7500TR099999", placa: "SAK1D39" }));
    expect(e.status).toBe(409);
    expect(e.codigo).toBe("VEI-01");
    expect(e.detalhes).toEqual({ campo: "placa", veiculo_id: 504 });
  });

  it("test_vei_01_chassi_unico_409", async () => {
    const e = await falha(veiculosFalso.criar({ ...NOVO, placa: "ABC1D23", chassi: "9C2KC2210RR004417" }));
    expect(e.status).toBe(409);
    expect(e.detalhes).toMatchObject({ campo: "chassi", veiculo_id: 504 });
  });

  it("chassi com menos de 17 caracteres e placa fora do formato voltam 400 no campo", async () => {
    const e = await falha(veiculosFalso.criar({ ...NOVO, placa: "12", chassi: "ABC123" }));
    expect(e.status).toBe(400);
    expect(Object.keys(e.campos ?? {}).sort()).toEqual(["chassi", "placa"]);
  });

  it("categoria de outra filial e ano do modelo menor que o de fabricação voltam 400", async () => {
    const e = await falha(veiculosFalso.criar({ ...NOVO, placa: "ABC1D24", chassi: "9C2JC7500TR000001", categoria_id: 4, ano_modelo: 2025 }));
    expect(e.status).toBe(400);
    expect(e.campos).toMatchObject({ categoria_id: expect.any(String), ano_modelo: expect.any(String) });
  });

  it("test_plt_03_limite_do_plano_422", async () => {
    definirLimiteDoPlanoFalso(1);
    try {
      const e = await falha(veiculosFalso.criar({ ...NOVO, placa: "ABC1D25", chassi: "9C2JC7500TR000002" }));
      expect(e.status).toBe(422);
      expect(e.codigo).toBe("PLT-03");
    } finally {
      definirLimiteDoPlanoFalso(150);
    }
  });

  it("test_vei_02_km_nunca_diminui", async () => {
    const { id } = await veiculosFalso.criar({ ...NOVO, placa: "ABC1D26", chassi: "9C2JC7500TR000003", km_atual: 500 });
    const e = await falha(veiculosFalso.registrarKm(id, 400));
    expect(e.status).toBe(422);
    expect(e.codigo).toBe("VEI-01");
    expect(e.detalhes).toEqual({ km_atual: 500 });
    expect((await veiculosFalso.registrarKm(id, 650)).km_atual).toBe(650);
  });

  it("categorias respeitam a filial e o tipo", async () => {
    const centro = await veiculosFalso.categorias({ filial: 1, tipo_veiculo: "moto" });
    expect(centro.map((c) => c.nome)).not.toContain("Scooter");
    expect(centro.every((c) => c.tipo_veiculo === "moto")).toBe(true);
    expect((await veiculosFalso.categorias({ filial: 2 })).map((c) => c.nome)).toContain("Scooter");
  });

  it("só administrador e gerente cadastram: o vendedor recebe 403", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const e = await falha(veiculosFalso.criar({ ...NOVO, placa: "ABC1D27", chassi: "9C2JC7500TR000004" }));
    expect(e.status).toBe(403);
  });
});

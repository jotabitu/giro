// T-363 · Modelos de contrato na API real: rotas, métodos e corpos do contrato (docs/api/contratos.md).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { definirAccess } from "./http";
import { modelosContratoApi } from "./modelos-contrato";

let fetchMock: ReturnType<typeof vi.fn>;
const chamada = (n: number) => fetchMock.mock.calls[n] as [string, RequestInit];

beforeEach(() => {
  fetchMock = vi.fn(async () => new Response(JSON.stringify({ resultados: [], html: "<p>x</p>" }), { status: 200, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  definirAccess("a");
});
afterEach(() => vi.unstubAllGlobals());

describe("modelosContratoApi", () => {
  it("s_09_rotas: lista, marcadores, prontos e criação a partir do pronto", async () => {
    await modelosContratoApi.listar();
    await modelosContratoApi.marcadores();
    await modelosContratoApi.prontos();
    await modelosContratoApi.criar({ nome: "Semanal", finalidade: "locacao", a_partir_de: "locacao_semanal_moto" });
    expect(chamada(0)[0]).toBe("/api/contratos/modelos/");
    expect(chamada(1)[0]).toBe("/api/contratos/marcadores/");
    expect(chamada(2)[0]).toBe("/api/contratos/modelos-prontos/");
    expect([chamada(3)[0], chamada(3)[1].method]).toEqual(["/api/contratos/modelos/", "POST"]);
    expect(JSON.parse(chamada(3)[1].body as string)).toEqual({ nome: "Semanal", finalidade: "locacao", a_partir_de: "locacao_semanal_moto" });
  });

  it("loc_15_rotas: editar (PATCH), prévia, publicar e arquivar", async () => {
    await modelosContratoApi.alterar(10, { texto: "<p>oi</p>" });
    expect(await modelosContratoApi.previa(10)).toBe("<p>x</p>");
    await modelosContratoApi.previa(10, 2836);
    await modelosContratoApi.publicar(10);
    await modelosContratoApi.arquivar(10);
    expect([chamada(0)[0], chamada(0)[1].method]).toEqual(["/api/contratos/modelos/10/", "PATCH"]);
    expect([chamada(1)[0], chamada(1)[1].method, chamada(1)[1].body]).toEqual(["/api/contratos/modelos/10/previa/", "POST", "{}"]);
    expect(JSON.parse(chamada(2)[1].body as string)).toEqual({ locacao_id: 2836 });
    expect([chamada(3)[0], chamada(3)[1].method]).toEqual(["/api/contratos/modelos/10/publicar/", "POST"]);
    expect([chamada(4)[0], chamada(4)[1].method]).toEqual(["/api/contratos/modelos/10/arquivar/", "POST"]);
  });
});

// T-359 · Tabelas de preço na API real: rotas, métodos e filtros do contrato (docs/api/veiculos.md, docs/api/locacoes.md).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { definirAccess } from "./http";
import { precosApi } from "./precos";

let fetchMock: ReturnType<typeof vi.fn>;
const chamada = (n: number) => fetchMock.mock.calls[n] as [string, RequestInit];

beforeEach(() => {
  fetchMock = vi.fn(async () => new Response(JSON.stringify({ resultados: [] }), { status: 200, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  definirAccess("a");
});
afterEach(() => vi.unstubAllGlobals());

describe("precosApi", () => {
  it("loc_15_rotas: categorias com filtros, preço novo (POST) e preço agendado (PUT)", async () => {
    const corpo = { diaria_centavos: 1, semanal_centavos: 2, mensal_centavos: 3, caucao_centavos: 4, vigente_desde: "2026-11-01" };
    await precosApi.categorias({ filial: 2, ativo: true });
    await precosApi.definirPreco(5, corpo);
    await precosApi.trocarPrecoAgendado(5, "2026-11-01", corpo);
    await precosApi.planosEspeciais({ ativo: "todos" });
    await precosApi.historico();
    expect(chamada(0)[0]).toBe("/api/categorias/?filial=2&ativo=true");
    expect([chamada(1)[0], chamada(1)[1].method]).toEqual(["/api/categorias/5/precos/", "POST"]);
    expect(JSON.parse(chamada(1)[1].body as string)).toEqual(corpo);
    expect([chamada(2)[0], chamada(2)[1].method]).toEqual(["/api/categorias/5/precos/2026-11-01/", "PUT"]);
    expect(chamada(3)[0]).toBe("/api/planos-especiais/?ativo=todos");
    expect(chamada(4)[0]).toBe("/api/precos/historico/");
  });

  it("desativar e reativar usam POST nas rotas próprias", async () => {
    await precosApi.desativarCategoria(1);
    await precosApi.reativarCategoria(1);
    await precosApi.desativarExtra(2);
    await precosApi.desativarPlanoEspecial(3);
    expect(fetchMock.mock.calls.map((c) => [(c as [string, RequestInit])[0], (c as [string, RequestInit])[1].method])).toEqual([
      ["/api/categorias/1/desativar/", "POST"],
      ["/api/categorias/1/reativar/", "POST"],
      ["/api/extras/2/desativar/", "POST"],
      ["/api/planos-especiais/3/desativar/", "POST"],
    ]);
  });
});

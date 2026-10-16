// T-240 · Cadastrar veículo: o 201 basta. A leitura da ficha que vinha depois do POST virava "não foi possível cadastrar" quando falhava (500 no GET), com o veículo já gravado.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { definirAccess } from "./http";
import type { NovoVeiculo } from "./tipos-frota";
import { veiculosApi } from "./veiculos";

const NOVO: NovoVeiculo = { placa: "TST2B34", chassi: "9C2JC00001RRT0777", marca: "Honda", modelo: "Biz 125", ano_fabricacao: 2024, ano_modelo: 2024, cor: "preta", km_atual: 10, categoria_id: 1, filial_id: 1 };

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  definirAccess("abc");
});
afterEach(() => {
  vi.unstubAllGlobals();
  definirAccess(null);
});

describe("veiculosApi.criar (VEI-01, T-240)", () => {
  it("201 com a ficha dando 500 logo depois: o cadastro conclui e só o POST sai", async () => {
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) =>
      init?.method === "POST"
        ? new Response(JSON.stringify({ id: 90, placa: "TST2B34", marca: "Honda", modelo: "Biz 125" }), { status: 201, headers: { "content-type": "application/json" } })
        : new Response("InvalidOperation", { status: 500 }),
    );
    const criado = await veiculosApi.criar(NOVO);
    expect(criado).toMatchObject({ id: 90, placa: "TST2B34" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });
  });
});

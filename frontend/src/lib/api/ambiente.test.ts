import { afterEach, describe, expect, it, vi } from "vitest";
import { ambienteApi } from "./ambiente";

const resposta = (status: number, corpo: unknown) => vi.fn().mockResolvedValue(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }));

afterEach(() => vi.unstubAllGlobals());

describe("ambienteApi", () => {
  it("lê hoje e data_simulada da rota da empresa e da plataforma", async () => {
    const f = resposta(200, { hoje: "2026-10-07", data_simulada: true });
    vi.stubGlobal("fetch", f);
    expect(await ambienteApi.obter("empresa")).toEqual({ hoje: "2026-10-07", data_simulada: true });
    expect(f.mock.calls[0]![0]).toBe("/api/ambiente/");
    await ambienteApi.obter("plataforma");
    expect(f.mock.calls[1]![0]).toBe("/api/plataforma/ambiente/");
  });

  it("rota inexistente (404), erro de servidor ou corpo fora do contrato dão null, sem lançar", async () => {
    vi.stubGlobal("fetch", resposta(404, { codigo: "nao_encontrado", mensagem: "x" }));
    expect(await ambienteApi.obter("empresa")).toBeNull();
    vi.stubGlobal("fetch", resposta(500, {}));
    expect(await ambienteApi.obter("empresa")).toBeNull();
    vi.stubGlobal("fetch", resposta(200, { hoje: "amanhã" }));
    expect(await ambienteApi.obter("empresa")).toBeNull();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("rede")));
    expect(await ambienteApi.obter("empresa")).toBeNull();
  });
});

// T-370 · Rotas, métodos e corpos das ações novas na API real (docs/api/financeiro.md, docs/api/clientes.md).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clientesApi } from "./clientes";
import { financeiroApi } from "./financeiro";
import { definirAccess } from "./http";

let fetchMock: ReturnType<typeof vi.fn>;
let proxima: { status: number; corpo: unknown } = { status: 200, corpo: {} };
const chamada = (n: number) => fetchMock.mock.calls[n] as [string, RequestInit];

beforeEach(() => {
  proxima = { status: 200, corpo: {} };
  fetchMock = vi.fn(async () => new Response(JSON.stringify(proxima.corpo), { status: proxima.status, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  definirAccess("a");
});
afterEach(() => vi.unstubAllGlobals());

describe("financeiro", () => {
  it("fin_07_rotas: estornar movimento e renegociar", async () => {
    await financeiroApi.estornarMovimento(240, 503, "Lançado por engano");
    await financeiroApi.renegociar({ contas: [9010], novas: [{ vencimento: "2026-10-15", valor_centavos: 15000 }], motivo: "Prazo" });
    expect([chamada(0)[0], chamada(0)[1].method, chamada(0)[1].body]).toEqual(["/api/financeiro/caixas/240/movimentos/503/estornar/", "POST", JSON.stringify({ motivo: "Lançado por engano" })]);
    expect([chamada(1)[0], chamada(1)[1].method]).toEqual(["/api/financeiro/contas-receber/renegociar/", "POST"]);
    expect(JSON.parse(chamada(1)[1].body as string)).toEqual({ contas: [9010], novas: [{ vencimento: "2026-10-15", valor_centavos: 15000 }], motivo: "Prazo" });
  });
});

describe("clientes", () => {
  it("cli_05_rotas: bloquear, inativar e reativar mandam só o motivo", async () => {
    await clientesApi.bloquear(1201, "Documento suspeito");
    await clientesApi.inativar(1201, "Mudou");
    await clientesApi.reativar(1201, "Voltou");
    expect(fetchMock.mock.calls.map((c) => [(c as [string, RequestInit])[0], (c as [string, RequestInit])[1].method])).toEqual([
      ["/api/clientes/1201/bloquear/", "POST"],
      ["/api/clientes/1201/inativar/", "POST"],
      ["/api/clientes/1201/reativar/", "POST"],
    ]);
    expect(JSON.parse(chamada(0)[1].body as string)).toEqual({ motivo: "Documento suspeito" });
  });

  it("apr_05_desbloquear: 200 devolve o cliente e 202 devolve o pedido de aprovação", async () => {
    proxima = { status: 200, corpo: { id: 1203, status: "ativo" } };
    expect(await clientesApi.desbloquear(1203, "Quitou")).toMatchObject({ status: 200, cliente: { id: 1203 } });
    proxima = { status: 202, corpo: { pedido_aprovacao: { id: 88, tipo: "APR-05", status: "pendente" } } };
    expect(await clientesApi.desbloquear(1203, "Quitou")).toEqual({ status: 202, pedido: { id: 88, tipo: "APR-05", status: "pendente" } });
    expect(chamada(1)[0]).toBe("/api/clientes/1203/desbloquear/");
  });
});

// Cliente HTTP (T-126): JWT, renovação, erros 401/403/409/422 no formato da API e cursores das listas.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErroApi } from "./tipos";
import { accessAtual, aoPerderSessao, chamar, chamarComStatus, cursoresDaLista, definirAccess, definirFilial, http, renovarAccess } from "./http";
import { contasApi } from "./contas";
import { locacoesApi } from "./locacoes";

type Resposta = { status?: number; corpo?: unknown };
let fetchMock: ReturnType<typeof vi.fn>;

function responder(...respostas: Resposta[]) {
  for (const r of respostas) {
    fetchMock.mockImplementationOnce(async () => new Response(r.status === 204 || r.corpo === undefined ? null : JSON.stringify(r.corpo), { status: r.status ?? 200, headers: { "content-type": "application/json" } }));
  }
}
const chamada = (n: number) => fetchMock.mock.calls[n] as [string, RequestInit & { headers: Record<string, string> }];

beforeEach(() => {
  definirFilial(null);
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  definirAccess(null);
});
afterEach(() => vi.unstubAllGlobals());

async function falha(p: Promise<unknown>): Promise<ErroApi> {
  try {
    await p;
  } catch (e) {
    if (e instanceof ErroApi) return e;
  }
  throw new Error("esperava um ErroApi");
}

describe("chamadas autenticadas", () => {
  it("manda o access em Authorization e a query sem valores vazios", async () => {
    definirAccess("abc");
    responder({ corpo: { resultados: [] } });
    await http.get("/api/veiculos/", { status: "alugado", busca: "", tipo_veiculo: undefined });
    const [url, init] = chamada(0);
    expect(url).toBe("/api/veiculos/?status=alugado");
    expect(init.headers.Authorization).toBe("Bearer abc");
  });

  it("access vencido: renova uma vez e repete a chamada", async () => {
    definirAccess("velho");
    responder({ status: 401, corpo: { codigo: "nao_autenticado", mensagem: "x" } }, { corpo: { access: "novo" } }, { corpo: { id: 1 } });
    expect(await http.get("/api/auth/eu/")).toEqual({ id: 1 });
    expect(chamada(1)[0]).toBe("/api/auth/renovar/");
    expect(chamada(1)[1].headers["X-Requested-With"]).toBe("giro");
    expect(chamada(2)[1].headers.Authorization).toBe("Bearer novo");
  });

  it("várias chamadas vencidas juntas usam uma só renovação", async () => {
    definirAccess("velho");
    fetchMock.mockImplementation(async (url: string, init: { headers: Record<string, string> }) => {
      if (url === "/api/auth/renovar/") return new Response(JSON.stringify({ access: "novo" }), { status: 200 });
      if (init.headers.Authorization === "Bearer novo") return new Response(JSON.stringify({ ok: true }), { status: 200 });
      return new Response(JSON.stringify({ codigo: "nao_autenticado", mensagem: "x" }), { status: 401 });
    });
    await Promise.all([http.get("/api/a/"), http.get("/api/b/"), http.get("/api/c/")]);
    expect(fetchMock.mock.calls.filter((c) => c[0] === "/api/auth/renovar/")).toHaveLength(1);
  });

  it("renovação recusada: avisa que a sessão acabou e devolve o 401", async () => {
    definirAccess("velho");
    const aviso = vi.fn();
    const sair = aoPerderSessao(aviso);
    responder({ status: 401, corpo: { codigo: "nao_autenticado", mensagem: "x" } }, { status: 401, corpo: { codigo: "sessao_encerrada", mensagem: "Sessão encerrada" } });
    const erro = await falha(http.get("/api/auth/eu/"));
    sair();
    expect(erro.status).toBe(401);
    expect(aviso).toHaveBeenCalledOnce();
  });

  it("sessao_encerrada na chamada não tenta renovar", async () => {
    definirAccess("a");
    const aviso = vi.fn();
    const sair = aoPerderSessao(aviso);
    responder({ status: 401, corpo: { codigo: "sessao_encerrada", mensagem: "Sessão encerrada" } });
    await falha(http.get("/api/clientes/"));
    sair();
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(aviso).toHaveBeenCalledOnce();
  });
});

describe("erros no formato da API", () => {
  it("403 mantém código e mensagem", async () => {
    definirAccess("a");
    responder({ status: 403, corpo: { codigo: "permissao", mensagem: "Você não pode fazer isto" } });
    const e = await falha(http.post("/api/locacoes/1/cancelar/", {}));
    expect([e.status, e.codigo, e.message]).toEqual([403, "permissao", "Você não pode fazer isto"]);
  });

  it("409 e 422 trazem `detalhes`", async () => {
    definirAccess("a");
    responder({ status: 409, corpo: { codigo: "troca_pendente", mensagem: "m", detalhes: { troca_id: 4 } } }, { status: 422, corpo: { codigo: "vistoria_pendente", mensagem: "m", detalhes: { pendencias: [{ codigo: "km" }] } } });
    expect((await falha(http.post("/api/x/"))).detalhes).toEqual({ troca_id: 4 });
    expect((await falha(http.post("/api/y/"))).detalhes).toEqual({ pendencias: [{ codigo: "km" }] });
  });

  it("400 validacao: `campos` da API (lista de textos) vira texto por campo", async () => {
    definirAccess("a");
    responder({ status: 400, corpo: { codigo: "validacao", mensagem: "Confira os campos destacados", campos: { cnpj: ["CNPJ inválido", "outro"], endereco: { cep: ["CEP inválido"] } } } });
    const e = await falha(http.post("/api/clientes/", {}));
    expect(e.campos).toEqual({ cnpj: "CNPJ inválido", endereco: "CEP inválido" });
  });

  it("resposta que não é JSON (proxy fora do ar) vira mensagem genérica", async () => {
    definirAccess("a");
    fetchMock.mockResolvedValueOnce(new Response("<html>Bad Gateway</html>", { status: 502 }));
    const e = await falha(http.get("/api/x/"));
    expect([e.status, e.codigo]).toEqual([502, "erro_servidor"]);
    expect(e.message).toBe("Não foi possível concluir agora. Tente de novo.");
  });

  it("sem rede responde sem_conexao", async () => {
    definirAccess("a");
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    expect((await falha(http.get("/api/x/"))).codigo).toBe("sem_conexao");
  });
});

describe("formatos", () => {
  it("204 não tem corpo", async () => {
    definirAccess("a");
    responder({ status: 204 });
    expect(await chamar("DELETE", "/api/vistorias/1/avarias/2/")).toBeUndefined();
  });

  it("FormData vai como multipart, sem Content-Type fixo", async () => {
    definirAccess("a");
    responder({ status: 201, corpo: {} });
    const f = new FormData();
    f.set("posicao", "frente");
    await chamarComStatus("POST", "/api/vistorias/1/fotos/", { corpo: f });
    expect(chamada(0)[1].body).toBe(f);
    expect(chamada(0)[1].headers["Content-Type"]).toBeUndefined();
  });

  it("proximo e anterior viram o cursor puro", () => {
    const r = cursoresDaLista({ resultados: [], proximo: "http://motorapida.localhost:3000/api/veiculos/?cursor=cD0y&status=alugado", anterior: null }) as { proximo: string; anterior: null };
    expect(r.proximo).toBe("cD0y");
    expect(r.anterior).toBeNull();
  });
});

describe("contas", () => {
  it("entrar sem 2 etapas guarda o access em memória; as chamadas seguintes o usam", async () => {
    responder({ corpo: { etapa: "pronto", access: "tok", usuario: { id: 1 } } }, { corpo: { id: 1 } });
    const r = await contasApi.entrar({ email: "a@b.com", senha: "x", aparelho: "desktop" });
    expect(r.etapa).toBe("pronto");
    expect(chamada(0)[1].headers.Authorization).toBeUndefined();
    await contasApi.eu();
    expect(chamada(1)[1].headers.Authorization).toBe("Bearer tok");
  });

  it("2 etapas: o código vai com o token pré-2fa e o access só vale depois do `pronto`", async () => {
    responder({ corpo: { etapa: "verificar_2fa", token_pre_2fa: "pre" } }, { corpo: { etapa: "pronto", access: "final", usuario: {} } });
    await contasApi.entrar({ email: "a@b.com", senha: "x", aparelho: "celular" });
    expect(accessAtual()).toBeNull();
    await contasApi.verificar2fa("pre", { codigo: "123456" });
    expect(chamada(1)[1].headers.Authorization).toBe("Bearer pre");
    expect(JSON.parse(chamada(1)[1].body as string)).toEqual({ codigo: "123456" });
    expect(accessAtual()).toBe("final");
  });

  it("sair apaga o access mesmo se a API falhar", async () => {
    definirAccess("a");
    responder({ status: 500, corpo: {} });
    await falha(contasApi.sair());
    expect(chamada(0)[1].headers["X-Requested-With"]).toBe("giro");
    expect(accessAtual()).toBeNull();
  });

  it("renovar troca o cookie por um access novo", async () => {
    responder({ corpo: { access: "n" } });
    expect(await renovarAccess()).toBe("n");
    expect(accessAtual()).toBe("n");
  });
});

describe("locações", () => {
  it("cancelar com 202 devolve o pedido de aprovação", async () => {
    definirAccess("a");
    responder({ status: 202, corpo: { pedido_aprovacao: { id: 88, tipo: "APR-02", status: "pendente" } } });
    const r = await locacoesApi.cancelar(1, { motivo: "m", forma_devolucao: "pix" });
    expect(r).toEqual({ status: 202, pedido: { id: 88, tipo: "APR-02", status: "pendente" } });
  });

  it("cancelar com 200 devolve a locação", async () => {
    definirAccess("a");
    responder({ corpo: { id: 1, status: "cancelada" } });
    const r = await locacoesApi.cancelar(1, { motivo: "m", forma_devolucao: "pix" });
    expect(r.status).toBe(200);
  });

  it("listar manda os filtros e o cursor", async () => {
    definirAccess("a");
    responder({ corpo: { resultados: [], proximo: null, anterior: null } });
    await locacoesApi.listar({ aba: "abertas", busca: "lucas", cursor: "xyz" });
    expect(chamada(0)[0]).toBe("/api/locacoes/?aba=abertas&busca=lucas&cursor=xyz");
  });
});

describe("filial escolhida (USR-07, T-161)", () => {
  it("manda X-Filial com o id ou com \"todas\" em toda chamada da sessão", async () => {
    definirAccess("abc");
    definirFilial("2");
    responder({ corpo: { resultados: [] } }, { corpo: { resultados: [] } });
    await http.get("/api/financeiro/contas-receber/");
    definirFilial("todas");
    await http.post("/api/financeiro/caixas/", { troco_centavos: 20000 });
    expect(chamada(0)[1].headers["X-Filial"]).toBe("2");
    expect(chamada(1)[1].headers["X-Filial"]).toBe("todas");
  });

  it("sem escolha, sem cabeçalho; e as rotas de conta, seletor, login e renovação nunca levam", async () => {
    definirAccess("abc");
    responder({ corpo: {} });
    await http.get("/api/veiculos/");
    expect(chamada(0)[1].headers["X-Filial"]).toBeUndefined();

    definirFilial("1");
    responder({ corpo: { id: 1 } }, { corpo: { pode_escolher_todas: false, resultados: [] } }, { corpo: { etapa: "verificar_2fa" } }, { corpo: { access: "novo" } });
    await contasApi.eu();
    await chamar("GET", "/api/filiais/minhas/", { semFilial: true });
    await contasApi.entrar({ email: "a@b.c", senha: "x", aparelho: "desktop" });
    await renovarAccess();
    for (const n of [1, 2, 3, 4]) expect(chamada(n)[1].headers["X-Filial"], String(n)).toBeUndefined();
  });

  it("sessão perdida esquece a filial", async () => {
    definirAccess("abc");
    definirFilial("1");
    const sair = aoPerderSessao(() => {});
    responder({ status: 401, corpo: { codigo: "nao_autenticado", mensagem: "x" } }, { status: 401, corpo: { codigo: "token_invalido", mensagem: "x" } });
    await falha(http.get("/api/veiculos/"));
    sair();
    definirAccess("outro");
    responder({ corpo: {} });
    await http.get("/api/veiculos/");
    expect(chamada(2)[1].headers["X-Filial"]).toBeUndefined();
  });
});

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
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: "POST" });
  });
});

describe("veiculosApi.criar com o CRLV-e (VEI-08)", () => {
  it("vai em multipart com o arquivo, a validade, o exercício e o comprovante, e sem Content-Type fixo", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: 91 }), { status: 201, headers: { "content-type": "application/json" } }));
    const arquivo = new File(["%PDF-1.4"], "crlv.pdf", { type: "application/pdf" });
    await veiculosApi.criar({ ...NOVO, combustivel: "flex" }, { arquivo, validade: "2027-10-31", exercicio: 2026, leitura: "assinado" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/veiculos/");
    const corpo = init.body as FormData;
    expect(corpo).toBeInstanceOf(FormData);
    expect(corpo.get("placa")).toBe("TST2B34");
    expect(corpo.get("categoria_id")).toBe("1");
    expect(corpo.get("combustivel")).toBe("flex");
    expect((corpo.get("crlv_arquivo") as File).name).toBe("crlv.pdf");
    expect(corpo.get("crlv_validade")).toBe("2027-10-31");
    expect(corpo.get("crlv_exercicio")).toBe("2026");
    expect(corpo.get("leitura")).toBe("assinado");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
  });

  it("sem exercício, o campo não vai; sem CRLV, segue em JSON", async () => {
    fetchMock.mockImplementation(async () => new Response(JSON.stringify({ id: 92 }), { status: 201, headers: { "content-type": "application/json" } }));
    await veiculosApi.criar(NOVO, { arquivo: new File(["%PDF-"], "a.pdf"), validade: "2027-01-01", exercicio: null, leitura: "x" });
    expect((fetchMock.mock.calls[0]?.[1] as RequestInit).body as FormData).not.toSatisfy((f: FormData) => f.has("crlv_exercicio"));
    await veiculosApi.criar(NOVO);
    expect(typeof (fetchMock.mock.calls[1]?.[1] as RequestInit).body).toBe("string");
  });
});

describe("veiculosApi.lerCrlv e modelos (VEI-08, T-257)", () => {
  it("manda o PDF no campo arquivo e devolve a leitura como veio", async () => {
    const leitura = { documento: "crlv", lidos: ["placa"], quantidade: 1, rotulo: "CRLV-e lido · 1 campo preenchido", leitura: "c" };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(leitura), { status: 200, headers: { "content-type": "application/json" } }));
    const r = await veiculosApi.lerCrlv(new File(["%PDF-"], "crlv.pdf"));
    expect(r.rotulo).toBe("CRLV-e lido · 1 campo preenchido");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/veiculos/leitura-crlv/");
    expect(init.method).toBe("POST");
    expect(((init.body as FormData).get("arquivo") as File).name).toBe("crlv.pdf");
  });

  it.each([
    [422, { codigo: "VEI-08", mensagem: "Não conseguimos ler este documento. Preencha os campos à mão." }],
    [503, { codigo: "leitura_ocupada", mensagem: "Muitas leituras ao mesmo tempo. Tente de novo em instantes." }],
  ])("a recusa %s sobe com a mensagem da API", async (status, corpo) => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(corpo), { status, headers: { "content-type": "application/json" } }));
    await expect(veiculosApi.lerCrlv(new File(["x"], "a.pdf"))).rejects.toMatchObject({ status, codigo: corpo.codigo, message: corpo.mensagem });
  });

  it("o catálogo sai com tipo, marca e busca, e campo vazio fica fora da query", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ resultados: [{ marca: "Honda", modelo: "Pop 110i ES", tipo: "moto" }] }), { status: 200, headers: { "content-type": "application/json" } }));
    const r = await veiculosApi.modelos({ tipo: "moto", marca: "", busca: "pop" });
    expect(r).toEqual([{ marca: "Honda", modelo: "Pop 110i ES", tipo: "moto" }]);
    const url = new URL(fetchMock.mock.calls[0]?.[0] as string, "http://x");
    expect(url.pathname).toBe("/api/veiculos/modelos/");
    expect(url.searchParams.get("tipo")).toBe("moto");
    expect(url.searchParams.get("busca")).toBe("pop");
    expect(url.searchParams.has("marca")).toBe(false);
  });
});

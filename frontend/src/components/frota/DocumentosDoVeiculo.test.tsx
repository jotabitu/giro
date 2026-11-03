// T-413 · Documentos do veículo (VEI-03, AUD-05): substituir no editar e abrir na ficha.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, veiculos, type Eu } from "@/lib/api";
import { definirAccess } from "@/lib/api/http";
import { veiculosApi } from "@/lib/api/veiculos";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/501/editar", useSearchParams: () => new URLSearchParams() }));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { DocumentosDoVeiculo } from "./DocumentosDoVeiculo";
import { AbrirDocumento } from "./FichaVeiculo";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

describe("documentos do veículo, administrador e gerente", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("VEI-03: a seção do editar lista CRLV, IPVA, seguro e rastreador com Substituir e Abrir", async () => {
    const cliente = new QueryClient();
    cliente.setQueryData(["veiculo", 501, "documentos"], await veiculos.documentos(501));
    const h = renderToStaticMarkup(
      <QueryClientProvider client={cliente}>
        <DocumentosDoVeiculo id={501} />
      </QueryClientProvider>,
    );
    for (const t of ["CRLV", "IPVA", "Seguro", "Rastreador"]) expect(h).toContain(t);
    expect(h).toContain("Substituir");
    expect(h).toContain('type="file"');
    expect(h).toContain("Arquivo (PDF, JPG ou PNG, até 10 MB)");
    expect(h).toContain("Abrir CRLV");
    expect(h).toContain("Sem arquivo");
  });

  it("VEI-03: substituir deixa o anterior no histórico como inativo e o novo em uso", async () => {
    const arquivo = new File(["%PDF"], "apolice-nova.pdf", { type: "application/pdf" });
    const novo = await veiculos.enviarDocumento(502, { tipo: "seguro", validade: "2027-08-01", arquivo });
    expect(novo.arquivo?.nome).toBe("apolice-nova.pdf");
    const ativos = await veiculos.documentos(502);
    expect(ativos.filter((d) => d.tipo === "seguro")).toHaveLength(1);
    expect(ativos.find((d) => d.tipo === "seguro")?.validade).toBe("2027-08-01");
    const historico = await veiculos.historicoDeDocumentos(502);
    const seguros = historico.filter((d) => d.tipo === "seguro");
    expect(seguros.map((d) => d.ativo)).toContain(false);
    expect(seguros.map((d) => d.ativo)).toContain(true);
  });

  it("sem validade a API recusa e o erro vai para o campo", async () => {
    await expect(veiculos.enviarDocumento(502, { tipo: "ipva", validade: "" })).rejects.toMatchObject({ status: 400, campos: { validade: "Informe a validade" } });
  });

  it("AUD-05: a ficha abre o arquivo pela URL assinada numa aba nova; sem arquivo, diz isso", () => {
    const com = renderToStaticMarkup(<AbrirDocumento d={{ rotulo: "Seguro", arquivo: { nome: "apolice.pdf", url: "https://x/assinada?sig=1" } }} />);
    expect(com).toContain('href="https://x/assinada?sig=1"');
    expect(com).toContain('target="_blank"');
    expect(com).toContain('rel="noopener noreferrer"');
    expect(renderToStaticMarkup(<AbrirDocumento d={{ rotulo: "Rastreador", arquivo: null }} />)).toContain("Sem arquivo");
  });
});

describe("documentos do veículo, perfil sem edição", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));
  it("a API recusa o envio com 403", async () => {
    await expect(veiculos.enviarDocumento(501, { tipo: "seguro", validade: "2027-01-01" })).rejects.toMatchObject({ status: 403 });
  });
});

describe("documentos do veículo, rotas da API real", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    definirAccess("token");
    fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 9, tipo: "seguro", validade: "2027-01-01", situacao: "em_dia", dias_para_vencer: 200, resultados: [] }), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("POST em multipart com tipo, validade, exercício e arquivo", async () => {
    await veiculosApi.enviarDocumento(501, { tipo: "crlv", validade: "2027-01-01", exercicio: "2026", arquivo: new File(["x"], "crlv.pdf") });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/veiculos/501/documentos/");
    expect(init.method).toBe("POST");
    const f = init.body as FormData;
    expect([f.get("tipo"), f.get("validade"), f.get("exercicio")]).toEqual(["crlv", "2027-01-01", "2026"]);
    expect((f.get("arquivo") as File).name).toBe("crlv.pdf");
  });

  it("o histórico lê a rota própria", async () => {
    await veiculosApi.historicoDeDocumentos(501);
    expect((fetchMock.mock.calls[0] as [string])[0]).toBe("/api/veiculos/501/documentos/historico/");
  });
});

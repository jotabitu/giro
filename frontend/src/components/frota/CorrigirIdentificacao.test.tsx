// T-284 · Corrigir placa ou chassi (VEI-01): ação do administrador na edição do veículo, pela rota corrigir-identificacao.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, veiculos, type Eu } from "@/lib/api";
import { definirAccess } from "@/lib/api/http";
import { veiculosApi } from "@/lib/api/veiculos";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/501/editar", useSearchParams: () => new URLSearchParams() }));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { CorrigirIdentificacao } from "./CorrigirIdentificacao";
import { EditarVeiculo } from "./EditarVeiculo";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function edicao(id: number): Promise<string> {
  const ficha = await veiculos.obter(id);
  const cliente = new QueryClient();
  cliente.setQueryData(["veiculo", id], ficha);
  cliente.setQueryData(["categorias", { filial: String(ficha.filial.id), tipo: ficha.tipo_veiculo }], await veiculos.categorias({ filial: ficha.filial.id, tipo_veiculo: ficha.tipo_veiculo }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cliente}>
      <EditarVeiculo id={id} />
    </QueryClientProvider>,
  );
}

describe("ação Corrigir placa ou chassi na edição", () => {
  it("o administrador vê a ação; o gerente edita o veículo mas não vê a ação", async () => {
    await entrarComo("mariana@motorapida.com.br");
    const adm = texto(await edicao(501));
    expect(adm).toContain("Corrigir placa ou chassi");
    expect(adm).toContain("use Corrigir placa ou chassi");
    await entrarComo("rodrigo@motorapida.com.br");
    const ger = texto(await edicao(501));
    expect(ger).toContain("Salvar alterações");
    expect(ger).not.toContain("Corrigir placa ou chassi");
    expect(ger).toContain("fale com o administrador");
  });

  it("o diálogo pede placa, chassi e motivo, com os dados atuais", async () => {
    await entrarComo("mariana@motorapida.com.br");
    const ficha = await veiculos.obter(501);
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <CorrigirIdentificacao ficha={ficha} aoFechar={() => {}} aoConcluir={() => {}} />
      </QueryClientProvider>,
    );
    const t = texto(html);
    for (const trecho of ["Corrigir placa ou chassi", "Placa", "Chassi", "Motivo", "Obrigatório", "Cancelar", "Corrigir"]) expect(t, trecho).toContain(trecho);
    expect(html).toContain('value="QXA-4B21"');
    expect(html).toContain('value="9C2KC2210PR004401"');
  });
});

describe("POST /api/veiculos/{id}/corrigir-identificacao/ no falso", () => {
  beforeEach(() => entrarComo("mariana@motorapida.com.br"));

  it("corrige a placa e o chassi e devolve a ficha", async () => {
    const r = await veiculos.corrigirIdentificacao(504, { placa: "SAK-1D40", chassi: "9c2kc2210rr004499", motivo: "erro de digitação" });
    expect(r.placa).toBe("SAK1D40");
    expect(r.chassi).toBe("9C2KC2210RR004499");
  });

  it("erros da API voltam por campo: chassi com 17 caracteres e motivo obrigatório", async () => {
    await expect(veiculos.corrigirIdentificacao(504, { chassi: "123", motivo: "" })).rejects.toMatchObject({ status: 400, campos: { chassi: "O chassi tem 17 caracteres", motivo: expect.any(String) } });
  });

  it("placa e chassi são únicos: 409 VEI-01 diz o campo", async () => {
    await expect(veiculos.corrigirIdentificacao(504, { placa: "QXA4B21", motivo: "teste" })).rejects.toMatchObject({ status: 409, codigo: "VEI-01", detalhes: { campo: "placa" } });
    await expect(veiculos.corrigirIdentificacao(504, { chassi: "9C2KC2210PR004401", motivo: "teste" })).rejects.toMatchObject({ status: 409, codigo: "VEI-01", detalhes: { campo: "chassi" } });
  });

  it("gerente recebe 403", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    await expect(veiculos.corrigirIdentificacao(504, { placa: "SAK1D41", motivo: "teste" })).rejects.toMatchObject({ status: 403 });
  });
});

describe("cliente HTTP real", () => {
  it("manda POST na rota com placa, chassi e motivo", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 501 }), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    definirAccess("abc");
    try {
      await veiculosApi.corrigirIdentificacao(501, { placa: "QXA4B22", motivo: "erro de digitação" });
      const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
      expect(url).toBe("/api/veiculos/501/corrigir-identificacao/");
      expect(init.method).toBe("POST");
      expect(JSON.parse(String(init.body))).toEqual({ placa: "QXA4B22", motivo: "erro de digitação" });
    } finally {
      vi.unstubAllGlobals();
      definirAccess(null);
    }
  });
});

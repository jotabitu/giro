// Frota (D-25, USR-09): sem o preço na resposta, a coluna e o campo "Diária" não aparecem.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, veiculos, type Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos", useSearchParams: () => new URLSearchParams() }));

import { ListaVeiculos } from "./ListaVeiculos";

async function pagina(email: string): Promise<string> {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
  const cache = new QueryClient();
  cache.setQueryData(["veiculos", { status: "todos", tipo: "todos", busca: "", cursor: undefined }], await veiculos.listar({ status: "todos" }));
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaVeiculos />
    </QueryClientProvider>,
  );
  return html.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
}

describe("lista da frota por perfil", () => {
  it("gerente vê a coluna Diária", async () => {
    const t = await pagina("rodrigo@motorapida.com.br");
    expect(t).toContain("Diária");
    expect(t).toContain("R$ 54,90");
  });

  it("usr_09: vistoriador vê a frota sem Diária nem nenhum valor em reais", async () => {
    const t = await pagina("joao@motorapida.com.br");
    expect(t).toContain("QXA-4B21");
    expect(t).toContain("Quilometragem");
    expect(t).not.toContain("Diária");
    expect(t).not.toMatch(/R\$ \d/);
    expect(t).not.toContain("Cadastrar veículo");
  });

  it.each([["vendedor", "bruna@motorapida.com.br"], ["financeiro", "financeiro@motorapida.com.br"]])("usr_09: %s lê a frota com a Diária e sem o botão de cadastro", async (_perfil, email) => {
    const t = await pagina(email);
    expect(t).toContain("QXA-4B21");
    expect(t).toContain("Diária");
    expect(t).not.toContain("Cadastrar veículo");
  });
});

// T-486 · VEI-18, VEI-19: a coluna "Em estoque" com os dias da API, o parado em alerta e a ordem pela API.
describe("Em estoque na Frota", () => {
  async function comEstoque(email: string, comCampos: boolean): Promise<string> {
    const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") {
      const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
      if (v.etapa !== "pronto") throw new Error("esperava pronto");
    }
    sessao.eu = await contas.eu();
    const lista = await veiculos.listar({ status: "todos" });
    const [primeiro, segundo, ...resto] = lista.resultados;
    const resultados = comCampos
      ? [
          { ...primeiro!, status: "a_venda" as const, a_venda_desde: "2026-08-15", dias_em_estoque: 53, parado: true },
          { ...segundo!, status: "a_venda" as const, a_venda_desde: "2026-10-07", dias_em_estoque: 0, parado: false },
          ...resto.map((v) => ({ ...v, a_venda_desde: null, dias_em_estoque: null, parado: false })),
        ]
      : lista.resultados;
    const cache = new QueryClient();
    cache.setQueryData(["veiculos", { status: "todos", tipo: "todos", busca: "", cursor: undefined }], { ...lista, resultados });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <ListaVeiculos />
      </QueryClientProvider>,
    );
    return html;
  }

  it("test_vei_18_coluna_em_estoque_com_os_dias_e_o_parado", async () => {
    const h = await comEstoque("rodrigo@motorapida.com.br", true);
    const t = h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
    expect(t).toContain("Em estoque");
    expect(t).toContain("53 dias");
    expect(t).toContain("Hoje");
    expect(h).toMatch(/wl-badge--warning[^>]*>53 dias</);
    expect(h).toContain('aria-sort="none"');
    expect(h).toContain('aria-label="Ordenar por tempo em estoque"');
  });

  it("test_vei_18_vistoriador_sem_os_campos_nao_ve_a_coluna", async () => {
    const t = (await comEstoque("joao@motorapida.com.br", false)).replace(/<[^>]+>/g, "|");
    expect(t).not.toContain("Em estoque");
  });
});

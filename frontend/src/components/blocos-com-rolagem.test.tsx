// T-510: Pagamentos e Histórico da locação e Sessões abertas do usuário têm altura máxima e rolagem própria, em lista longa e curta.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, locacoes, usuarios, type Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes", useSearchParams: () => new URLSearchParams() }));

import { PainelDoUsuario } from "./admin/PainelDoUsuario";
import { DetalheDaLocacao } from "./locacoes/DetalheDaLocacao";

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

async function locacao(parcelas: number, eventos: number, id = 2836): Promise<{ desktop: string; celular: string }> {
  const l = await locacoes.obter(id);
  const h = await locacoes.historico(id);
  const base = l.parcelas?.[0];
  const cache = new QueryClient();
  cache.setQueryData(["locacao", id], { ...l, parcelas: base ? [...(l.parcelas ?? []), ...Array.from({ length: Math.max(0, parcelas - (l.parcelas?.length ?? 0)) }, (_, n) => ({ ...base, id: 900 + n, numero: 50 + n }))] : l.parcelas });
  const evento = h.resultados[0];
  cache.setQueryData(["locacao", id, "historico"], { ...h, resultados: evento ? Array.from({ length: eventos }, (_, n) => ({ ...evento, rotulo: `Evento ${n + 1}` })) : h.resultados });
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDaLocacao id={id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = html.match(/^<div class="hidden flex-col gap-6 md:flex">(.*)<\/div><div class="flex flex-col gap-4 md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop, celular };
}

const regiao = (h: string, rotulo: string) => h.match(new RegExp(`<div role="region" aria-label="${rotulo}" tabindex="0" class="wl-rolagem[^"]*">(.*?)</div></section>`, "s"))?.[1];

describe("T-510 · Pagamentos e Histórico da locação com rolagem", () => {
  it("lista longa: pagamentos e histórico ficam numa região rotulada, focável, com o cabeçalho da tabela dentro dela", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const { desktop, celular } = await locacao(14, 18);
    const pag = regiao(desktop, "Pagamentos da locação");
    expect(pag).toContain("<thead>");
    expect(pag?.match(/<tr>/g)).toHaveLength(15);
    const hist = regiao(desktop, "Histórico da locação");
    expect(hist?.match(/Evento \d+/g)).toHaveLength(18);
    expect(regiao(celular, "Histórico da locação")).toContain("Evento 18");
    // No celular, a lista de contas aparece enquanto a locação ainda tem o que receber (LOC-2856, Lucas).
    const lucas = await locacao(14, 3, 2856);
    expect(regiao(lucas.celular, "Pagamentos da locação")?.match(/<li /g)).toHaveLength(14);
  });

  it("título e ação do bloco ficam fora da região que rola", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const { desktop } = await locacao(14, 18);
    expect(desktop).toMatch(/<h2 class="wl-panel__title">Pagamentos<\/h2>.*?<div role="region" aria-label="Pagamentos da locação"/s);
    expect(regiao(desktop, "Pagamentos da locação")).not.toContain("wl-panel__title");
  });

  it("lista curta: a região existe e o teto é altura máxima, nunca altura fixa", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const { desktop } = await locacao(0, 2);
    expect(regiao(desktop, "Pagamentos da locação")?.match(/<tr>/g)).toHaveLength(4);
    const css = readFileSync(new URL("../design-system/componentes.css", import.meta.url), "utf8");
    const regra = css.match(/^\.wl-rolagem \{([^}]*)\}/m)?.[1] ?? "";
    expect(regra).toMatch(/max-height: 320px/);
    expect(regra).not.toMatch(/(^|[; ])height:/);
    expect(regra).toMatch(/overflow: auto/);
    expect(regra).toMatch(/overscroll-behavior: auto/);
    expect(css).toMatch(/\.wl-rolagem thead th \{[^}]*position: sticky; top: 0/);
    expect(css).toMatch(/\.wl-rolagem:focus-visible \{[^}]*outline: 2px solid var\(--focus\)/);
  });
});

describe("T-510 · Sessões abertas do usuário com rolagem", () => {
  async function painel(sessoes: number): Promise<string> {
    await entrar("mariana@motorapida.com.br");
    const base = (await usuarios.sessoes(2))[0] ?? { id: 1, tipo: "desktop", aparelho: "Chrome", ip: "177.10.0.1", criada_em: "2026-10-07T09:20:00Z", ultimo_uso: "2026-10-07T13:00:00Z", atual: false };
    const cache = new QueryClient();
    cache.setQueryData(["usuarios", "detalhe", 2], await usuarios.obter(2));
    cache.setQueryData(["usuarios", "sessoes", 2], Array.from({ length: sessoes }, (_, n) => ({ ...base, id: 100 + n, aparelho: `Aparelho ${n + 1}` })));
    return renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <PainelDoUsuario id={2} eu={sessao.eu as Eu} aoConcluir={() => {}} />
      </QueryClientProvider>,
    );
  }

  it("lista longa: as sessões ficam na região rotulada e o título fica fora", async () => {
    const h = await painel(9);
    const inicio = h.indexOf('<div role="region" aria-label="Sessões abertas" tabindex="0" class="wl-rolagem');
    expect(inicio).toBeGreaterThan(-1);
    const r = h.slice(inicio, h.indexOf("Redefinir 2 etapas"));
    expect(r.match(/Aparelho \d+/g)).toHaveLength(9);
    expect(r).not.toContain("<h3");
    expect(h.indexOf("<h3")).toBeLessThan(h.indexOf('aria-label="Sessões abertas"'));
  });

  it("sem sessão, não há região vazia", async () => {
    expect(await painel(0)).not.toContain('aria-label="Sessões abertas"');
  });
});

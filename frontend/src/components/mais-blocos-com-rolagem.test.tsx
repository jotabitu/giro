// T-512: mais blocos de lista com altura máxima e rolagem própria (ListaComRolagem, T-510), em lista longa e curta:
// ficha do cliente (Pagamentos, Parcelas atrasadas, Locações), detalhe do cliente (Locações) e início (Devoluções da semana).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { clientes, contas, financeiro, relatorios, type Eu, type LocacaoDoCliente } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/", useSearchParams: () => new URLSearchParams() }));

import { DetalheDoCliente } from "./clientes/DetalheDoCliente";
import { InicioGeral } from "./inicio/InicioGeral";

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

const LOCACAO_MOLDE: LocacaoDoCliente = {
  id: 1,
  codigo: "LOC-1001",
  status: "encerrada",
  veiculo: { id: 1, modelo: "Honda CG 160 Fan", placa: "RTA2C55", tipo: "moto" },
  periodicidade: "semanal",
  inicio: "2026-01-05",
  fim_previsto: "2026-02-05",
  situacao: { codigo: "encerrada", rotulo: "Encerrada", tom: "neutro" },
  pago_centavos: 62900,
  pagamento: { rotulo: "Pago", tom: "sucesso" },
  caucao: null,
};

/** Repete a primeira linha (ou a do molde, se a lista do seed vier vazia) até ter `n`, com id único. */
function ate<T extends { id: number }>(linhas: T[], n: number, molde: T[] = []): T[] {
  const base = linhas[0] ?? molde[0];
  if (!base) throw new Error(`seed vazio: ${JSON.stringify(linhas)} n=${n}`);
  return Array.from({ length: n }, (_, i) => ({ ...base, id: 9000 + i }));
}

const regiao = (h: string, rotulo: string) => h.match(new RegExp(`<div role="region" aria-label="${rotulo}" tabindex="0" class="wl-rolagem[^"]*">(.*?)</div></section>`, "s"))?.[1];
const linhasDe = (r: string | undefined) => r?.match(/<tr[ >]/g)?.length ?? 0;

async function ficha(id: number, n: number): Promise<string> {
  const [c, locs, atrasadas, pagas] = await Promise.all([
    clientes.obter(id),
    clientes.locacoes(id),
    financeiro.listarContas({ cliente: id, situacao: "atrasadas" }),
    financeiro.listarContas({ cliente: id, situacao: "pagas" }),
  ]);
  const cache = new QueryClient();
  cache.setQueryData(["cliente", id], c);
  cache.setQueryData(["cliente", id, "locacoes"], { ...locs, total: n, resultados: ate(locs.resultados, n, [LOCACAO_MOLDE]) });
  cache.setQueryData(["cliente", id, "contas", "atrasadas"], { ...atrasadas, resultados: ate(atrasadas.resultados, n) });
  cache.setQueryData(["cliente", id, "contas", "pagas"], { ...pagas, resultados: ate(pagas.resultados, n, atrasadas.resultados.map((a) => ({ ...a, pago_em: "2026-10-01", forma: "pix" }))) });
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDoCliente id={id} />
    </QueryClientProvider>,
  );
}

describe("T-512 · ficha do cliente (financeiro) com rolagem", () => {
  it("lista longa: Pagamentos, Parcelas atrasadas e Locações ficam em regiões rotuladas, com todas as linhas", async () => {
    await entrar("financeiro@motorapida.com.br");
    const h = await ficha(1203, 15);
    expect(regiao(h, "Parcelas atrasadas do cliente")?.match(/<li /g)).toHaveLength(15);
    expect(regiao(h, "Pagamentos do cliente")?.match(/<li /g)).toHaveLength(15);
    const locs = regiao(h, "Locações do cliente");
    expect(locs).toContain("<thead>");
    expect(linhasDe(locs)).toBe(16);
  });

  it("título do bloco fica fora da região que rola", async () => {
    await entrar("financeiro@motorapida.com.br");
    const h = await ficha(1203, 15);
    for (const [titulo, rotulo] of [["Parcelas atrasadas", "Parcelas atrasadas do cliente"], ["Pagamentos", "Pagamentos do cliente"], ["Locações", "Locações do cliente"]]) {
      expect(h).toMatch(new RegExp(`<h2 class="wl-panel__title">${titulo}</h2>.*?<div role="region" aria-label="${rotulo}"`, "s"));
      expect(regiao(h, rotulo as string)).not.toContain("wl-panel__title");
    }
  });

  it("lista curta: uma linha em cada região, sem espaço vazio (teto é altura máxima)", async () => {
    await entrar("financeiro@motorapida.com.br");
    const h = await ficha(1203, 1);
    expect(regiao(h, "Parcelas atrasadas do cliente")?.match(/<li /g)).toHaveLength(1);
    expect(regiao(h, "Pagamentos do cliente")?.match(/<li /g)).toHaveLength(1);
    expect(linhasDe(regiao(h, "Locações do cliente"))).toBe(2);
  });

  it("sem dado, a região não aparece: continua o texto de vazio", async () => {
    await entrar("financeiro@motorapida.com.br");
    const h = await ficha(1203, 0);
    expect(h).not.toContain('aria-label="Pagamentos do cliente"');
    expect(h).toContain("Nenhum pagamento ainda.");
  });
});

describe("T-512 · detalhe do cliente (administrador) com rolagem em Locações", () => {
  async function detalhe(n: number) {
    await entrar("rodrigo@motorapida.com.br");
    const id = 1203;
    const [c, locs] = await Promise.all([clientes.obter(id), clientes.locacoes(id)]);
    const cache = new QueryClient();
    cache.setQueryData(["cliente", id], c);
    cache.setQueryData(["cliente", id, "locacoes"], { ...locs, total: n, resultados: ate(locs.resultados, n, [LOCACAO_MOLDE]) });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <DetalheDoCliente id={id} />
      </QueryClientProvider>,
    );
    const [, desktop = "", celular = ""] = html.match(/^<div class="hidden md:block">(.*)<\/div><div class="md:hidden">(.*)<\/div>$/s) ?? [];
    return { desktop, celular };
  }

  it("lista longa: desktop (tabela com cabeçalho) e celular (cartão) rolam dentro da região", async () => {
    const { desktop, celular } = await detalhe(14);
    expect(linhasDe(regiao(desktop, "Locações do cliente"))).toBe(15);
    expect(regiao(desktop, "Locações do cliente")).toContain("<thead>");
    const cartao = celular.match(/<div role="region" aria-label="Locações do cliente" tabindex="0" class="wl-rolagem[^"]*">(.*?)<\/dl><\/div>/s)?.[1];
    expect(cartao?.match(/<dt/g)).toHaveLength(14);
  });

  it("lista curta: a região existe com uma linha só", async () => {
    const { desktop } = await detalhe(1);
    expect(linhasDe(regiao(desktop, "Locações do cliente"))).toBe(2);
  });
});

describe("T-512 · início: Devoluções da semana com rolagem", () => {
  async function inicio(n: number): Promise<string> {
    await entrar("mariana@motorapida.com.br");
    const d = (await relatorios.inicio("7d")) as unknown as { devolucoes_semana: { linhas: { codigo: string }[] } };
    const base = d.devolucoes_semana.linhas[0];
    const linhas = base ? Array.from({ length: n }, (_, i) => ({ ...base, codigo: `LOC-${7000 + i}` })) : [];
    const geral = { ...d, devolucoes_semana: { ...d.devolucoes_semana, linhas } } as never;
    return renderToStaticMarkup(<InicioGeral d={geral} periodo="7d" aoMudarPeriodo={() => {}} />);
  }

  it("lista longa: a tabela fica na região e o título e o subtítulo ficam fora", async () => {
    const h = await inicio(14);
    const r = regiao(h, "Devoluções da semana");
    expect(r).toContain("<thead>");
    expect(linhasDe(r)).toBe(15);
    expect(h).toMatch(/<h2 class="wl-panel__title">Devoluções da semana<\/h2>.*?<div role="region" aria-label="Devoluções da semana"/s);
    expect(r).not.toContain("wl-panel__title");
  });

  it("lista curta: a região existe com poucas linhas", async () => {
    expect(linhasDe(regiao(await inicio(2), "Devoluções da semana"))).toBe(3);
  });
});

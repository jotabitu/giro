// T-511: o "Próxima" de Contas a receber leva o cursor à URL, a lista lê o cursor da URL e o manda à API.
// T-513: o número da página vai à URL junto com o cursor e aparece entre "Anterior" e "Próxima".
// Sem DOM nos testes (environment node): o clique é o onClick do botão "Próxima" do Paginacao real.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, financeiro, type Eu, type FiltroReceber, type ListaContasReceber } from "@/lib/api";
import { reiniciarFinanceiroFalso } from "@/testes/falsos/falso-financeiro";

const url = vi.hoisted(() => ({ params: new URLSearchParams(), replace: null as null | ((destino: string) => void) }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push() {}, replace: (destino: string) => url.replace?.(destino) }),
  usePathname: () => "/financeiro/receber",
  useSearchParams: () => url.params,
}));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));

type PropsPaginacao = { anterior: string | null; proximo: string | null; pagina: number; aoIr: (cursor: string | null, pagina: number) => void; texto: string; extra?: ReactNode };
const capturado = vi.hoisted(() => ({ paginacao: null as null | PropsPaginacao, chips: null as null | { aoMudar: (v: string) => void } }));
vi.mock("@/components/lista/Paginacao", async (original) => {
  const real = await original<typeof import("@/components/lista/Paginacao")>();
  return {
    Paginacao: (p: PropsPaginacao) => {
      capturado.paginacao = p;
      return real.Paginacao(p);
    },
  };
});
vi.mock("@/components/lista/FiltroChips", async (original) => {
  const real = await original<typeof import("@/components/lista/FiltroChips")>();
  return {
    FiltroChips: (p: Parameters<typeof real.FiltroChips>[0]) => {
      capturado.chips = p;
      return real.FiltroChips(p);
    },
  };
});

import { Paginacao } from "@/components/lista/Paginacao";
import { ListaReceber } from "./ListaReceber";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

/** Acha no elemento devolvido pelo Paginacao o botão com o rótulo e chama o onClick dele. */
function clicar(no: ReactNode, rotulo: string): boolean {
  if (Array.isArray(no)) return no.some((n) => clicar(n, rotulo));
  if (!isValidElement(no)) return false;
  const props = (no as ReactElement<{ children?: ReactNode; onClick?: () => void; disabled?: boolean }>).props;
  if (props.children === rotulo && props.onClick) {
    expect(props.disabled, `${rotulo} desabilitado`).toBe(false);
    props.onClick();
    return true;
  }
  return clicar(props.children, rotulo);
}

function clicarNaPaginacao(rotulo: "Próxima" | "Anterior") {
  const p = capturado.paginacao;
  if (!p) throw new Error("a lista não mostrou a paginação");
  expect(clicar(Paginacao(p), rotulo)).toBe(true);
}

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

/** Renderiza a lista com a URL atual, roda a consulta que a própria tela montou e devolve a página já com os dados. */
async function telaComDados(cache: QueryClient): Promise<string> {
  const tela = () =>
    renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <ListaReceber />
      </QueryClientProvider>,
    );
  tela();
  const cursor = url.params.get("cursor") ?? undefined;
  const [consulta] = cache.getQueryCache().findAll({ queryKey: ["contas-receber"], predicate: (q) => (q.queryKey[1] as { cursor?: string }).cursor === cursor });
  if (!consulta) throw new Error("a tela não montou a consulta");
  await consulta.fetch();
  return texto(tela());
}

let chamadas: FiltroReceber[];
let pagina1: ListaContasReceber;
let pagina2: ListaContasReceber;

beforeEach(async () => {
  reiniciarFinanceiroFalso();
  url.params = new URLSearchParams();
  url.replace = vi.fn((destino: string) => {
    url.params = new URLSearchParams(destino.split("?")[1] ?? "");
  });
  capturado.paginacao = null;
  capturado.chips = null;
  await entrar("rodrigo@motorapida.com.br");
  // Carlos e Rafael, as duas atrasadas do seed, uma em cada página.
  const base = await financeiro.listarContas({ periodo: "mes", situacao: "atrasadas" });
  expect(base.resultados.length).toBe(2);
  pagina1 = { ...base, resultados: [base.resultados[0]!], proximo: "cD0y", anterior: null };
  pagina2 = { ...base, resultados: [base.resultados[1]!], proximo: null, anterior: "0" };
  chamadas = [];
  vi.spyOn(financeiro, "listarContas").mockImplementation(async (f: FiltroReceber = {}) => {
    chamadas.push(f);
    return f.cursor ? pagina2 : pagina1;
  });
});
afterEach(() => vi.restoreAllMocks());

describe("paginação de Contas a receber (T-511)", () => {
  it("Próxima grava o cursor na URL, a API recebe o cursor e a lista muda", async () => {
    const cache = new QueryClient();
    const nome1 = pagina1.resultados[0]!.cliente.nome;
    const nome2 = pagina2.resultados[0]!.cliente.nome;

    const primeira = await telaComDados(cache);
    expect(chamadas.at(-1)?.cursor).toBeUndefined();
    expect(primeira).toContain(nome1);
    expect(primeira).not.toContain(nome2);
    expect(primeira).toContain("|Anterior|Página |1|Próxima|");

    clicarNaPaginacao("Próxima");
    expect(url.replace).toHaveBeenLastCalledWith("/financeiro/receber?cursor=cD0y&pagina=2");

    const segunda = await telaComDados(cache);
    expect(chamadas.at(-1)).toMatchObject({ periodo: "mes", situacao: "atrasadas", cursor: "cD0y" });
    expect(segunda).toContain(nome2);
    expect(segunda).not.toContain(nome1);
    expect(segunda).toContain("|Anterior|Página |2|Próxima|");

    // Anterior com "0" é a primeira página: o cursor sai da URL.
    clicarNaPaginacao("Anterior");
    expect(url.replace).toHaveBeenLastCalledWith("/financeiro/receber");
  });

  it("trocar a aba na página 2 volta para a primeira página e o número sai da URL", async () => {
    url.params = new URLSearchParams({ cursor: "cD0y", pagina: "2" });
    expect(await telaComDados(new QueryClient())).toContain("|Anterior|Página |2|Próxima|");
    expect(chamadas.at(-1)?.cursor).toBe("cD0y");
    capturado.chips?.aoMudar("pagas");
    expect(url.replace).toHaveBeenLastCalledWith("/financeiro/receber?aba=pagas");
  });
});

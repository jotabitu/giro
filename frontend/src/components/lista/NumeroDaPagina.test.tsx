// T-513: número da página entre "Anterior" e "Próxima", acompanhado na URL junto com o cursor.
// A API pagina só por cursor e não devolve o número: a tela soma 1 no Próxima e tira 1 no Anterior.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { clientes, contas, filiais, type Eu } from "@/lib/api";
import { useFiltrosNaUrl } from "@/lib/filtros-url";
import { paginaDoCursor } from "@/lib/paginacao";

const url = vi.hoisted(() => ({ params: new URLSearchParams(), replace: null as null | ((destino: string) => void) }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push() {}, replace: (destino: string) => url.replace?.(destino) }),
  usePathname: () => "/clientes",
  useSearchParams: () => url.params,
}));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { Paginacao } from "./Paginacao";
import { ListaClientes } from "@/components/clientes/ListaClientes";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

/** Acha o botão com o rótulo no elemento devolvido pelo Paginacao e chama o onClick dele. */
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

describe("Paginacao com o número da página (T-513)", () => {
  it("mostra o número entre os botões, com aria-current e rótulo acessível", () => {
    const html = renderToStaticMarkup(<Paginacao texto="Mostrando 20" anterior="cD0x" proximo="cD0y" pagina={2} aoIr={() => {}} />);
    expect(texto(html)).toContain("|Mostrando 20|Anterior|2|Próxima|");
    expect(html).toContain('<span aria-current="page" aria-label="Página 2"');
    expect(html).not.toMatch(/ de \d/);
  });

  it("Próxima soma 1 e Anterior tira 1, levando o cursor da API", () => {
    const aoIr = vi.fn();
    const el = Paginacao({ texto: "", anterior: "cD0x", proximo: "cD0z", pagina: 3, aoIr });
    clicar(el, "Próxima");
    expect(aoIr).toHaveBeenLastCalledWith("cD0z", 4);
    clicar(el, "Anterior");
    expect(aoIr).toHaveBeenLastCalledWith("cD0x", 2);
  });

  it("Anterior com o cursor \"0\" volta à primeira página", () => {
    const aoIr = vi.fn();
    clicar(Paginacao({ texto: "", anterior: "0", proximo: null, pagina: 2, aoIr }), "Anterior");
    expect(aoIr).toHaveBeenLastCalledWith(null, 1);
  });

  it("sem cursor a página é 1, mesmo com pagina na URL", () => {
    expect(paginaDoCursor(null, "4")).toBe(1);
    expect(paginaDoCursor(undefined, null)).toBe(1);
    expect(paginaDoCursor("cD0y", "3")).toBe(3);
    expect(paginaDoCursor("cD0y", null)).toBe(1);
    expect(paginaDoCursor("cD0y", "abc")).toBe(1);
    expect(paginaDoCursor("cD0y", "0")).toBe(1);
  });
});

describe("número da página na lista de Clientes (T-513)", () => {
  async function tela(): Promise<string> {
    const cache = new QueryClient();
    cache.setQueryData(["filiais", "minhas"], await filiais.minhas());
    const cursor = url.params.get("cursor") ?? undefined;
    const base = await clientes.listar({});
    // Página do meio: a API devolve os dois cursores.
    cache.setQueryData(["clientes", { filial: "", situacao: url.params.get("situacao") ?? "todos", ordem: "-criado_em", busca: "", cursor }], { ...base, proximo: "cD00MA", anterior: cursor ? "cD0yMA" : null });
    return texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <ListaClientes />
        </QueryClientProvider>,
      ),
    );
  }

  beforeEach(async () => {
    url.params = new URLSearchParams();
    url.replace = vi.fn((destino: string) => {
      url.params = new URLSearchParams(destino.split("?")[1] ?? "");
    });
    const r = await contas.entrar({ email: "mariana@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    sessao.eu = await contas.eu();
  });

  it("abre na página 1 sem cursor e mostra a página da URL quando há cursor", async () => {
    expect(await tela()).toContain("|Anterior|1|Próxima|");
    url.params = new URLSearchParams({ cursor: "cD00MA", pagina: "3" });
    expect(await tela()).toContain("|Anterior|3|Próxima|");
  });

  it("Próxima e Anterior levam cursor e número à URL; filtro e busca voltam a 1", () => {
    let hook: ReturnType<typeof useFiltrosNaUrl> | null = null;
    const Sonda = () => {
      hook = useFiltrosNaUrl();
      return null;
    };
    const ler = () => {
      renderToStaticMarkup(<Sonda />);
      if (!hook) throw new Error("sem hook");
      return hook as ReturnType<typeof useFiltrosNaUrl>;
    };
    url.params = new URLSearchParams({ situacao: "em_aberto" });
    let h = ler();
    clicar(Paginacao({ texto: "", anterior: null, proximo: "cD0yMA", ...h.paginacao }), "Próxima");
    expect(url.replace).toHaveBeenLastCalledWith("/clientes?situacao=em_aberto&cursor=cD0yMA&pagina=2");
    h = ler();
    expect(h.paginacao.pagina).toBe(2);
    clicar(Paginacao({ texto: "", anterior: "0", proximo: "cD00MA", ...h.paginacao }), "Próxima");
    expect(url.replace).toHaveBeenLastCalledWith("/clientes?situacao=em_aberto&cursor=cD00MA&pagina=3");
    h = ler();
    clicar(Paginacao({ texto: "", anterior: "cD0yMA", proximo: null, ...h.paginacao }), "Anterior");
    expect(url.replace).toHaveBeenLastCalledWith("/clientes?situacao=em_aberto&cursor=cD0yMA&pagina=2");
    h = ler();
    h.definir({ situacao: "bloqueados" });
    expect(url.replace).toHaveBeenLastCalledWith("/clientes?situacao=bloqueados");
    expect(ler().paginacao.pagina).toBe(1);
    url.params = new URLSearchParams({ cursor: "cD0yMA", pagina: "2" });
    ler().definir({ busca: "Juliana" });
    expect(url.replace).toHaveBeenLastCalledWith("/clientes?busca=Juliana");
  });

  it("URL com pagina e sem cursor dá 1", async () => {
    url.params = new URLSearchParams({ pagina: "5" });
    expect(await tela()).toContain("|Anterior|1|Próxima|");
  });
});

// Filtro de filial da lista de Clientes (T-251, CLI-10, CA-248-01, 02, 06 e 07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { clientes, contas, filiais, type Eu } from "@/lib/api";

const url = vi.hoisted(() => ({ filial: null as string | null }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push() {}, replace() {} }),
  usePathname: () => "/clientes",
  useSearchParams: () => new URLSearchParams(url.filial ? { filial: url.filial } : {}),
}));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { ListaClientes } from "./ListaClientes";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

async function pagina(filial: string | null): Promise<string> {
  url.filial = filial;
  const cache = new QueryClient();
  cache.setQueryData(["filiais", "minhas"], await filiais.minhas());
  cache.setQueryData(["clientes", { filial: filial ?? "", situacao: "todos", ordem: "-criado_em", busca: "", cursor: undefined }], await clientes.listar({ filial: filial ? Number(filial) : undefined }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaClientes />
    </QueryClientProvider>,
  );
}

describe("filtro de filial em Clientes (CLI-10)", () => {
  it("começa em Todas as filiais e oferece as filiais da pessoa, sem seguir o seletor do topo", async () => {
    await entrarComo("mariana@motorapida.com.br");
    const html = await pagina(null);
    expect(html).toContain("Filial</label>");
    expect(html).toContain('<option value="" selected="">Todas as filiais</option>');
    expect(html).toContain("Filial Centro");
    expect(html).toContain("Juliana Rocha");
  });

  it("com a filial na URL a opção fica marcada e a lista é a da filial", async () => {
    await entrarComo("mariana@motorapida.com.br");
    expect(await pagina("1")).toMatch(/<option value="1" selected="">Filial Centro<\/option>/);
    expect((await clientes.listar({ filial: 1 })).resultados.length).toBeGreaterThan(0);
    expect((await clientes.listar({ filial: 2 })).resultados).toHaveLength(0);
  });
});

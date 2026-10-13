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
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
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
});

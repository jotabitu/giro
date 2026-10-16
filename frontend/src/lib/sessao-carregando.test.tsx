// T-322: enquanto o `eu` carrega, a casca mostra só o carregamento. Nem a guarda de rota nem as telas que leem `pode.*` renderizam.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace() {} }), usePathname: () => "/veiculos/movimentacoes" }));
vi.mock("@/lib/endereco", () => ({ useEnderecoSemEmpresa: () => false }));
vi.mock("@/lib/marca-empresa", () => ({ useMarcaDaEmpresa: () => ({}) }));

import { GuardaDeRota } from "@/components/casca/CascaDoApp";
import { SessaoProvider } from "./sessao";

const arvore = (cliente: QueryClient) =>
  renderToStaticMarkup(
    <QueryClientProvider client={cliente}>
      <SessaoProvider>
        <GuardaDeRota>
          <p>conteúdo da tela</p>
        </GuardaDeRota>
      </SessaoProvider>
    </QueryClientProvider>,
  );

describe("sessão carregando (T-322)", () => {
  it("sem o eu, mostra Carregando e nunca o aviso de falta de acesso", () => {
    const h = arvore(new QueryClient());
    expect(h).toContain("Carregando");
    expect(h).toContain('aria-busy="true"');
    expect(h).not.toContain("Seu perfil não tem acesso");
    expect(h).not.toContain("conteúdo da tela");
  });

  it("com o eu e a rota fora do menu, mostra o aviso de verdade", () => {
    const cliente = new QueryClient();
    const eu = { pode: { movimentacoes: "nao" }, navegacao: { inicio: { rota: "/inicio" }, menu_inicio: [], menu_completo: [] } } as unknown as Eu;
    cliente.setQueryData(["eu"], eu);
    const h = arvore(cliente);
    expect(h).toContain("Seu perfil não tem acesso");
    expect(h).not.toContain("Carregando");
  });
});

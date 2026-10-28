// Página de entrada do suporte (T-372): docs/api/contas.md, "Página de entrada e faixa no frontend" (PLT-07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

const estado = vi.hoisted(() => ({ link: { pronto: true, token: null as string | null }, saiu: null as string | null }));
vi.mock("@/lib/fragmento", () => ({ useTokenDoFragmento: () => estado.link }));
vi.mock("@/lib/sessao", () => ({ useGuardarSessao: () => () => {} }));
vi.mock("./CabecalhoMarca", () => ({ CabecalhoMarca: () => null, RodapeGiro: () => null }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: () => {} }),
  useSearchParams: () => new URLSearchParams(estado.saiu ? `saiu=${estado.saiu}` : ""),
}));

import { EntradaDoSuporte } from "./EntradaDoSuporte";

function pagina(): string {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>
      <EntradaDoSuporte />
    </QueryClientProvider>,
  );
}

describe("Entrada do suporte", () => {
  it("sem fragmento: 'O acesso de suporte terminou' e nenhum botão ou campo de login", () => {
    estado.link = { pronto: true, token: null };
    estado.saiu = null;
    const h = pagina();
    expect(h).toContain("O acesso de suporte terminou");
    expect(h).not.toContain("<button");
    expect(h).not.toContain("<input");
    expect(h).not.toContain('href="/entrar"');
  });

  it("com ?saiu=1: 'Você saiu do modo suporte'", () => {
    estado.link = { pronto: true, token: null };
    estado.saiu = "1";
    expect(pagina()).toContain("Você saiu do modo suporte");
  });

  it("com token no fragmento, mostra 'Entrando no modo suporte…' enquanto confere", () => {
    estado.link = { pronto: true, token: "suporte-valido" };
    estado.saiu = null;
    const h = pagina();
    expect(h).toContain("Entrando no modo suporte…");
    expect(h).not.toContain("suporte-valido");
  });

  it("antes de ler o fragmento no navegador, não decide nada", () => {
    estado.link = { pronto: false, token: null };
    estado.saiu = null;
    expect(pagina()).toContain("Entrando no modo suporte…");
  });
});

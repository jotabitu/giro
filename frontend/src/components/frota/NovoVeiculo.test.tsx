import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ veiculos: "editar" as string }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {}, replace: () => {} }), usePathname: () => "/veiculos", useSearchParams: () => new URLSearchParams() }));
vi.mock("@/lib/sessao", () => ({
  useSessao: () => ({ eu: { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { veiculos: sessao.veiculos } } as unknown as Eu, sair: async () => {} }),
}));

import { ListaVeiculos } from "./ListaVeiculos";
import { NovoVeiculoForm } from "./NovoVeiculoForm";

const html = (el: React.ReactElement) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);

describe("botão Cadastrar veículo na Frota", () => {
  it("aparece uma vez só, como botão preto com texto, para quem pode editar veículos", () => {
    sessao.veiculos = "editar";
    const h = html(<ListaVeiculos />);
    expect(h).toContain('href="/veiculos/novo"');
    expect(h).toContain("Cadastrar veículo");
    expect(h.match(/href="\/veiculos\/novo"/g)).toHaveLength(1);
    expect(h).toContain("wl-btn wl-btn--solid");
    expect(h).not.toContain("wl-icon-btn");
    expect(h).not.toContain('aria-label="Cadastrar veículo"');
  });

  it("não aparece para quem só vê ou só registra km", () => {
    for (const p of ["nao", "km_e_avarias"]) {
      sessao.veiculos = p;
      expect(html(<ListaVeiculos />)).not.toContain("/veiculos/novo");
    }
  });
});

describe("tela Cadastrar veículo", () => {
  it("mostra os campos do contrato e as filiais da pessoa", () => {
    sessao.veiculos = "editar";
    const h = html(<NovoVeiculoForm />);
    for (const t of ["Placa", "Marca", "Modelo", "Chassi", "Renavam", "Km atual", "Categoria de preço", "Salvar veículo", "Salvar e cadastrar outro"]) expect(h).toContain(t);
    expect(h).toContain("Nunca diminui depois de salvo");
    expect(h).toContain(">Filial Centro</option>");
  });

  it("o que o contrato não tem fica desativado", () => {
    sessao.veiculos = "editar";
    const h = html(<NovoVeiculoForm />);
    expect(h).toMatch(/<button[^>]*disabled[^>]*>Enviar CRLV-e/);
    expect(h).toContain("A consulta FIPE ainda não está disponível");
  });

  it("perfil sem permissão não vê o formulário", () => {
    sessao.veiculos = "nao";
    const h = html(<NovoVeiculoForm />);
    expect(h).toContain("Seu perfil não cadastra veículos");
    expect(h).not.toContain("Chassi");
  });
});

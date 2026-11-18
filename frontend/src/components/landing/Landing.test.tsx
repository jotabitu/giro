import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { CatalogoDaCompra } from "@/lib/api/tipos-compra";

vi.mock("@/lib/api/compra", () => ({ compraApi: { planos: () => new Promise(() => {}) } }));

import { Landing } from "./Landing";
import { CartoesDaLanding } from "./Planos";
import { QuemUsa } from "./QuemUsa";

const html = renderToStaticMarkup(
  <QueryClientProvider client={new QueryClient()}>
    <Landing />
  </QueryClientProvider>,
);

// Catálogo da API pública de planos (PLT-11, fase 1: só Essencial e Profissional à venda).
const CATALOGO: CatalogoDaCompra = {
  planos: [
    { codigo: "essencial", nome: "Essencial", descricao: "Para quem está começando a frota.", mensal_centavos: 13000, anual_centavos: 130000, limites: { veiculos: 30, filiais: 1, usuarios: 3 }, inclui: ["Locação, vistoria e contas a receber"], destaque: false },
    { codigo: "profissional", nome: "Profissional", descricao: "Para locadoras com equipe e mais de uma loja.", mensal_centavos: 16000, anual_centavos: 160000, limites: { veiculos: 150, filiais: 3, usuarios: 10 }, inclui: ["Tudo do Essencial, mais despesas", "Pix e boleto automáticos"], destaque: true },
  ],
  teste: { dias: 14, inicio: "2026-10-07", fim: "2026-10-21", lembrete: "2026-10-19", primeira_fatura: "2026-10-22" },
};

describe("landing pública (T-489, T-490)", () => {
  it("tem as 9 seções na ordem, sem Quem usa", () => {
    const marcos = ['class="nav dark"', 'id="topo"', 'id="problema"', 'id="como-funciona"', 'id="modulos"', 'id="white-label"', 'id="planos"', 'id="perguntas"', 'class="dark close"'];
    const posicoes = marcos.map((m) => html.indexOf(m));
    expect(posicoes.every((p) => p >= 0)).toBe(true);
    expect([...posicoes].sort((a, b) => a - b)).toEqual(posicoes);
    expect(html).not.toContain('id="clientes"');
    expect(html).not.toContain('href="#clientes"');
    expect(html).not.toContain("A preencher");
  });

  it("copia os textos principais como estão e não escreve preço de plano", () => {
    for (const texto of ["Sua locadora de motos e carros fora do caderno.", "7 contratos precisam de ação hoje", "Feche o caderno. Abra o Giro.", "12.430 km", "Carregando os planos..."]) {
      expect(html).toContain(texto);
    }
    for (const fixo of ["R$ 199", "R$ 449", "R$ 899", "Mais vendido"]) expect(html).not.toContain(fixo);
    expect(html).not.toMatch(/!/);
  });

  it("planos, preços e benefícios vêm do catálogo da API, com o selo da /compra (PLT-11)", () => {
    const cartoes = renderToStaticMarkup(<CartoesDaLanding catalogo={CATALOGO} />);
    for (const t of ["Essencial", "R$ 130", "Profissional", "R$ 160", "Mais escolhido", "Até 150 veículos", "Pix e boleto automáticos"]) {
      expect(cartoes, t).toContain(t);
    }
    expect(cartoes).not.toContain("Completo");
    // T-490: o botão de cada plano vai direto à criação da conta com ele.
    expect(cartoes).toContain('href="/compra?plano=essencial"');
    expect(cartoes).toContain('href="/compra?plano=profissional"');
  });

  it("usa o logo oficial por SVG e nada de fonte externa", () => {
    expect(html).toContain('src="/marca/giro-motos-horizontal.svg"');
    expect(html).not.toContain("fonts.googleapis.com");
  });

  it("botões gerais descem para a seção Planos, não abrem a /compra, e o WhatsApp fica sem número (T-490)", () => {
    const gerais = html.match(/<a class="wl-btn wl-btn--brand[^"]*" href="([^"]+)">Começar teste grátis/g) ?? [];
    expect(gerais).toHaveLength(3);
    for (const a of gerais) expect(a).toContain('href="#planos"');
    expect(html).not.toContain('href="/compra"');
    expect(html).toMatch(/<h2 class="h2" id="planos-titulo" tabindex="-1">/);
    expect(html).toContain('href="https://wa.me/"');
  });

  it("perguntas com details; Quem usa continua no código, sem depoimento inventado", () => {
    expect(html.match(/<details>/g)).toHaveLength(6);
    expect(renderToStaticMarkup(<QuemUsa />)).toContain("A preencher");
  });
});

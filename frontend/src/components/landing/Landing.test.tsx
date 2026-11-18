import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Landing } from "./Landing";

const html = renderToStaticMarkup(<Landing />);

describe("landing pública (T-489)", () => {
  it("tem as 10 seções na ordem da especificação", () => {
    const marcos = ['class="nav dark"', 'id="topo"', 'id="problema"', 'id="como-funciona"', 'id="modulos"', 'id="white-label"', 'id="clientes"', 'id="planos"', 'id="perguntas"', 'class="dark close"'];
    const posicoes = marcos.map((m) => html.indexOf(m));
    expect(posicoes.every((p) => p >= 0)).toBe(true);
    expect([...posicoes].sort((a, b) => a - b)).toEqual(posicoes);
  });

  it("copia os textos principais como estão", () => {
    for (const texto of ["Sua locadora de motos e carros fora do caderno.", "7 contratos precisam de ação hoje", "Feche o caderno. Abra o Giro.", "R$ 199", "R$ 449", "R$ 899", "Mais vendido", "12.430 km"]) {
      expect(html).toContain(texto);
    }
    expect(html).not.toMatch(/!/);
  });

  it("usa o logo oficial por SVG e nada de fonte externa", () => {
    expect(html).toContain('src="/marca/giro-motos-horizontal.svg"');
    expect(html).not.toContain("fonts.googleapis.com");
  });

  it("aponta o teste grátis para a compra pública e deixa o WhatsApp sem número", () => {
    expect(html).toContain('href="/compra"');
    expect(html).toContain('href="https://wa.me/"');
  });

  it("perguntas com details e Quem usa sem depoimento inventado", () => {
    expect(html.match(/<details>/g)).toHaveLength(6);
    expect(html).toContain("A preencher");
  });
});

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BarraDeAcoes } from "./BarraDeAcoes";

describe("BarraDeAcoes (T-514)", () => {
  it("fica fixa ao rolar, acima da barra de navegação no celular, com Cancelar quieto em link e o principal sólido", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes cancelar={{ href: "/veiculos" }} principal={{ rotulo: "Cadastrar veículo" }} />);
    expect(html).toContain("sticky bottom-[88px]");
    expect(html).toContain("md:bottom-4");
    expect(html).toContain("shadow-pop");
    expect(html).toMatch(/<a [^>]*href="\/veiculos"[^>]*class="wl-btn wl-btn--quiet"[^>]*>Cancelar<\/a>|<a [^>]*class="wl-btn wl-btn--quiet"[^>]*href="\/veiculos"[^>]*>Cancelar<\/a>/);
    expect(html).toMatch(/<button type="submit" class="wl-btn wl-btn--solid">Cadastrar veículo<\/button>/);
  });

  it("no estado ocupado troca o texto por Salvando… e desabilita", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes cancelar={{ href: "/x" }} principal={{ rotulo: "Salvar alterações", ocupado: true }} />);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Salvando…<\/button>/);
    expect(html).not.toContain("Salvar alterações");
    const outro = renderToStaticMarkup(<BarraDeAcoes cancelar={{ href: "/x" }} principal={{ rotulo: "Salvar", ocupado: true, textoOcupado: "Lançando…" }} />);
    expect(outro).toContain("Lançando…");
  });

  it("com form=id liga o botão ao form que está fora da barra", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes cancelar={{ href: "/x" }} principal={{ rotulo: "Salvar", form: "meu-form" }} />);
    expect(html).toMatch(/<button type="submit" form="meu-form"/);
  });

  it("Cancelar em botão (desfazer) pode ficar inativo; o principal com aoClicar vira botão comum", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes cancelar={{ aoClicar: () => {}, disabled: true }} principal={{ rotulo: "Salvar", aoClicar: () => {}, disabled: true }} />);
    expect(html).toMatch(/<button type="button" disabled="" class="wl-btn wl-btn--quiet">Cancelar<\/button>/);
    expect(html).toMatch(/<button type="button" disabled="" class="wl-btn wl-btn--solid">Salvar<\/button>/);
  });

  it("mostra o slot da esquerda antes dos botões", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes aEsquerda={<span>Alterações não salvas</span>} cancelar={{ href: "/x" }} principal={{ rotulo: "Salvar" }} />);
    expect(html.indexOf("Alterações não salvas")).toBeGreaterThan(-1);
    expect(html.indexOf("Alterações não salvas")).toBeLessThan(html.indexOf("Cancelar"));
  });
});

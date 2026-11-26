import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BarraDeAcoes } from "./BarraDeAcoes";
import { observarBlocos, type BlocoDosBotoes } from "./useBlocoVisivel";

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

const blocos = (visivel: boolean): BlocoDosBotoes => ({ ref: () => () => {}, visivel });

describe("BarraDeAcoes com o bloco fixo de botões (T-519)", () => {
  it("com o bloco visível a barra fica escondida: invisível, inerte e fora da leitura, mas ocupando o lugar", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes blocos={blocos(true)} cancelar={{ href: "/x" }} principal={{ rotulo: "Salvar" }} />);
    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain('inert=""');
    expect(html).toContain("opacity-0");
    expect(html).toContain("pointer-events-none");
    expect(html).toContain("transition-[opacity,transform]");
    expect(html).toContain("sticky bottom-[88px]");
  });

  it("sem o bloco na tela a barra aparece, com transição suave", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes blocos={blocos(false)} cancelar={{ href: "/x" }} principal={{ rotulo: "Salvar" }} />);
    expect(html).not.toContain("aria-hidden");
    expect(html).not.toContain("inert");
    expect(html).not.toContain("opacity-0");
    expect(html).toContain("duration-200");
  });

  it("sem a prop blocos a barra aparece sempre, como na T-514", () => {
    const html = renderToStaticMarkup(<BarraDeAcoes cancelar={{ href: "/x" }} principal={{ rotulo: "Salvar" }} />);
    expect(html).not.toContain("opacity-0");
    expect(html).not.toContain("transition-");
  });
});

type Entrada = { target: Element; isIntersecting: boolean };

/** IntersectionObserver falso: guarda quem foi observado e deixa o teste disparar a medida. */
function observadorFalso() {
  const vivos: { observados: Element[]; desligado: boolean; avisar: (e: Entrada[]) => void }[] = [];
  class Falso {
    observados: Element[] = [];
    desligado = false;
    constructor(public avisar: (e: Entrada[]) => void) {
      vivos.push(this);
    }
    observe(el: Element) {
      this.observados.push(el);
    }
    disconnect() {
      this.desligado = true;
    }
  }
  return { Falso, vivos };
}

describe("observarBlocos (IntersectionObserver)", () => {
  const a = { nome: "cabecalho" } as unknown as Element;
  const b = { nome: "pe" } as unknown as Element;

  it("avisa que o bloco está visível quando ele entra na tela e que não está quando sai", () => {
    const { Falso, vivos } = observadorFalso();
    const avisos: boolean[] = [];
    observarBlocos([a], (v) => avisos.push(v), Falso);
    expect(vivos[0]!.observados).toEqual([a]);
    vivos[0]!.avisar([{ target: a, isIntersecting: true }]);
    vivos[0]!.avisar([{ target: a, isIntersecting: false }]);
    expect(avisos).toEqual([true, false]);
  });

  it("com o bloco em dois lugares, basta um aparecer (o outro está display:none no tamanho da tela)", () => {
    const { Falso, vivos } = observadorFalso();
    const avisos: boolean[] = [];
    observarBlocos([a, b], (v) => avisos.push(v), Falso);
    vivos[0]!.avisar([{ target: a, isIntersecting: false }, { target: b, isIntersecting: true }]);
    vivos[0]!.avisar([{ target: b, isIntersecting: false }]);
    expect(avisos).toEqual([true, false]);
  });

  it("parar de observar desliga o observador", () => {
    const { Falso, vivos } = observadorFalso();
    const parar = observarBlocos([a], () => {}, Falso);
    parar();
    expect(vivos[0]!.desligado).toBe(true);
  });

  it("sem elemento ou sem IntersectionObserver a barra fica à mostra", () => {
    const { Falso } = observadorFalso();
    const sem: boolean[] = [];
    observarBlocos([], (v) => sem.push(v), Falso);
    observarBlocos([a], (v) => sem.push(v), undefined);
    expect(sem).toEqual([false, false]);
  });
});

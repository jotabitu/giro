// T-521 (VEI-08, CA-521-04): o campo com sugestões do design system, no lugar do datalist do navegador.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CampoComSugestoes } from "./CampoComSugestoes";
import { aoDigitar, aoTeclar, FECHADO } from "./logica";

const opcoes = [
  { valor: "CG 160 Fan", apoio: "Honda", chave: "Honda|CG 160 Fan" },
  { valor: "CG 160 Start", apoio: "Honda", chave: "Honda|CG 160 Start" },
  { valor: "Factor 150", apoio: "Yamaha", chave: "Yamaha|Factor 150" },
];

describe("teclado do campo com sugestões", () => {
  it("abrir: focar ou digitar abre sem opção em foco; seta para baixo abre na primeira", () => {
    expect(aoDigitar()).toEqual({ aberto: true, indice: -1 });
    expect(aoTeclar(FECHADO, "ArrowDown", 3)).toEqual({ estado: { aberto: true, indice: 0 }, escolher: null, daLista: true });
    expect(aoTeclar(FECHADO, "ArrowUp", 3).estado).toEqual({ aberto: true, indice: 2 });
  });

  it("setas movem sem dar a volta; Home e End vão às pontas", () => {
    expect(aoTeclar({ aberto: true, indice: 0 }, "ArrowDown", 3).estado.indice).toBe(1);
    expect(aoTeclar({ aberto: true, indice: 2 }, "ArrowDown", 3).estado.indice).toBe(2);
    expect(aoTeclar({ aberto: true, indice: 0 }, "ArrowUp", 3).estado.indice).toBe(0);
    expect(aoTeclar({ aberto: true, indice: -1 }, "ArrowUp", 3).estado.indice).toBe(2);
    expect(aoTeclar({ aberto: true, indice: 1 }, "End", 3).estado.indice).toBe(2);
    expect(aoTeclar({ aberto: true, indice: 1 }, "Home", 3).estado.indice).toBe(0);
    // Sem opção em foco, Home e End são do texto do campo.
    expect(aoTeclar({ aberto: true, indice: -1 }, "Home", 3).daLista).toBe(false);
  });

  it("Enter escolhe a opção em foco e fecha", () => {
    expect(aoTeclar({ aberto: true, indice: 1 }, "Enter", 3)).toEqual({ estado: FECHADO, escolher: 1, daLista: true });
  });

  it("digitar livre: sem opção em foco, o Enter não escolhe e segue para o formulário", () => {
    expect(aoTeclar(aoDigitar(), "Enter", 3)).toEqual({ estado: aoDigitar(), escolher: null, daLista: false });
    expect(aoTeclar(FECHADO, "Enter", 3).daLista).toBe(false);
    // Letras não são da lista: vão para o campo.
    expect(aoTeclar({ aberto: true, indice: 1 }, "a", 3).daLista).toBe(false);
  });

  it("Esc fecha; fechada ou sem opções, o Esc é de quem está em volta", () => {
    expect(aoTeclar({ aberto: true, indice: 1 }, "Escape", 3)).toEqual({ estado: FECHADO, escolher: null, daLista: true });
    expect(aoTeclar(FECHADO, "Escape", 3).daLista).toBe(false);
    expect(aoTeclar(aoDigitar(), "Escape", 0).daLista).toBe(false);
  });

  it("Tab fecha sem prender o foco; sem opções, as setas não abrem nada", () => {
    expect(aoTeclar({ aberto: true, indice: 1 }, "Tab", 3)).toEqual({ estado: FECHADO, escolher: null, daLista: false });
    expect(aoTeclar(FECHADO, "ArrowDown", 0).daLista).toBe(false);
  });
});

describe("CampoComSugestoes na tela", () => {
  it("é um combobox com listbox, sem datalist, e a lista nasce fechada", () => {
    const h = renderToStaticMarkup(<CampoComSugestoes rotulo="Modelo" dica="Escolha da lista ou digite" opcoes={opcoes} aoEscolher={() => {}} />);
    expect(h).toMatch(/<input[^>]*role="combobox"/);
    expect(h).toContain('aria-autocomplete="list"');
    expect(h).toContain('aria-expanded="false"');
    expect(h).toMatch(/<ul[^>]*role="listbox"[^>]*hidden=""/);
    expect(h).not.toContain("<datalist");
    expect(h).not.toContain(" list=");
    expect(h).toContain("Escolha da lista ou digite");
  });

  it("aberta, mostra o modelo e a marca em texto menor, com a escolhida marcada", () => {
    const h = renderToStaticMarkup(<CampoComSugestoes rotulo="Modelo" abertoNoInicio opcoes={opcoes} escolhida="Honda|CG 160 Start" aoEscolher={() => {}} />);
    expect(h).toContain('aria-expanded="true"');
    expect(h).not.toMatch(/<ul[^>]*hidden/);
    expect(h.match(/role="option"/g)).toHaveLength(3);
    expect(h).toContain('<span class="wl-sugestoes__apoio">Yamaha</span>');
    expect(h.match(/aria-selected="true"/g)).toHaveLength(1);
    expect(h).toMatch(/aria-selected="true"[^>]*>.*CG 160 Start/);
  });

  it("sem opções, é um campo de texto comum: a lista não aparece", () => {
    const h = renderToStaticMarkup(<CampoComSugestoes rotulo="Modelo" abertoNoInicio opcoes={[]} defaultValue="YES 125" aoEscolher={() => {}} />);
    expect(h).toContain('aria-expanded="false"');
    expect(h).toContain('value="YES 125"');
  });
});

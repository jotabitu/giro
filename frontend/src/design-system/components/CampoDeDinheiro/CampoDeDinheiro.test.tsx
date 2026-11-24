// T-509 · Campo de dinheiro com a máscara ao vivo: digitar, apagar, colar, vazio e valor grande.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { centavosDoTexto } from "@/lib/veiculos";
import { CampoDeDinheiro, InputDeDinheiro, propsDeDinheiro } from "./CampoDeDinheiro";
import { centavosDoColado, mascaraDinheiro } from "./logica";

/** O que o navegador faz a cada tecla: acrescenta ao texto do campo, e a máscara reescreve. */
const digitar = (teclas: string, inicial = "", prefixo = false): string => [...teclas].reduce((texto, t) => mascaraDinheiro(texto + t, prefixo), inicial);
/** Backspace: o navegador tira o último caractere e a máscara reescreve. */
const apagar = (texto: string, vezes = 1, prefixo = false): string => Array.from({ length: vezes }).reduce<string>((t) => mascaraDinheiro(t.slice(0, -1), prefixo), texto);

describe("mascaraDinheiro", () => {
  it("os dígitos entram pela direita como centavos", () => {
    const passos = ["5", "0", "0", "0", "0", "0"].map((_, i, a) => digitar(a.slice(0, i + 1).join("")));
    expect(passos).toEqual(["0,05", "0,50", "5,00", "50,00", "500,00", "5.000,00"]);
  });

  it("o exemplo do dono: 5 e cinco zeros mostram 5,00, 50,00 e 5.000,00 a cada tecla", () => {
    expect(digitar("500")).toBe("5,00");
    expect(digitar("5000")).toBe("50,00");
    expect(digitar("500000")).toBe("5.000,00");
  });

  it("apagar volta um dígito e o campo vazio fica vazio", () => {
    expect(apagar("5.000,00")).toBe("500,00");
    expect(apagar("5.000,00", 3)).toBe("5,00");
    expect(apagar("0,05")).toBe("");
    expect(apagar("0,05", 2)).toBe("");
    expect(mascaraDinheiro("")).toBe("");
    expect(mascaraDinheiro("abc")).toBe("");
    expect(mascaraDinheiro("0")).toBe("");
    expect(mascaraDinheiro("0,00")).toBe("");
  });

  it("valor grande ganha ponto de milhar e para no teto de R$ 999.999.999,99", () => {
    expect(digitar("123456789")).toBe("1.234.567,89");
    expect(digitar("99999999999")).toBe("999.999.999,99");
    expect(digitar("999999999999")).toBe("999.999.999,99");
  });

  it("com prefixo, o R$ fica na frente e some junto com o último dígito", () => {
    expect(digitar("500000", "", true)).toBe("R$ 5.000,00");
    expect(digitar("5", "", true)).toBe("R$ 0,05");
    expect(apagar("R$ 5.000,00", 1, true)).toBe("R$ 500,00");
    expect(apagar("R$ 0,05", 1, true)).toBe("");
    expect(mascaraDinheiro("R$ ", true)).toBe("");
  });

  it("continua de um valor que veio da API (54,90 e R$ 1.250,00)", () => {
    expect(digitar("1", "54,90")).toBe("549,01");
    expect(digitar("0", "R$ 1.250,00", true)).toBe("R$ 12.500,00");
  });

  it("o texto do campo vira centavos pela conversão que já existia, sem mudar o que a API recebe", () => {
    expect(centavosDoTexto(digitar("500000"))).toBe(500000);
    expect(centavosDoTexto(digitar("500000", "", true))).toBe(500000);
    expect(centavosDoTexto(digitar("5490"))).toBe(5490);
    expect(centavosDoTexto(digitar("5"))).toBe(5);
  });
});

describe("centavosDoColado", () => {
  it("colar 5.000,00 ou 5000 dá R$ 5.000,00", () => {
    expect(mascaraDinheiro(centavosDoColado("5.000,00"))).toBe("5.000,00");
    expect(mascaraDinheiro(centavosDoColado("5000"))).toBe("5.000,00");
    expect(mascaraDinheiro(centavosDoColado("5.000"))).toBe("5.000,00");
    expect(mascaraDinheiro(centavosDoColado("R$ 5.000,00"), true)).toBe("R$ 5.000,00");
  });

  it("vírgula separa os centavos; ponto com 1 ou 2 casas também", () => {
    expect(mascaraDinheiro(centavosDoColado("5,5"))).toBe("5,50");
    expect(mascaraDinheiro(centavosDoColado("54,90"))).toBe("54,90");
    expect(mascaraDinheiro(centavosDoColado("5000.50"))).toBe("5.000,50");
    expect(mascaraDinheiro(centavosDoColado("1.250.000"))).toBe("1.250.000,00");
  });

  it("texto sem número fica vazio", () => {
    expect(mascaraDinheiro(centavosDoColado("abc"))).toBe("");
    expect(mascaraDinheiro(centavosDoColado(""))).toBe("");
  });
});

describe("propsDeDinheiro", () => {
  it("aplica a máscara no evento antes de onChange ler o valor (serve a register e a campo controlado)", () => {
    const lidos: string[] = [];
    const { onChange } = propsDeDinheiro({ onChange: (e) => lidos.push(e.target.value) });
    const alvo = { value: "50000" };
    onChange({ target: alvo } as never);
    expect(alvo.value).toBe("500,00");
    expect(lidos).toEqual(["500,00"]);
  });

  it("com prefixo, onChange recebe R$ na frente", () => {
    const lidos: string[] = [];
    const { onChange } = propsDeDinheiro({ prefixo: true, onChange: (e) => lidos.push(e.target.value) });
    onChange({ target: { value: "R$ 5.000,0" } } as never);
    expect(lidos).toEqual(["R$ 500,00"]);
  });
});

describe("CampoDeDinheiro", () => {
  it("é um TextField: rótulo, dica, erro e teclado numérico", () => {
    const html = renderToStaticMarkup(<CampoDeDinheiro rotulo="Entrada" dica="Cobrada na retirada" value="5.000,00" onChange={() => {}} />);
    expect(html).toContain("Entrada");
    expect(html).toContain("Cobrada na retirada");
    expect(html).toContain('inputMode="numeric"');
    expect(html).toContain('value="5.000,00"');
    expect(renderToStaticMarkup(<CampoDeDinheiro rotulo="Entrada" erro="Informe um valor" />)).toContain("wl-field--error");
  });

  it("InputDeDinheiro serve ao input solto e respeita a classe da tela", () => {
    expect(renderToStaticMarkup(<InputDeDinheiro value="R$ 0,05" onChange={() => {}} />)).toContain('class="wl-input"');
    expect(renderToStaticMarkup(<InputDeDinheiro className="wl-input w-full" onChange={() => {}} />)).toContain('class="wl-input w-full"');
  });
});

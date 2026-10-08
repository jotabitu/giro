import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CodigoVerificacao } from "./CodigoVerificacao";
import { aplicarApagar, aplicarEntrada, aplicarExcluir, completo, destinoDaTecla, soDigitos } from "./logica";

describe("lógica do código de verificação", () => {
  it("soDigitos tira espaços, hífens e letras", () => {
    expect(soDigitos("481 -0x29")).toBe("481029");
  });

  it("digitar avança para a próxima caixa", () => {
    expect(aplicarEntrada("", 0, "4")).toEqual({ valor: "4", foco: 1 });
    expect(aplicarEntrada("48", 2, "1")).toEqual({ valor: "481", foco: 3 });
  });

  it("digitar numa caixa além do fim cola ao fim, sem buracos", () => {
    expect(aplicarEntrada("4", 4, "9")).toEqual({ valor: "49", foco: 2 });
  });

  it("digitar sobre um dígito troca só ele", () => {
    expect(aplicarEntrada("481029", 2, "7")).toEqual({ valor: "487029", foco: 3 });
  });

  it("na última caixa o foco fica nela e o código completa", () => {
    const r = aplicarEntrada("48102", 5, "9");
    expect(r).toEqual({ valor: "481029", foco: 5 });
    expect(completo(r.valor)).toBe(true);
  });

  it("letras e símbolos são ignorados", () => {
    expect(aplicarEntrada("48", 2, "x")).toEqual({ valor: "48", foco: 2 });
    expect(aplicarEntrada("48", 2, " ")).toEqual({ valor: "48", foco: 2 });
  });

  it("colar o código inteiro preenche tudo, mesmo com espaço ou hífen", () => {
    expect(aplicarEntrada("", 0, "481 029")).toEqual({ valor: "481029", foco: 5 });
    expect(aplicarEntrada("12", 0, "481-029")).toEqual({ valor: "481029", foco: 5 });
  });

  it("colar mais que o tamanho corta o excesso", () => {
    expect(aplicarEntrada("", 0, "48102999").valor).toBe("481029");
  });

  it("colar no meio mantém o começo e substitui dali em diante", () => {
    expect(aplicarEntrada("48", 2, "1029")).toEqual({ valor: "481029", foco: 5 });
  });

  it("colar um código curto deixa o foco na próxima caixa vazia", () => {
    expect(aplicarEntrada("", 0, "481")).toEqual({ valor: "481", foco: 3 });
  });

  it("Backspace apaga o dígito da caixa e fica nela", () => {
    expect(aplicarApagar("481", 1)).toEqual({ valor: "41", foco: 1 });
  });

  it("Backspace numa caixa vazia apaga o último dígito e volta", () => {
    expect(aplicarApagar("481", 3)).toEqual({ valor: "48", foco: 2 });
    expect(aplicarApagar("481", 5)).toEqual({ valor: "48", foco: 2 });
  });

  it("Backspace sem dígito nenhum não faz nada", () => {
    expect(aplicarApagar("", 0)).toEqual({ valor: "", foco: 0 });
  });

  it("Delete apaga o dígito e fica no lugar; sem dígito, não muda", () => {
    expect(aplicarExcluir("481", 0)).toEqual({ valor: "81", foco: 0 });
    expect(aplicarExcluir("481", 4)).toEqual({ valor: "481", foco: 4 });
  });

  it("setas, Home e End navegam sem passar das pontas", () => {
    expect(destinoDaTecla("ArrowLeft", 0)).toBe(0);
    expect(destinoDaTecla("ArrowLeft", 3)).toBe(2);
    expect(destinoDaTecla("ArrowRight", 5)).toBe(5);
    expect(destinoDaTecla("ArrowRight", 1)).toBe(2);
    expect(destinoDaTecla("Home", 4)).toBe(0);
    expect(destinoDaTecla("End", 1)).toBe(5);
    expect(destinoDaTecla("a", 1)).toBeNull();
  });

  it("respeita outro tamanho", () => {
    expect(aplicarEntrada("", 0, "12345678", 8)).toEqual({ valor: "12345678", foco: 7 });
    expect(destinoDaTecla("End", 0, 8)).toBe(7);
  });
});

describe("CodigoVerificacao (marcação)", () => {
  const base = { rotulo: "Código do aplicativo", valor: "48", aoMudar: () => {} };

  it("tem uma caixa por dígito, com autocomplete one-time-code e teclado numérico", () => {
    const html = renderToStaticMarkup(<CodigoVerificacao {...base} />);
    expect(html.match(/<input/g)).toHaveLength(6);
    expect(html.match(/autoComplete="one-time-code"|autocomplete="one-time-code"/g)).toHaveLength(6);
    expect(html.match(/inputMode="numeric"|inputmode="numeric"/g)).toHaveLength(6);
  });

  it("mostra os dígitos nas primeiras caixas e deixa as outras vazias", () => {
    const html = renderToStaticMarkup(<CodigoVerificacao {...base} />);
    expect(html).toContain('value="4"');
    expect(html).toContain('value="8"');
    expect(html.match(/value=""/g)).toHaveLength(4);
  });

  it("é um grupo nomeado pelo rótulo e cada caixa diz qual dígito é", () => {
    const html = renderToStaticMarkup(<CodigoVerificacao {...base} />);
    expect(html).toContain('role="group"');
    expect(html).toContain("Código do aplicativo");
    expect(html).toContain('aria-label="Dígito 1 de 6"');
    expect(html).toContain('aria-label="Dígito 6 de 6"');
  });

  it("sem erro não marca inválido nem mostra alerta", () => {
    const html = renderToStaticMarkup(<CodigoVerificacao {...base} />);
    expect(html).not.toContain("aria-invalid");
    expect(html).not.toContain('role="alert"');
  });

  it("com erro marca as caixas, mostra o alerta e liga o grupo a ele", () => {
    const html = renderToStaticMarkup(<CodigoVerificacao {...base} erro="Código incorreto. Confira o horário do celular e tente de novo." />);
    expect(html.match(/aria-invalid="true"/g)).toHaveLength(6);
    expect(html).toContain('role="alert"');
    expect(html).toContain("Código incorreto");
    expect(html).toContain("wl-otp__digito--erro");
    expect(html).toMatch(/aria-describedby="[^"]+-erro"/);
  });

  it("desabilitado desabilita todas as caixas", () => {
    const html = renderToStaticMarkup(<CodigoVerificacao {...base} disabled />);
    expect(html.match(/disabled=""/g)).toHaveLength(6);
  });
});

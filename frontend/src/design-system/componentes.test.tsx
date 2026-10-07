import { existsSync, readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CATALOGO } from "@/app/design-system/catalogo";
import { ExemploDe } from "@/app/design-system/exemplos";
import { Button, IconButton, StatusBadge, TextField } from "./components";

const dir = new URL("./", import.meta.url);

describe("componentes", () => {
  it("são os 12 do design system, cada um com preview e README", () => {
    expect(CATALOGO).toHaveLength(12);
    for (const c of CATALOGO) {
      expect(existsSync(new URL(`components/${c.nome}/README.md`, dir)), `README de ${c.nome}`).toBe(true);
      expect(existsSync(new URL(`components/${c.nome}/${c.nome}.tsx`, dir)), `código de ${c.nome}`).toBe(true);
    }
  });

  it("todo preview renderiza", () => {
    for (const c of CATALOGO) expect(renderToStaticMarkup(<ExemploDe slug={c.slug} />), c.nome).toContain("<");
  });

  it("estilos só usam tokens, sem cor fixa", () => {
    const css = readFileSync(new URL("componentes.css", dir), "utf8");
    expect(css.match(/#[0-9a-fA-F]{3,8}\b/g)).toBeNull();
    expect(css).not.toMatch(/rgba?\(/);
  });

  it("Button usa as classes da variante e tem tipo button", () => {
    const html = renderToStaticMarkup(<Button variante="solido" compacto>Salvar</Button>);
    expect(html).toContain("wl-btn wl-btn--solid wl-btn--sm");
    expect(html).toContain('type="button"');
  });

  it("IconButton leva aria-label", () => {
    expect(renderToStaticMarkup(<IconButton aria-label="Filtros" icone={<i />} notificacao />)).toContain('aria-label="Filtros"');
  });

  it("StatusBadge mostra o texto e o tom", () => {
    const html = renderToStaticMarkup(<StatusBadge tom="critico">Atrasado</StatusBadge>);
    expect(html).toContain("wl-badge--critical");
    expect(html).toContain("Atrasado");
  });

  it("TextField liga rótulo, dica e erro", () => {
    const html = renderToStaticMarkup(<TextField rotulo="CNH" dica="ignorada" erro="CNH vencida: renove antes de alugar" />);
    expect(html).toContain("wl-field--error");
    expect(html).toContain('aria-invalid="true"');
    expect(html).toContain("CNH vencida");
    expect(html).not.toContain("ignorada");
  });
});

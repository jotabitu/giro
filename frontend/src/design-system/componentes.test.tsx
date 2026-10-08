import { existsSync, readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CATALOGO } from "@/app/design-system/catalogo";
import { ExemploDe } from "@/app/design-system/exemplos";
import { Button, Dialogo, Gaveta, IconButton, KpiTile, StatusBadge, TextField, VehicleCard } from "./components";

const dir = new URL("./", import.meta.url);

describe("componentes", () => {
  it("são os 12 do design system mais os componentes da T-042 e T-046, cada um com preview e README", () => {
    expect(CATALOGO).toHaveLength(16);
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

  it("VehicleCard sem foto escolhe a ilustração pelo tipo", () => {
    const props = { placa: "QXA-4B21", status: "Devolução hoje", modelo: "Modelo", cliente: "Cliente", contrato: "LOC-1", diasCorridos: 1, diasContratados: 2, fatos: [{ rotulo: "A", valor: "1" }, { rotulo: "B", valor: "2" }, { rotulo: "C", valor: "3" }] } as const;
    const moto = renderToStaticMarkup(<VehicleCard {...props} />);
    const carro = renderToStaticMarkup(<VehicleCard {...props} tipo="carro" />);
    expect(moto).toContain('viewBox="0 0 120 64"');
    expect(moto).toContain("M24 44 44 20h26l16 24");
    expect(carro).not.toContain("M24 44 44 20h26l16 24");
  });

  it("Tailwind usa a variável da fonte, que leva a Geist do next/font", async () => {
    const { default: config } = await import("../../tailwind.config");
    expect(config.theme?.fontFamily).toMatchObject({ sans: ["var(--font-sans)"], mono: ["var(--font-mono)"] });
  });
});

describe("Dialogo e Gaveta (T-046)", () => {
  const sem = () => {};

  it("Dialogo nomeia e descreve a janela e só monta o conteúdo quando aberto", () => {
    const fechado = renderToStaticMarkup(
      <Dialogo aberto={false} aoFechar={sem} titulo="Cancelar contrato LOC-2841" descricao="Não dá para desfazer.">
        <p>texto do conteudo</p>
      </Dialogo>,
    );
    expect(fechado).toContain("<dialog");
    expect(fechado).toContain("aria-labelledby");
    expect(fechado).toContain("aria-describedby");
    expect(fechado).toContain("Cancelar contrato LOC-2841");
    expect(fechado).not.toContain("texto do conteudo");
    const aberto = renderToStaticMarkup(
      <Dialogo aberto aoFechar={sem} titulo="Título" acoes={<button>Confirmar</button>}>
        <p>texto do conteudo</p>
      </Dialogo>,
    );
    expect(aberto).toContain("texto do conteudo");
    expect(aberto).toContain("Confirmar");
    expect(aberto).toContain('aria-label="Fechar"');
    expect(aberto).not.toContain("aria-describedby");
  });

  it("Gaveta aplica o lado pedido e abre da esquerda por padrão", () => {
    expect(renderToStaticMarkup(<Gaveta aberto aoFechar={sem} titulo="Menu" />)).toContain("wl-gaveta--esquerda");
    expect(renderToStaticMarkup(<Gaveta aberto aoFechar={sem} titulo="Filtros" lado="baixo" />)).toContain("wl-gaveta--baixo");
  });
});

describe("KpiTile com valor longo (T-046)", () => {
  it("passa o tamanho do texto ao CSS e não abrevia o valor", () => {
    const html = renderToStaticMarkup(<KpiTile rotulo="Receita" valor="R$ 1.284.350,00" />);
    expect(html).toContain("--chars:15");
    expect(html).toContain("R$ 1.284.350,00");
  });

  it("o CSS encolhe por container query até o mínimo de 16px", () => {
    const css = readFileSync(new URL("componentes.css", dir), "utf8");
    expect(css).toContain("--chars");
    expect(css).toMatch(/container-type:\s*inline-size/);
    expect(css).toMatch(/16px/);
  });
});

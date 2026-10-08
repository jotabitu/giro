import { describe, expect, it } from "vitest";
import { aplicarMarca } from "./marca";
import { contraste, corSobreMarca, cssDaMarca, hexValido, MARCA_PADRAO, marcaSuave, MINIMO_CONTRASTE, variaveisDaMarca } from "./marca";

// Cores de clientes variadas, claras, escuras e do meio da escala.
const CORES = ["#c8f04a", "#ffffff", "#000000", "#e11d48", "#2563eb", "#16a34a", "#f59e0b", "#7c3aed", "#0ea5e9", "#9ca3af", "#777777", "#ff7f00", "#1e3a8a"];

describe("marca da empresa", () => {
  it("on-brand tem contraste mínimo de 4,5:1 em qualquer cor", () => {
    for (const cor of CORES) expect(contraste(cor, corSobreMarca(cor)), cor).toBeGreaterThanOrEqual(MINIMO_CONTRASTE);
  });

  it("on-brand de uma cor de matiz variado também passa (varredura)", () => {
    for (let r = 0; r < 256; r += 51)
      for (let g = 0; g < 256; g += 51)
        for (let b = 0; b < 256; b += 51) {
          const cor = `#${[r, g, b].map((c) => c.toString(16).padStart(2, "0")).join("")}`;
          expect(contraste(cor, corSobreMarca(cor)), cor).toBeGreaterThanOrEqual(MINIMO_CONTRASTE);
        }
  });

  it("a cor padrão usa tinta (limão é claro)", () => {
    expect(MARCA_PADRAO).toBe("#c8f04a");
    expect(corSobreMarca(MARCA_PADRAO)).toBe("#111114");
  });

  it("brand-soft é clareada no tema claro e escurecida no escuro", () => {
    const base = "#2563eb";
    expect(contraste(marcaSuave(base, "light"), "#ffffff")).toBeLessThan(contraste(base, "#ffffff"));
    expect(contraste(marcaSuave(base, "dark"), "#000000")).toBeLessThan(contraste(base, "#000000"));
  });

  it("cssDaMarca troca as três variáveis nos dois temas", () => {
    const css = cssDaMarca("#2563eb");
    for (const v of ["--brand: #2563eb", "--on-brand:", "--brand-soft:", '[data-theme="dark"]']) expect(css).toContain(v);
  });

  it("cor inválida cai na padrão e não injeta CSS", () => {
    const css = cssDaMarca("red; } body { display: none");
    expect(css).toContain(`--brand: ${MARCA_PADRAO}`);
    expect(css).not.toContain("display");
    expect(hexValido("#12345")).toBe(false);
    expect(() => variaveisDaMarca("azul")).toThrow();
  });

  it("aplicarMarca existe para troca em execução no navegador", () => {
    expect(typeof aplicarMarca).toBe("function");
  });
});

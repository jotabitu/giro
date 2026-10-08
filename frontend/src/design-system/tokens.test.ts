import { describe, expect, it } from "vitest";
import { cores, cssDosTemas } from "./tokens";

describe("tokens", () => {
  it("claro e escuro têm os mesmos nomes", () => {
    expect(Object.keys(cores.dark)).toEqual(Object.keys(cores.light));
  });

  it("expõe a marca como variável trocável", () => {
    const css = cssDosTemas();
    for (const v of ["--brand:", "--brand-soft:", "--on-brand:"]) expect(css).toContain(v);
  });
});

import { describe, expect, it } from "vitest";
import { regrasDeSenha } from "./senha";

describe("regrasDeSenha", () => {
  it("marca cada regra pela senha digitada", () => {
    const r = regrasDeSenha("curta1", "a@b.com");
    expect(r.map((x) => x.ok)).toEqual([false, true, true]);
  });

  it("aceita senha com 12 caracteres, letras e números", () => {
    expect(regrasDeSenha("senhaforte123").every((x) => x.ok)).toBe(true);
  });

  it("recusa senha igual ao e-mail", () => {
    expect(regrasDeSenha("rodrigo@motorapida.com.br", "rodrigo@motorapida.com.br").find((x) => x.chave === "diferente")?.ok).toBe(false);
  });
});

import { describe, expect, it } from "vitest";
import { montarCsp, novoNonce } from "./csp";

describe("montarCsp", () => {
  it("amarra o script ao nonce e proíbe inline e frames", () => {
    const csp = montarCsp("abc", false);
    expect(csp).toContain("script-src 'self' 'nonce-abc' 'strict-dynamic'");
    expect(csp).not.toMatch(/script-src[^;]*'unsafe-(inline|eval)'/);
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("upgrade-insecure-requests");
  });

  it("só libera eval em dev", () => {
    expect(montarCsp("abc", true)).toContain("'unsafe-eval'");
    expect(montarCsp("abc", true)).not.toContain("upgrade-insecure-requests");
  });

  it("gera nonce diferente a cada chamada", () => {
    expect(novoNonce()).not.toBe(novoNonce());
  });
});

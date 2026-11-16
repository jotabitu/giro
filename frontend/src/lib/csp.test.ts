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

  it("sem GIRO_ARQUIVOS_ORIGEM a img-src fica só com a mesma origem", () => {
    expect(montarCsp("abc", false)).toContain("img-src 'self' data: blob:;");
    expect(montarCsp("abc", false, "")).toBe(montarCsp("abc", false));
  });

  it("acrescenta as origens do armazenamento à img-src", () => {
    const csp = montarCsp(
      "abc",
      false,
      " https://giro-arquivos.conta.r2.cloudflarestorage.com  https://conta.r2.cloudflarestorage.com/ ",
    );
    expect(csp).toContain(
      "img-src 'self' data: blob: https://giro-arquivos.conta.r2.cloudflarestorage.com https://conta.r2.cloudflarestorage.com;",
    );
    expect(csp).toContain("object-src 'none'");
  });

  it("ignora origem inválida", () => {
    const csp = montarCsp(
      "abc",
      false,
      "https: * http://s3.exemplo.com https://*.exemplo.com https://s3.exemplo.com/bucket https://ok.exemplo.com",
    );
    expect(csp).toContain("img-src 'self' data: blob: https://ok.exemplo.com;");
  });

  it("gera nonce diferente a cada chamada", () => {
    expect(novoNonce()).not.toBe(novoNonce());
  });
});

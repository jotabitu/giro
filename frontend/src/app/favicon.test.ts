import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Favicon do Giro em todas as abas, inclusive no sistema da locadora: única exceção ao white label
// (decisão do dono, 12 nov 2026, T-465). Arquivos de convenção do App Router, copiados do kit da marca.
// `icon.ico`, e não `favicon.ico`: o Next põe ?hash no link do `icon`, e o navegador troca o ícone guardado
// em cache por origem quando o arquivo muda (no `favicon.ico` o link nunca muda).
const RAIZ = join(__dirname, "..", "..");

describe("favicon do Giro", () => {
  it.each([
    ["src/app/icon.ico", "docs/marca/kit/web/favicon.ico"],
    ["src/app/apple-icon.png", "docs/marca/kit/web/apple-touch-icon.png"],
  ])("%s é a cópia sem mudança do kit (%s)", (app, kit) => {
    const copia = readFileSync(join(RAIZ, app));
    const original = readFileSync(join(RAIZ, "..", kit));
    expect(copia.equals(original)).toBe(true);
  });
});

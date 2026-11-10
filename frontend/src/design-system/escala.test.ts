import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { espacamento } from "./tokens";

// O Tailwind do Giro usa a escala de espacos de tokens.ts no lugar da dele (tailwind.config.ts).
// Classe de espaco fora da escala nao gera CSS e o espaco fica zero, sem erro nenhum.
// Este teste recusa a classe antes de chegar na tela. Medida arbitraria (`mt-[18px]`) segue permitida.

const PASSOS = new Set<string>(["0", "px", ...Object.keys(espacamento)]);

const PREFIXOS =
  "(?:-?(?:m|p)(?:[xytblrse])?|gap(?:-[xy])?|-?space-[xy]|-?(?:inset(?:-[xy])?|top|right|bottom|left|start|end)|w|h|size|min-w|min-h|max-w|max-h|basis|-?scroll-(?:m|p)(?:[xytblrse])?)";
const CLASSE = new RegExp(`^${PREFIXOS}-(\\d+(?:\\.\\d+)?)$`);

export function classesForaDaEscala(texto: string): string[] {
  const fora: string[] = [];
  for (const cru of texto.split(/[\s"'`{}()<>,;=]+/)) {
    const classe = cru.replace(/^(?:[a-z0-9-]+:)+/i, "").replace(/^!/, "");
    const m = CLASSE.exec(classe);
    if (m && !PASSOS.has(m[1] as string)) fora.push(classe);
  }
  return fora;
}

function arquivos(dir: string): string[] {
  return readdirSync(dir).flatMap((nome) => {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) return arquivos(caminho);
    return /\.(tsx?|css)$/.test(nome) && !/\.test\.tsx?$/.test(nome) ? [caminho] : [];
  });
}

describe("escala de espaços", () => {
  it("a escala tem o passo 16 (64 px), das miniaturas", () => {
    expect(espacamento["16"]).toBe("64px");
    expect(classesForaDaEscala("size-16 md:h-16")).toEqual([]);
  });

  it("o verificador reconhece classe fora da escala", () => {
    expect(classesForaDaEscala('className="mt-1.5 gap-13 md:p-7 w-1/2 mt-[18px] -mt-13 z-10"')).toEqual([
      "gap-13",
      "-mt-13",
    ]);
  });

  it("nenhum arquivo de src usa classe de espaço fora da escala", () => {
    const problemas: string[] = [];
    for (const arquivo of arquivos(join(process.cwd(), "src"))) {
      const fora = classesForaDaEscala(readFileSync(arquivo, "utf8"));
      if (fora.length) problemas.push(`${arquivo}: ${[...new Set(fora)].join(", ")}`);
    }
    expect(problemas).toEqual([]);
  });
});

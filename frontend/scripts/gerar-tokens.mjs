// Gera src/design-system/tokens.ts a partir de docs/design-system/tokens.json.
// Ponto de partida da T-002; o agente design-system assume a pasta na T-004.
import { readFileSync, writeFileSync } from "node:fs";

const dir = new URL("../../docs/design-system/", import.meta.url);
const j = JSON.parse(readFileSync(new URL("tokens.json", dir), "utf8"));
const cores = Object.fromEntries(j.color.tokens.map((t) => [t.name, t.value]));
const pick = (tema) => Object.fromEntries(Object.entries(cores).map(([k, v]) => [k, v[tema]]));
const espacos = Object.fromEntries(j.spacing.tokens.map((t) => [t.name.replace("space-", ""), t.value]));
const raios = Object.fromEntries(j.radius.tokens.map((t) => [t.name.replace("radius-", ""), t.value]));
const sombra = Object.fromEntries(Object.entries(j.shadow.tokens[0].value));
const fmt = (o) => JSON.stringify(o, null, 2);

writeFileSync(
  new URL("../src/design-system/tokens.ts", import.meta.url),
  `// Gerado de docs/design-system/tokens.json por scripts/gerar-tokens.mjs. Não edite à mão.
export const cores = {
  light: ${fmt(pick("light"))},
  dark: ${fmt(pick("dark"))},
} as const;

export type NomeCor = keyof typeof cores.light;

export const espacamento = ${fmt(espacos)} as const;

export const raio = ${fmt(raios)} as const;

export const sombraPop = ${fmt(sombra)} as const;

export const fontes = {
  sans: ${JSON.stringify(j.type.families.sans)},
  mono: ${JSON.stringify(j.type.families.mono)},
} as const;

export const tipografia = ${fmt(Object.fromEntries(j.type.groups.flatMap((g) => g.styles.map((s) => [s.name, { fontSize: s.fontSize, lineHeight: s.lineHeight, fontWeight: s.fontWeight, ...(s.letterSpacing ? { letterSpacing: s.letterSpacing } : {}), family: g.family }]))))} as const;

/** Variáveis CSS de um tema. As cores da empresa (brand, on-brand, brand-soft) entram aqui e podem ser trocadas em execução. */
export function variaveisCss(tema: "light" | "dark"): string {
  const c = cores[tema];
  const linhas = Object.entries(c).map(([k, v]) => \`--\${k}: \${v};\`);
  linhas.push(\`--shadow-pop: \${sombraPop[tema]};\`);
  return linhas.join(" ");
}

export const variaveisBase: string = [
  ...Object.entries(espacamento).map(([k, v]) => \`--space-\${k}: \${v};\`),
  ...Object.entries(raio).map(([k, v]) => \`--radius-\${k}: \${v};\`),
  \`--font-sans: \${fontes.sans};\`,
  \`--font-mono: \${fontes.mono};\`,
].join(" ");

export function cssDosTemas(): string {
  return \`:root, [data-theme="light"] { \${variaveisCss("light")} } [data-theme="dark"] { \${variaveisCss("dark")} } :root { \${variaveisBase} }\`;
}
`,
);

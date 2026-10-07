import type { Config } from "tailwindcss";
import { cores, espacamento, raio, fontes, tipografia } from "./src/design-system/tokens";

// As cores apontam para variáveis CSS (tema claro/escuro e marca da empresa trocam em execução);
// os nomes e valores vêm de src/design-system/tokens.ts.
const corVar = Object.fromEntries(
  Object.keys(cores.light).map((nome) => [nome, `var(--${nome})`]),
);

const fontSize: Record<string, [string, { lineHeight: string; fontWeight: string; letterSpacing?: string }]> = {};
for (const [nome, t] of Object.entries(tipografia)) {
  fontSize[nome] = [
    t.fontSize,
    {
      lineHeight: t.lineHeight,
      fontWeight: String(t.fontWeight),
      ...("letterSpacing" in t ? { letterSpacing: t.letterSpacing as string } : {}),
    },
  ];
}

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    colors: { transparent: "transparent", current: "currentColor", ...corVar },
    spacing: { 0: "0px", px: "1px", ...espacamento },
    borderRadius: { none: "0", ...raio, full: "9999px" },
    fontFamily: { sans: [fontes.sans], mono: [fontes.mono] },
    fontSize,
    boxShadow: { pop: "var(--shadow-pop)", none: "none" },
    extend: {},
  },
  plugins: [],
};

export default config;

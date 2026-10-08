import type { Config } from "tailwindcss";
import { cores, espacamento, raio, tipografia } from "./src/design-system/tokens";

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
    // Mesmo ponto de quebra de componentes.css (720px): acima disso, desktop.
    screens: { md: "721px", lg: "1024px", xl: "1280px" },
    colors: { transparent: "transparent", current: "currentColor", ...corVar },
    spacing: { 0: "0px", px: "1px", ...espacamento },
    borderRadius: { none: "0", ...raio, full: "9999px" },
    // Aponta para as variáveis (que já incluem a Geist carregada pelo next/font e o fallback dos tokens).
    fontFamily: { sans: ["var(--font-sans)"], mono: ["var(--font-mono)"] },
    fontSize,
    boxShadow: { pop: "var(--shadow-pop)", none: "none" },
    extend: {},
  },
  plugins: [],
};

export default config;

// Gerado de docs/design-system/tokens.json por scripts/gerar-tokens.mjs. Não edite à mão.
export const cores = {
  light: {
  "canvas": "#ecebf0",
  "surface": "#ffffff",
  "surface-sunken": "#f3f3f6",
  "line": "#e4e4ea",
  "ink": "#111114",
  "ink-muted": "#686873",
  "solid": "#111114",
  "on-solid": "#ffffff",
  "on-solid-muted": "#a3a3ad",
  "brand": "#c8f04a",
  "on-brand": "#111114",
  "brand-soft": "#eef9cc",
  "focus": "#111114",
  "success": "#1e9e57",
  "success-soft": "#dff4e6",
  "success-ink": "#11693a",
  "info": "#2e6be6",
  "info-soft": "#e1eafc",
  "info-ink": "#1d4bae",
  "warning": "#f2a516",
  "on-warning": "#111114",
  "warning-soft": "#fceecf",
  "warning-ink": "#85560a",
  "critical": "#d23f28",
  "on-critical": "#ffffff",
  "critical-soft": "#fce3de",
  "critical-ink": "#a52f1c"
},
  dark: {
  "canvas": "#0b0b0e",
  "surface": "#17171b",
  "surface-sunken": "#212127",
  "line": "#2c2c34",
  "ink": "#f4f4f6",
  "ink-muted": "#a3a3ad",
  "solid": "#f4f4f6",
  "on-solid": "#111114",
  "on-solid-muted": "#5c5c66",
  "brand": "#c8f04a",
  "on-brand": "#111114",
  "brand-soft": "#2b3510",
  "focus": "#f4f4f6",
  "success": "#4ccb7f",
  "success-soft": "#12301e",
  "success-ink": "#7bdda0",
  "info": "#6d9df5",
  "info-soft": "#142443",
  "info-ink": "#9dbdfa",
  "warning": "#f2a516",
  "on-warning": "#111114",
  "warning-soft": "#3a2b0b",
  "warning-ink": "#f3c969",
  "critical": "#f0735e",
  "on-critical": "#1a0906",
  "critical-soft": "#3a1610",
  "critical-ink": "#f49a8a"
},
} as const;

export type NomeCor = keyof typeof cores.light;

export const espacamento = {
  "1": "4px",
  "2": "8px",
  "3": "12px",
  "4": "16px",
  "5": "20px",
  "6": "24px",
  "8": "32px",
  "10": "40px"
} as const;

export const raio = {
  "sm": "10px",
  "md": "14px",
  "lg": "24px",
  "xl": "32px",
  "pill": "999px"
} as const;

export const sombraPop = {
  "light": "0 12px 32px rgba(17, 17, 20, 0.12)",
  "dark": "0 12px 32px rgba(0, 0, 0, 0.5)"
} as const;

export const fontes = {
  sans: "Geist, \"Helvetica Neue\", Arial, sans-serif",
  mono: "\"Geist Mono\", ui-monospace, Menlo, monospace",
} as const;

export const tipografia = {
  "display": {
    "fontSize": "40px",
    "lineHeight": "44px",
    "fontWeight": 600,
    "letterSpacing": "-0.02em",
    "family": "sans"
  },
  "metric": {
    "fontSize": "44px",
    "lineHeight": "44px",
    "fontWeight": 600,
    "letterSpacing": "-0.03em",
    "family": "sans"
  },
  "title": {
    "fontSize": "24px",
    "lineHeight": "30px",
    "fontWeight": 600,
    "letterSpacing": "-0.01em",
    "family": "sans"
  },
  "heading": {
    "fontSize": "18px",
    "lineHeight": "24px",
    "fontWeight": 600,
    "family": "sans"
  },
  "body": {
    "fontSize": "15px",
    "lineHeight": "22px",
    "fontWeight": 400,
    "family": "sans"
  },
  "body-strong": {
    "fontSize": "15px",
    "lineHeight": "22px",
    "fontWeight": 500,
    "family": "sans"
  },
  "caption": {
    "fontSize": "14px",
    "lineHeight": "20px",
    "fontWeight": 400,
    "family": "sans"
  },
  "overline": {
    "fontSize": "12px",
    "lineHeight": "16px",
    "fontWeight": 600,
    "letterSpacing": "0.08em",
    "family": "sans"
  },
  "data": {
    "fontSize": "14px",
    "lineHeight": "20px",
    "fontWeight": 400,
    "letterSpacing": "0.02em",
    "family": "mono"
  }
} as const;

/** Variáveis CSS de um tema. As cores da empresa (brand, on-brand, brand-soft) entram aqui e podem ser trocadas em execução. */
export function variaveisCss(tema: "light" | "dark"): string {
  const c = cores[tema];
  const linhas = Object.entries(c).map(([k, v]) => `--${k}: ${v};`);
  linhas.push(`--shadow-pop: ${sombraPop[tema]};`);
  return linhas.join(" ");
}

export const variaveisBase: string = [
  ...Object.entries(espacamento).map(([k, v]) => `--space-${k}: ${v};`),
  ...Object.entries(raio).map(([k, v]) => `--radius-${k}: ${v};`),
  `--font-sans: ${fontes.sans};`,
  `--font-mono: ${fontes.mono};`,
].join(" ");

export function cssDosTemas(): string {
  return `:root, [data-theme="light"] { ${variaveisCss("light")} } [data-theme="dark"] { ${variaveisCss("dark")} } :root { ${variaveisBase} }`;
}

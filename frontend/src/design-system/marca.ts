// White label: a empresa troca só --brand, --on-brand e --brand-soft (docs/design-system/README.md).
// brand é sempre preenchimento, nunca texto ou borda sobre surface.
import { cores } from "./tokens";

export const ID_ESTILO_MARCA = "marca-da-empresa";

const HEX = /^#[0-9a-fA-F]{6}$/;

/** Cor padrão para demonstração e clientes sem identidade. */
export const MARCA_PADRAO: string = cores.light.brand;

const BRANCO = "#ffffff";
const PRETO = "#000000";
const TINTA = cores.light.ink;
export const MINIMO_CONTRASTE = 4.5;


export function hexValido(hex: string): boolean {
  return HEX.test(hex);
}

function rgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function paraHex([r, g, b]: [number, number, number]): string {
  return `#${[r, g, b].map((c) => Math.round(c).toString(16).padStart(2, "0")).join("")}`;
}

function luminancia(hex: string): number {
  const [r, g, b] = rgb(hex).map((c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Razão de contraste WCAG entre duas cores #rrggbb. */
export function contraste(a: string, b: string): number {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x) as [number, number];
  return (claro + 0.05) / (escuro + 0.05);
}

/**
 * Texto sobre a cor da marca: tinta se a cor for clara, branco se for escura (pelo maior contraste).
 * Em tons médios em que nenhum dos dois chega a 4,5:1, usa preto puro, que então sempre passa
 * (se o branco falha, a luminância da cor passa de 0,18 e o preto dá mais de 4,6:1).
 */
export function corSobreMarca(brand: string): string {
  const melhor = contraste(brand, TINTA) >= contraste(brand, BRANCO) ? TINTA : BRANCO;
  return contraste(brand, melhor) >= MINIMO_CONTRASTE ? melhor : PRETO;
}

function misturar(hex: string, base: string, parte: number): string {
  const a = rgb(hex);
  const b = rgb(base);
  return paraHex(a.map((c, i) => c * parte + (b[i] as number) * (1 - parte)) as [number, number, number]);
}

/** brand-soft: a marca clareada sobre branco (claro) ou escurecida sobre preto (escuro). */
export function marcaSuave(brand: string, tema: "light" | "dark"): string {
  return tema === "light" ? misturar(brand, "#ffffff", 0.3) : misturar(brand, "#000000", 0.215);
}

export type VariaveisDaMarca = {
  "--brand": string;
  "--on-brand": string;
  "--brand-soft": string;
};

export function variaveisDaMarca(brand: string, tema: "light" | "dark" = "light"): VariaveisDaMarca {
  if (!hexValido(brand)) throw new Error(`Cor da marca inválida: ${brand}`);
  const cor = brand.toLowerCase();
  return { "--brand": cor, "--on-brand": corSobreMarca(cor), "--brand-soft": marcaSuave(cor, tema) };
}

/**
 * CSS da marca da empresa, para ficar depois do CSS dos temas. Cor inválida cai na padrão.
 * Só emite valores #rrggbb calculados aqui, então não há como injetar CSS.
 */
export function cssDaMarca(brand: string): string {
  const cor = hexValido(brand) ? brand : MARCA_PADRAO;
  const claro = variaveisDaMarca(cor, "light");
  const escuro = variaveisDaMarca(cor, "dark");
  return (
    `:root, [data-theme="light"] { --brand: ${claro["--brand"]}; --on-brand: ${claro["--on-brand"]}; --brand-soft: ${claro["--brand-soft"]}; } ` +
    `[data-theme="dark"] { --brand: ${escuro["--brand"]}; --on-brand: ${escuro["--on-brand"]}; --brand-soft: ${escuro["--brand-soft"]}; }`
  );
}

/** Navegador: troca a marca em execução, sem recarregar. */
export function aplicarMarca(brand: string): void {
  let el = document.getElementById(ID_ESTILO_MARCA);
  if (!el) {
    el = document.createElement("style");
    el.id = ID_ESTILO_MARCA;
    document.head.appendChild(el);
  }
  el.textContent = cssDaMarca(brand);
}

export type Tema = "light" | "dark";

/** Navegador: troca o tema claro/escuro. */
export function aplicarTema(tema: Tema): void {
  document.documentElement.setAttribute("data-theme", tema);
}

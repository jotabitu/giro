// Marca da locadora na tela. A API entrega as cores prontas (docs/api/empresas.md); aqui só se aplica,
// sem conta de contraste, mistura ou iniciais (ADR 0004: a API decide, a tela mostra).
import type { MarcaEmpresa } from "@/lib/api/tipos";

const HEX = /^#[0-9a-fA-F]{6}$/;

/** O que as telas usam: nome, iniciais e logo (sempre por `<img>`, S-12). */
export type MarcaDaTela = {
  nome: string;
  iniciais: string;
  logo: { url: string; largura: number | null; altura: number | null } | null;
};

/** Host sem empresa (404) ou marca ainda não carregada: texto neutro, sem logo, cores padrão do design system. */
export const MARCA_NEUTRA: MarcaDaTela = { nome: "Sua locadora", iniciais: "SL", logo: null };

export function marcaDaTela(m: MarcaEmpresa | null | undefined): MarcaDaTela {
  return m ? { nome: m.nome_exibicao, iniciais: m.iniciais, logo: m.logo } : MARCA_NEUTRA;
}

/**
 * CSS das três variáveis da marca nos dois temas, com os valores da API. Só emite `#RRGGBB`, então não há como
 * injetar CSS. Qualquer cor fora do formato descarta o conjunto (`null`) e a tela fica com a padrão.
 */
export function cssDaMarcaDaApi(m: Pick<MarcaEmpresa, "cor" | "cor_sobre" | "cor_suave" | "cor_suave_escuro">): string | null {
  if (![m.cor, m.cor_sobre, m.cor_suave, m.cor_suave_escuro].every((c) => HEX.test(c))) return null;
  return (
    `:root, [data-theme="light"] { --brand: ${m.cor}; --on-brand: ${m.cor_sobre}; --brand-soft: ${m.cor_suave}; } ` +
    `[data-theme="dark"] { --brand: ${m.cor}; --on-brand: ${m.cor_sobre}; --brand-soft: ${m.cor_suave_escuro}; }`
  );
}

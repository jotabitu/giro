// Edição da marca (docs/api/empresas.md, "Escrita da marca"). Só decide o que enviar e o que mostrar;
// contraste, cor suave e iniciais vêm da API (ADR 0004: a API decide, a tela mostra).
import type { CorpoDaMarca, CorpoDaSimulacao, MarcaEmpresa } from "@/lib/api/tipos";

export type CorDaEscolha = { hex: string; rotulo: string };

/** As seis cores do passo Marca do assistente (Onboarding-Marca). */
export const CORES_DO_ASSISTENTE: CorDaEscolha[] = [
  { hex: "#C8F04A", rotulo: "Verde-limão" },
  { hex: "#FF7A45", rotulo: "Laranja" },
  { hex: "#2F6FED", rotulo: "Azul" },
  { hex: "#16B8A6", rotulo: "Verde-água" },
  { hex: "#E11D48", rotulo: "Vermelho" },
  { hex: "#7A5AF8", rotulo: "Roxo" },
];

/** Atalhos de "Cor principal" em Empresa e marca (Admin-Marca); a cor salva vem na frente. */
export const CORES_DE_ATALHO: CorDaEscolha[] = [
  { hex: "#FF7A45", rotulo: "Laranja" },
  { hex: "#2F6FED", rotulo: "Azul" },
  { hex: "#16B8A6", rotulo: "Verde-água" },
  { hex: "#111114", rotulo: "Preto" },
];

export const ACEITA_LOGO = "image/png,image/svg+xml,.png,.svg";
export const AJUDA_DO_LOGO = "PNG ou SVG, fundo transparente, até 2 MB";
export const ESPERA_DA_COR_MS = 300;

const HEX = /^#[0-9a-fA-F]{6}$/;

export type EscolhaDoLogo = { tipo: "salvo" } | { tipo: "novo"; arquivo: File } | { tipo: "removido" };

export type EdicaoDaMarca = { nome: string; cor: string; logo: EscolhaDoLogo };

export function edicaoInicial(m: Pick<MarcaEmpresa, "nome_exibicao" | "cor">): EdicaoDaMarca {
  return { nome: m.nome_exibicao, cor: m.cor, logo: { tipo: "salvo" } };
}

/** Texto digitado em "Cor principal": aceita com ou sem `#`, em qualquer caixa. */
export function normalizarCor(texto: string): string {
  const t = texto.trim();
  return t === "" || t.startsWith("#") ? t : `#${t}`;
}

/** Formato `#RRGGBB` (ou vazio, que volta à cor padrão). Quem confere de verdade é a API. */
export function corCompleta(texto: string): boolean {
  const t = normalizarCor(texto);
  return t === "" || HEX.test(t);
}

/** O corpo da simulação, ou `null` enquanto a cor digitada ainda não é uma cor inteira. */
export function corpoDaSimulacao(e: Pick<EdicaoDaMarca, "nome" | "cor">): CorpoDaSimulacao | null {
  const cor = normalizarCor(e.cor);
  return corCompleta(cor) ? { cor, nome_exibicao: e.nome } : null;
}

const mesmaCor = (a: string, b: string) => normalizarCor(a).toUpperCase() === normalizarCor(b).toUpperCase();

/** O PATCH só leva o que mudou; `{}` (Continuar do assistente sem mudança) também é aceito e marca o passo. */
export function corpoDoSalvar(guardada: Pick<MarcaEmpresa, "nome_exibicao" | "cor">, e: EdicaoDaMarca): CorpoDaMarca {
  const corpo: CorpoDaMarca = {};
  if (e.nome.trim() !== guardada.nome_exibicao) corpo.nome_exibicao = e.nome.trim();
  if (!mesmaCor(e.cor, guardada.cor)) corpo.cor = normalizarCor(e.cor);
  if (e.logo.tipo === "novo") corpo.logo = e.logo.arquivo;
  if (e.logo.tipo === "removido") corpo.remover_logo = true;
  return corpo;
}

export function mudou(guardada: Pick<MarcaEmpresa, "nome_exibicao" | "cor">, e: EdicaoDaMarca): boolean {
  return Object.keys(corpoDoSalvar(guardada, e)).length > 0;
}

/**
 * O logo que aparece na tela: o salvo (URL da API), o arquivo escolhido e ainda não salvo (`urlLocal`, de
 * `URL.createObjectURL`, sempre em `<img>`, S-12) ou nenhum, e então valem as iniciais.
 */
export function logoVisivel(guardada: Pick<MarcaEmpresa, "logo">, logo: EscolhaDoLogo, urlLocal: string | null): string | null {
  if (logo.tipo === "removido") return null;
  if (logo.tipo === "novo") return urlLocal;
  return guardada.logo?.url ?? null;
}

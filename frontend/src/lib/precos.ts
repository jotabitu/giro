import type { CobrancaDoExtra, CorpoDoPreco, PeriodicidadeDoPlano, PlanoEspecialDePreco } from "@/lib/api";
import { dinheiro } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";

// Tabelas de preço (LOC-01, LOC-02, LOC-15). A tela só formata e converte o que a pessoa digita; quem valida e calcula é a API.

export const CAMPOS_DE_PRECO = [
  { chave: "diaria_centavos", rotulo: "Diária" },
  { chave: "semanal_centavos", rotulo: "Semanal" },
  { chave: "mensal_centavos", rotulo: "Mensal" },
  { chave: "caucao_centavos", rotulo: "Caução" },
] as const;

export type ChaveDePreco = (typeof CAMPOS_DE_PRECO)[number]["chave"];

/** 5490 vira "54,90", o texto que vai no campo de valor. */
export function reaisDoCentavos(centavos: number): string {
  return (centavos / 100).toFixed(2).replace(".", ",");
}

export type TextosDePreco = Record<ChaveDePreco, string>;

export const textosDoPreco = (p: CorpoDoPreco | null | undefined): TextosDePreco => ({
  diaria_centavos: p ? reaisDoCentavos(p.diaria_centavos) : "",
  semanal_centavos: p ? reaisDoCentavos(p.semanal_centavos) : "",
  mensal_centavos: p ? reaisDoCentavos(p.mensal_centavos) : "",
  caucao_centavos: p ? reaisDoCentavos(p.caucao_centavos) : "",
});

/** Os quatro textos em centavos, ou os campos que não são valor (erro local; a API confere o resto). */
export function precoDosTextos(t: TextosDePreco): { preco: CorpoDoPreco } | { erros: Partial<Record<ChaveDePreco, string>> } {
  const erros: Partial<Record<ChaveDePreco, string>> = {};
  const valores = {} as CorpoDoPreco;
  for (const { chave } of CAMPOS_DE_PRECO) {
    const c = centavosDoTexto(t[chave]);
    if (c === null) erros[chave] = "Informe um valor em reais, como 54,90.";
    else valores[chave] = c;
  }
  return Object.keys(erros).length ? { erros } : { preco: valores };
}

export const precoIgual = (a: CorpoDoPreco, b: CorpoDoPreco) => CAMPOS_DE_PRECO.every(({ chave }) => a[chave] === b[chave]);

export const ROTULO_DA_COBRANCA: Record<CobrancaDoExtra, string> = { por_periodo: "por período", unica: "cobrança única" };

const SUFIXO: Record<PeriodicidadeDoPlano, string> = { diaria: "dia", semanal: "sem", mensal: "mês" };
export const ROTULO_DA_PERIODICIDADE: Record<PeriodicidadeDoPlano, string> = { diaria: "Diária", semanal: "Semanal", mensal: "Mensal" };

/** "R$ 279,00/sem" para preço fixo e "−10%" para desconto, como a lista de planos especiais mostra. */
export function valorDoPlano(p: Pick<PlanoEspecialDePreco, "regra" | "preco_centavos" | "desconto_pct" | "periodicidade">): string {
  if (p.regra === "preco_fixo") return p.preco_centavos === null ? "—" : `${dinheiro(p.preco_centavos)}/${SUFIXO[p.periodicidade as PeriodicidadeDoPlano]}`;
  if (p.desconto_pct === null) return "—";
  return `−${Number(p.desconto_pct).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}

export const contratos = (n: number) => `${n} ${n === 1 ? "contrato" : "contratos"}`;

/** Aviso do `locacoes_em_andamento_mantidas` que a API devolve ao gravar um preço (LOC-15). */
export function avisoDePrecoGravado(mantidas: number): string {
  if (mantidas <= 0) return "Preço salvo. Vale para os contratos novos.";
  return `Preço salvo. Vale para os contratos novos; ${mantidas} ${mantidas === 1 ? "locação em andamento mantém" : "locações em andamento mantêm"} o preço da assinatura.`;
}

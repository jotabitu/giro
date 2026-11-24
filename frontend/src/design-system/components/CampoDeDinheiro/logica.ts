/** Máscara de dinheiro ao digitar: os dígitos entram pela direita como centavos ("5" → "0,05", "500000" → "5.000,00"). */

/** Até R$ 999.999.999,99; a API confere o limite de cada campo. */
const MAX_DIGITOS = 11;

const milhar = (n: string): string => n.replace(/\B(?=(\d{3})+(?!\d))/g, ".");

/** Só dígitos, sem zeros à esquerda. Vazio (ou só zeros) fica vazio. */
export function digitosDoDinheiro(texto: string): string {
  return texto.replace(/\D/g, "").replace(/^0+/, "").slice(0, MAX_DIGITOS);
}

/** O que o campo mostra para o que a pessoa digitou. Sem dígito, vazio; com `prefixo`, "R$ " na frente. */
export function mascaraDinheiro(texto: string, prefixo = false): string {
  const d = digitosDoDinheiro(texto);
  if (!d) return "";
  const c = d.padStart(3, "0");
  return `${prefixo ? "R$ " : ""}${milhar(c.slice(0, -2))},${c.slice(-2)}`;
}

/**
 * Texto colado em centavos (só dígitos): com vírgula, a vírgula separa os centavos ("5.000,50", "5,5");
 * "5000.50" tem centavos; sem vírgula nem centavos ("5000", "5.000") é em reais cheios.
 */
export function centavosDoColado(colado: string): string {
  const t = colado.replace(/[^\d.,]/g, "");
  const centavos = (inteiro: string, frac: string): string => `${inteiro.replace(/\D/g, "")}${frac.replace(/\D/g, "").padEnd(2, "0").slice(0, 2)}`;
  const virgula = t.lastIndexOf(",");
  if (virgula >= 0) return centavos(t.slice(0, virgula), t.slice(virgula + 1));
  const ponto = t.lastIndexOf(".");
  if (ponto >= 0 && /^\d{1,2}$/.test(t.slice(ponto + 1))) return centavos(t.slice(0, ponto), t.slice(ponto + 1));
  return centavos(t, "");
}

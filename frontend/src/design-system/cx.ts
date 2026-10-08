/** Junta nomes de classe ignorando valores vazios. */
export function cx(...partes: Array<string | false | null | undefined>): string {
  return partes.filter(Boolean).join(" ");
}

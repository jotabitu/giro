/** Vai para o cursor com a página que ele representa. Cursor nulo é a primeira página. */
export type AoIrPagina = (cursor: string | null, pagina: number) => void;

/**
 * Número da página mostrado entre "Anterior" e "Próxima". A API pagina só por cursor e não devolve o número:
 * ele é estado de navegação. Só passa de 1 quando há cursor; sem cursor (ou com número inválido) é a primeira.
 */
export function paginaDoCursor(cursor: string | null | undefined, pagina: string | number | null | undefined): number {
  if (!cursor) return 1;
  const n = Number(pagina);
  return Number.isInteger(n) && n > 1 ? n : 1;
}

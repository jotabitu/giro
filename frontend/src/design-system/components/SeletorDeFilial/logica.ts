// Regras do seletor de filial sem DOM, para testar sem navegador.

export const TODAS = "todas";

export type OpcaoFilial = { id: string; nome: string; cidade: string };

export type ItemSeletor = { id: string; nome: string; detalhe: string };

/** Lista do seletor: "Todas as filiais" primeiro, quando a pessoa pode (administrador, USR-07). */
export function montarItens(filiais: ReadonlyArray<OpcaoFilial>, permiteTodas: boolean): ItemSeletor[] {
  const itens = filiais.map((f) => ({ id: f.id, nome: f.nome, detalhe: f.cidade }));
  if (!permiteTodas) return itens;
  const n = filiais.length;
  return [{ id: TODAS, nome: "Todas as filiais", detalhe: n === 1 ? "1 filial" : `${n} filiais` }, ...itens];
}

/** USR-07 e README da Sidebar: com uma filial só (e sem "Todas"), o seletor nem aparece. */
export function deveMostrar(filiais: ReadonlyArray<OpcaoFilial>, permiteTodas: boolean): boolean {
  return montarItens(filiais, permiteTodas).length > 1;
}

/** Item que o botão mostra como ativo; id desconhecido cai no primeiro. */
export function itemAtivo(itens: ReadonlyArray<ItemSeletor>, valor: string): ItemSeletor | undefined {
  return itens.find((i) => i.id === valor) ?? itens[0];
}

/** Destino das setas, Home e End dentro da lista; null quando a tecla não navega. Não dá a volta. */
export function destinoNaLista(tecla: string, atual: number, total: number): number | null {
  switch (tecla) {
    case "ArrowDown":
      return Math.min(atual + 1, total - 1);
    case "ArrowUp":
      return Math.max(atual - 1, 0);
    case "Home":
      return 0;
    case "End":
      return total - 1;
    default:
      return null;
  }
}

/** Estado da lista de sugestões: aberta ou não e a opção em foco (-1: nenhuma, o texto digitado vale). */
export type EstadoDasSugestoes = { aberto: boolean; indice: number };

export const FECHADO: EstadoDasSugestoes = { aberto: false, indice: -1 };

/** O que a tecla faz: o estado novo, se a opção em foco foi escolhida e se a tecla é da lista (o campo não a usa). */
export type ResultadoDaTecla = { estado: EstadoDasSugestoes; escolher: number | null; daLista: boolean };

/** Focar ou digitar abre a lista sem opção em foco: digitar livre continua valendo. */
export function aoDigitar(): EstadoDasSugestoes {
  return { aberto: true, indice: -1 };
}

/**
 * Teclado do campo com sugestões. Seta para baixo abre e desce; seta para cima abre e sobe; Home e End
 * vão às pontas; Enter escolhe a opção em foco (sem opção em foco, o Enter segue para o formulário);
 * Escape fecha (fechada, segue para quem está em volta); Tab fecha. Não dá a volta na lista.
 */
export function aoTeclar(estado: EstadoDasSugestoes, tecla: string, total: number): ResultadoDaTecla {
  const ficar = { estado, escolher: null, daLista: false };
  switch (tecla) {
    case "ArrowDown":
      if (total === 0) return ficar;
      return { estado: { aberto: true, indice: estado.aberto ? Math.min(estado.indice + 1, total - 1) : 0 }, escolher: null, daLista: true };
    case "ArrowUp":
      if (total === 0) return ficar;
      return { estado: { aberto: true, indice: estado.aberto && estado.indice >= 0 ? Math.max(estado.indice - 1, 0) : total - 1 }, escolher: null, daLista: true };
    case "Home":
    case "End":
      if (!estado.aberto || total === 0 || estado.indice < 0) return ficar;
      return { estado: { aberto: true, indice: tecla === "Home" ? 0 : total - 1 }, escolher: null, daLista: true };
    case "Enter":
      if (!estado.aberto || estado.indice < 0 || estado.indice >= total) return ficar;
      return { estado: FECHADO, escolher: estado.indice, daLista: true };
    case "Escape":
      // Sem opção nenhuma, a lista nem aparece: o Escape é de quem está em volta (a gaveta, o diálogo).
      if (!estado.aberto || total === 0) return ficar;
      return { estado: FECHADO, escolher: null, daLista: true };
    case "Tab":
      return { estado: FECHADO, escolher: null, daLista: false };
    default:
      return ficar;
  }
}

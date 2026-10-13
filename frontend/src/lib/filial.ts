// Escolha da filial do app (USR-07, docs/api/filiais.md): a lista vem de /filiais/minhas/ e a escolha vai em `X-Filial`.
// Sem DOM, para testar sem navegador.
import { TODAS } from "@/design-system";
import type { MinhasFiliais } from "@/lib/api/tipos";

export { TODAS };

/** Escolha válida para esta lista: a guardada, se ainda vale; senão a matriz, ou a primeira (o mesmo padrão da API sem cabeçalho). `null` = pessoa sem filial. */
export function escolhaValida(minhas: MinhasFiliais, guardada: string | null): string | null {
  const ids = minhas.resultados.map((f) => String(f.id));
  if (guardada === TODAS && minhas.pode_escolher_todas) return TODAS;
  if (guardada && ids.includes(guardada)) return guardada;
  const padrao = minhas.resultados.find((f) => f.matriz) ?? minhas.resultados[0];
  return padrao ? String(padrao.id) : null;
}

/** Nome para o cabeçalho das telas ("Todas as filiais" ou o nome da filial). */
export function nomeDaEscolha(minhas: MinhasFiliais, escolha: string | null): string | null {
  if (escolha === TODAS) return "Todas as filiais";
  return minhas.resultados.find((f) => String(f.id) === escolha)?.nome ?? null;
}

const chaveGuardada = (usuarioId: number) => `giro:filial:${usuarioId}`;

/** A escolha fica no navegador, por pessoa; storage bloqueado ou vazio não derruba nada. */
export function lerEscolhaGuardada(usuarioId: number): string | null {
  try {
    return window.localStorage.getItem(chaveGuardada(usuarioId));
  } catch {
    return null;
  }
}

export function guardarEscolha(usuarioId: number, escolha: string): void {
  try {
    window.localStorage.setItem(chaveGuardada(usuarioId), escolha);
  } catch {
    /* sem storage: vale só até recarregar */
  }
}

/** Consultas que não dependem da filial e ficam de pé quando ela muda. */
const SEM_FILIAL = new Set(["eu", "filiais-minhas", "marca"]);
export const dependeDaFilial = (chave: readonly unknown[]): boolean => !SEM_FILIAL.has(String(chave[0]));

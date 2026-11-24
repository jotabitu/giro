import type { ReactNode } from "react";
import { cx } from "../../cx";

/**
 * Lista que cresce sem limite dentro de um painel (T-510): o bloco tem altura máxima e só rola depois dela.
 * Lista curta não ganha espaço vazio. O título do painel e a ação do cabeçalho ficam fora da rolagem; numa tabela, o
 * `thead` fica preso no topo. A região é focável (teclado rola com as setas) e leva o rótulo para o leitor de tela.
 * No celular a rolagem encadeia: ao chegar ao fim da lista, o dedo continua rolando a página.
 */
export function ListaComRolagem({ rotulo, className, children }: { rotulo: string; className?: string; children: ReactNode }) {
  return (
    <div role="region" aria-label={rotulo} tabIndex={0} className={cx("wl-rolagem", className)}>
      {children}
    </div>
  );
}

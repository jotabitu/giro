"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { cx } from "../../cx";

export type ColunaTabela<L> = {
  chave: string;
  titulo: string;
  /** Como mostrar a célula. Sem isso, usa linha[chave]. */
  celula?: (linha: L) => ReactNode;
  /** Placa, código ou data curta (Geist Mono). */
  mono?: boolean;
};

/** Célula com duas informações: principal (nome do veículo) e secundária (cliente, cidade). */
export function CelulaDupla({ principal, secundaria }: { principal: ReactNode; secundaria: ReactNode }) {
  return (
    <>
      <span className="wl-cell-main">{principal}</span>
      <span className="wl-cell-sub">{secundaria}</span>
    </>
  );
}

export function DataTable<L extends Record<string, unknown>>({
  colunas,
  linhas,
  chaveDaLinha,
  aoAbrir,
  legenda,
}: {
  colunas: ReadonlyArray<ColunaTabela<L>>;
  linhas: ReadonlyArray<L>;
  chaveDaLinha: (linha: L) => string;
  /** Linha inteira clicável abre o detalhe. Ações destrutivas nunca ficam na linha. */
  aoAbrir?: (linha: L) => void;
  /** Descrição para leitores de tela. */
  legenda?: string;
}) {
  const aoTeclar = (e: KeyboardEvent<HTMLTableRowElement>, linha: L) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      aoAbrir?.(linha);
    }
  };
  return (
    <table className="wl-table wl-table--cards" aria-label={legenda}>
      <thead>
        <tr>
          {colunas.map((c) => (
            <th key={c.chave} scope="col">
              {c.titulo}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {linhas.map((linha) => (
          <tr
            key={chaveDaLinha(linha)}
            data-clicavel={aoAbrir ? "" : undefined}
            tabIndex={aoAbrir ? 0 : undefined}
            onClick={aoAbrir ? () => aoAbrir(linha) : undefined}
            onKeyDown={aoAbrir ? (e) => aoTeclar(e, linha) : undefined}
          >
            {colunas.map((c) => (
              <td key={c.chave} data-label={c.titulo} className={cx(c.mono && "wl-mono")}>
                {c.celula ? c.celula(linha) : (linha[c.chave] as ReactNode)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

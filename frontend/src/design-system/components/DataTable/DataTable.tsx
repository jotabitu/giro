"use client";

import { ArrowDown, ChevronsUpDown } from "lucide-react";
import type { KeyboardEvent, ReactNode } from "react";
import { cx } from "../../cx";
import { Icone } from "../../Icone";

export type ColunaTabela<L> = {
  chave: string;
  titulo: string;
  /** Como mostrar a célula. Sem isso, usa linha[chave]. */
  celula?: (linha: L) => ReactNode;
  /** Placa, código ou data curta (Geist Mono). */
  mono?: boolean;
  /**
   * Coluna ordenável (T-486, "Em estoque" da Frota): o título vira botão, e o `th` leva `aria-sort`. A ordem é da API;
   * a tabela só pede a troca.
   */
  ordem?: { estado: "descending" | "none"; rotulo: string; aoOrdenar: () => void };
};

function TituloOrdenavel({ titulo, ordem }: { titulo: string; ordem: NonNullable<ColunaTabela<unknown>["ordem"]> }) {
  return (
    <button
      type="button"
      onClick={ordem.aoOrdenar}
      aria-label={ordem.rotulo}
      className="inline-flex cursor-pointer items-center gap-1 border-0 bg-transparent p-0 font-[inherit] text-[inherit]"
    >
      {titulo}
      <Icone de={ordem.estado === "descending" ? ArrowDown : ChevronsUpDown} className="h-3.5 w-3.5" />
    </button>
  );
}

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
            <th key={c.chave} scope="col" aria-sort={c.ordem?.estado}>
              {c.ordem ? <TituloOrdenavel titulo={c.titulo} ordem={c.ordem} /> : c.titulo}
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

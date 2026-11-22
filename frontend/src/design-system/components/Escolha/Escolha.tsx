"use client";

import type { KeyboardEvent } from "react";

export type OpcaoDeEscolha = {
  valor: string;
  titulo: string;
  /** Linha de apoio abaixo do título ("Pix ou TED"). */
  apoio?: string;
};

export type EscolhaProps = {
  opcoes: OpcaoDeEscolha[];
  valor: string;
  aoMudar: (valor: string) => void;
  /** Nome acessível do grupo ("Forma de pagamento"). */
  rotulo: string;
  desabilitado?: boolean;
};

/** Opções que se excluem, em cartões: a forma de pagamento da venda. Controlado; setas movem a escolha. */
export function Escolha({ opcoes, valor, aoMudar, rotulo, desabilitado = false }: EscolhaProps) {
  function aoTeclar(e: KeyboardEvent<HTMLButtonElement>, indice: number) {
    const passo = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!passo) return;
    e.preventDefault();
    const proxima = opcoes[(indice + passo + opcoes.length) % opcoes.length];
    if (!proxima) return;
    aoMudar(proxima.valor);
    const botoes = e.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>("[role=radio]");
    botoes?.[(indice + passo + opcoes.length) % opcoes.length]?.focus();
  }

  return (
    <div className="wl-choice" role="radiogroup" aria-label={rotulo}>
      {opcoes.map((o, i) => {
        const marcada = o.valor === valor;
        return (
          <button
            key={o.valor}
            type="button"
            role="radio"
            className="wl-choice__item"
            aria-checked={marcada}
            tabIndex={marcada || (!opcoes.some((x) => x.valor === valor) && i === 0) ? 0 : -1}
            disabled={desabilitado}
            onClick={() => aoMudar(o.valor)}
            onKeyDown={(e) => aoTeclar(e, i)}
          >
            <span style={{ fontWeight: 500 }}>{o.titulo}</span>
            {o.apoio ? <small>{o.apoio}</small> : null}
          </button>
        );
      })}
    </div>
  );
}

import type { ReactNode } from "react";

/** Lista de linhas dentro de um painel. `rotulo` nomeia a lista para o leitor de tela. */
export function ListaDeLinhas({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <ul aria-label={rotulo} className="wl-linhas">
      {children}
    </ul>
  );
}

/** Linha de lista: título, apoio opcional e ação à direita (botão ou link compacto). */
export function LinhaDeLista({ titulo, apoio, acao }: { titulo: ReactNode; apoio?: ReactNode; acao?: ReactNode }) {
  return (
    <li className="wl-linha">
      <div className="wl-linha__texto">
        <div className="wl-linha__titulo">{titulo}</div>
        {apoio && <div className="wl-linha__apoio">{apoio}</div>}
      </div>
      {acao && <div className="wl-linha__acao">{acao}</div>}
    </li>
  );
}

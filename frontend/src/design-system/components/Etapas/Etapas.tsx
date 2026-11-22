import type { ReactNode } from "react";

export type EstadoDaEtapa = "feita" | "atual" | "pendente";

export type Etapa = {
  titulo: string;
  /** Data, quem fez ou o que falta ("Aguardando pagamento"). O estado nunca depende só do marcador. */
  texto?: string;
  estado: EstadoDaEtapa;
  /** Botões do passo (`Button` pequeno), como "Copiar link para assinar". */
  acoes?: ReactNode;
};

/** Linha do tempo vertical de um processo: assinatura e entrada da venda. Mais de um passo pode ser atual. */
export function Etapas({ etapas, rotulo }: { etapas: Etapa[]; rotulo: string }) {
  return (
    <ol className="wl-steps" aria-label={rotulo}>
      {etapas.map((e) => (
        <li key={e.titulo} data-state={e.estado === "feita" ? "done" : undefined} aria-current={e.estado === "atual" ? "step" : undefined}>
          <span className="wl-steps__title">{e.titulo}</span>
          {e.texto ? <span className="wl-steps__text">{e.texto}</span> : null}
          {e.acoes ? <div className="wl-steps__acts">{e.acoes}</div> : null}
        </li>
      ))}
    </ol>
  );
}

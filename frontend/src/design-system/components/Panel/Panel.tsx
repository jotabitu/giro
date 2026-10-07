import type { ReactNode } from "react";

/** Painel surface com radius-xl: todo conteúdo da tela fica em painéis. Apoio dos demais componentes. */
export function Panel({
  titulo,
  subtitulo,
  acao,
  children,
}: {
  titulo?: ReactNode;
  subtitulo?: ReactNode;
  /** Normalmente um IconButton ou SegmentedControl, à direita do título. */
  acao?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="wl-panel">
      {(titulo || acao) && (
        <div className="wl-panel__head">
          <div>
            {titulo && <h2 className="wl-panel__title">{titulo}</h2>}
            {subtitulo && <p className="wl-panel__sub">{subtitulo}</p>}
          </div>
          {acao}
        </div>
      )}
      {children}
    </section>
  );
}

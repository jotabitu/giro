import type { ReactNode } from "react";
import { cx } from "../../cx";

/** Painel surface com radius-xl: todo conteúdo da tela fica em painéis. Apoio dos demais componentes. */
export function Panel({
  titulo,
  subtitulo,
  acao,
  className,
  children,
}: {
  titulo?: ReactNode;
  subtitulo?: ReactNode;
  /** Normalmente um IconButton ou SegmentedControl, à direita do título. */
  acao?: ReactNode;
  /** Ajuste de layout da página (altura, posição); a aparência fica no `wl-panel`. */
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cx("wl-panel", className)}>
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

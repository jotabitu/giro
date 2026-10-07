import type { ReactNode } from "react";
import { cx } from "../../cx";

export function KpiTile({
  rotulo,
  valor,
  contexto,
  destaque,
}: {
  rotulo: string;
  /** Já formatado em pt-BR (R$ 4.380, 71%). O frontend não calcula. */
  valor: string;
  /** Linha que explica o número. Variação com seta e texto: use <KpiVariacao>. */
  contexto?: ReactNode;
  /** O número mais importante da tela, em solid. Nunca dois lado a lado. */
  destaque?: boolean;
}) {
  return (
    <div className={cx("wl-kpi", destaque && "wl-kpi--solid")}>
      <div className="wl-kpi__label">{rotulo}</div>
      <div className="wl-kpi__value">{valor}</div>
      {contexto && <div className="wl-kpi__meta">{contexto}</div>}
    </div>
  );
}

export function KpiVariacao({ children }: { children: ReactNode }) {
  return <span className="wl-kpi__up">{children}</span>;
}

/** Grade de quatro indicadores (duas colunas em tela estreita). */
export function KpiGrid({ children }: { children: ReactNode }) {
  return <div className="wl-kpis">{children}</div>;
}

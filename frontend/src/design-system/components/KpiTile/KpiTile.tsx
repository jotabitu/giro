import type { CSSProperties, ReactNode } from "react";
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
      {/* --chars deixa o CSS encolher o número até caber no bloco, em vez de estourar ou cortar. */}
      <div className="wl-kpi__value" style={{ "--chars": Math.max(valor.length, 1) } as CSSProperties}>
        {valor}
      </div>
      {contexto && <div className="wl-kpi__meta">{contexto}</div>}
    </div>
  );
}

export function KpiVariacao({ children }: { children: ReactNode }) {
  return <span className="wl-kpi__up">{children}</span>;
}

/** Grade de quatro indicadores (duas colunas em tela estreita). */
/** `colunas` só quando há menos cartões que as 4 colunas do padrão (ex.: ficha do veículo sem os indicadores financeiros): a fileira não deixa lugar vazio. */
export function KpiGrid({ children, colunas }: { children: ReactNode; colunas?: number }) {
  return (
    <div className="wl-kpis" style={colunas ? { gridTemplateColumns: `repeat(${colunas}, minmax(0, 1fr))` } : undefined}>
      {children}
    </div>
  );
}

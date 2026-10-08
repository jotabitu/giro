import type { ReactNode } from "react";
import { cx } from "../../cx";

/**
 * Cada tom é um grupo de status; estado novo entra num grupo, não ganha cor própria.
 * neutro: Em preparação, Vendido, prioridade Baixa. solido: Alugado. alta: prioridade Alta.
 * atencao: em andamento que pede olhar (Em vistoria). marca: resumo de alertas no topo.
 */
export type TomStatus =
  | "neutro"
  | "sucesso"
  | "info"
  | "alerta"
  | "critico"
  | "alta"
  | "atencao"
  | "solido"
  | "marca"
  | "superficie";

const CLASSE: Record<TomStatus, string | false> = {
  neutro: false,
  sucesso: "wl-badge--success",
  info: "wl-badge--info",
  alerta: "wl-badge--warning",
  critico: "wl-badge--critical",
  alta: "wl-badge--high",
  atencao: "wl-badge--attention",
  solido: "wl-badge--solid",
  marca: "wl-badge--brand",
  superficie: "wl-badge--surface",
};

export function StatusBadge({
  tom = "neutro",
  compacto,
  ponto,
  icone,
  children,
}: {
  tom?: TomStatus;
  /** 26px, para tabelas densas. */
  compacto?: boolean;
  /** Ponto antes do texto (estado em andamento). */
  ponto?: boolean;
  icone?: ReactNode;
  /** O significado está sempre no texto; a cor só reforça. */
  children: ReactNode;
}) {
  return (
    <span className={cx("wl-badge", CLASSE[tom], compacto && "wl-badge--sm")}>
      {ponto && <span className="wl-badge__dot" aria-hidden="true" />}
      {icone}
      {children}
    </span>
  );
}

/** Contador neutro do menu e de abas. */
export function Contador({ children }: { children: ReactNode }) {
  return <span className="wl-count">{children}</span>;
}

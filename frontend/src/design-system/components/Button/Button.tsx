import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "../../cx";

export type VarianteBotao = "solido" | "marca" | "padrao" | "quieto";

export type BotaoProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className"> & {
  /** solido: ação principal (uma por área). marca: destaque em card escuro. padrao: sobre o canvas. quieto: dentro de painel. */
  variante?: VarianteBotao;
  /** Compacto de 36px, para tabelas e cards. */
  compacto?: boolean;
  /** Ícone de 20px antes do texto (use <Icone />). */
  icone?: ReactNode;
};

const CLASSE: Record<VarianteBotao, string | false> = {
  solido: "wl-btn--solid",
  marca: "wl-btn--brand",
  padrao: false,
  quieto: "wl-btn--quiet",
};

export function Button({ variante = "padrao", compacto, icone, type = "button", children, ...resto }: BotaoProps) {
  return (
    <button type={type} className={cx("wl-btn", CLASSE[variante], compacto && "wl-btn--sm")} {...resto}>
      {icone}
      {children}
    </button>
  );
}

export type BotaoIconeProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className" | "aria-label"> & {
  /** Obrigatório: o botão não tem texto. */
  "aria-label": string;
  icone: ReactNode;
  /** Fundo surface-sunken, para uso dentro de painéis. */
  quieto?: boolean;
  /** 40px em vez de 48px. */
  compacto?: boolean;
  /** Ponto crítico de notificação. */
  notificacao?: boolean;
};

export function IconButton({ icone, quieto, compacto, notificacao, type = "button", ...resto }: BotaoIconeProps) {
  return (
    <button type={type} className={cx("wl-icon-btn", quieto && "wl-icon-btn--sunken", compacto && "wl-icon-btn--sm")} {...resto}>
      {icone}
      {notificacao && <span className="wl-notify" aria-hidden="true" />}
    </button>
  );
}

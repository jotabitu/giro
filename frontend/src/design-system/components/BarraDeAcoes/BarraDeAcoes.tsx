import Link from "next/link";
import type { ReactNode } from "react";
import { cx } from "../../cx";

export type PrincipalDaBarra = {
  /** Texto do botão: o que a tela já usa ("Cadastrar veículo", "Salvar alterações"). */
  rotulo: string;
  /** Id do form que o botão envia. Obrigatório quando a barra fica fora do `<form>`; sem `aoClicar`, vira `type="submit"`. */
  form?: string;
  /** Mostra `textoOcupado` e desabilita o botão. */
  ocupado?: boolean;
  /** Padrão: "Salvando…". */
  textoOcupado?: string;
  disabled?: boolean;
  /** Para a tela que não envia um form. */
  aoClicar?: () => void;
};

export type CancelarDaBarra = { rotulo?: string; /** Só vale com `aoClicar`: o cancelar que desfaz alterações fica inativo sem nada para desfazer. */ disabled?: boolean } & ({ href: string; aoClicar?: never } | { href?: never; aoClicar: () => void });

/**
 * Barra flutuante de ações no pé de uma tela de página inteira que cria ou edita (T-514): cartão branco com sombra,
 * fixo ao rolar, "Cancelar" quieto e o botão principal sólido à direita. No celular fica acima da barra de navegação
 * de baixo (`bottom-[88px]`). A barra fica no fim do conteúdo da página, então nada fica escondido atrás dela.
 */
export function BarraDeAcoes({ aEsquerda, cancelar, principal, className }: { aEsquerda?: ReactNode; cancelar: CancelarDaBarra; principal: PrincipalDaBarra; className?: string }) {
  const rotuloCancelar = cancelar.rotulo ?? "Cancelar";
  return (
    <div className={cx("sticky bottom-[88px] z-20 flex flex-wrap items-center gap-2 rounded-lg bg-surface p-3 shadow-pop md:bottom-4", className)}>
      {aEsquerda && <div className="min-w-0 basis-full text-caption text-ink-muted md:flex-1 md:basis-0">{aEsquerda}</div>}
      <div className="ml-auto flex shrink-0 gap-2">
        {cancelar.href !== undefined ? (
          <Link href={cancelar.href} className="wl-btn wl-btn--quiet">
            {rotuloCancelar}
          </Link>
        ) : (
          <button type="button" disabled={cancelar.disabled} className="wl-btn wl-btn--quiet" onClick={cancelar.aoClicar}>
            {rotuloCancelar}
          </button>
        )}
        <button
          type={principal.aoClicar ? "button" : "submit"}
          form={principal.form}
          disabled={principal.ocupado || principal.disabled}
          onClick={principal.aoClicar}
          className="wl-btn wl-btn--solid"
        >
          {principal.ocupado ? (principal.textoOcupado ?? "Salvando…") : principal.rotulo}
        </button>
      </div>
    </div>
  );
}

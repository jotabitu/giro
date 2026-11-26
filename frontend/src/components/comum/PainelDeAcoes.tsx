import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Painel "Ações" no topo da coluna lateral das fichas (veículo e cliente): cada ação numa linha com ícone, nome e uma explicação curta.
 * As de perigo ficam por último, depois de uma linha, em vermelho. No topo da ficha ficam só "Editar" e a ação principal.
 */
export function PainelDeAcoes({ children }: { children: ReactNode }) {
  return (
    <section className="wl-panel">
      <h2 className="text-[20px] font-semibold leading-[26px]">Ações</h2>
      <div className="wl-acoes-lista">{children}</div>
    </section>
  );
}

export function SeparadorDeAcoes() {
  return <div className="wl-acoes-sep" role="separator" />;
}

type Linha = {
  rotulo: string;
  detalhe: string;
  icone: ReactNode;
  href?: string;
  externo?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  perigo?: boolean;
};

export function LinhaDeAcao({ rotulo, detalhe, icone, href, externo, onClick, disabled, title, perigo }: Linha) {
  const classe = perigo ? "wl-acao wl-acao--perigo" : "wl-acao";
  const miolo = (
    <>
      <span className="wl-acao__ic" aria-hidden="true">
        {icone}
      </span>
      <span>
        {rotulo}
        <small aria-hidden="true">{detalhe}</small>
      </span>
    </>
  );
  if (href && !disabled) {
    return externo ? (
      <a href={href} target="_blank" rel="noreferrer" className={classe} aria-label={rotulo}>
        {miolo}
      </a>
    ) : (
      <Link href={href} className={classe} aria-label={rotulo}>
        {miolo}
      </Link>
    );
  }
  return (
    <button type="button" className={classe} aria-label={rotulo} onClick={onClick} disabled={disabled} title={title}>
      {miolo}
    </button>
  );
}

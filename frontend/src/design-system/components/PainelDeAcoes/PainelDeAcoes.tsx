import Link from "next/link";
import { useId, type ReactNode } from "react";

/**
 * Painel "Ações" no topo da coluna lateral das fichas (veículo e cliente): cada ação numa linha com ícone, nome e uma explicação curta.
 * As de perigo ficam por último, depois de um `SeparadorDeAcoes`, em vermelho. No topo da ficha ficam só "Editar" e a ação principal.
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

export type LinhaDeAcaoProps = {
  rotulo: string;
  /** Explicação curta. Numa ação desligada, é o motivo: fica visível e é lida como descrição. */
  detalhe: string;
  icone: ReactNode;
  href?: string;
  externo?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  perigo?: boolean;
};

/** Nome acessível = `rotulo` (aria-labelledby); `detalhe` entra como descrição (aria-describedby). Sem aria-label, que sobrescreveria o texto. */
export function LinhaDeAcao({ rotulo, detalhe, icone, href, externo, onClick, disabled, title, perigo }: LinhaDeAcaoProps) {
  const id = useId();
  const idNome = `${id}-nome`;
  const idDetalhe = `${id}-detalhe`;
  const classe = perigo ? "wl-acao wl-acao--perigo" : "wl-acao";
  const ligacao = { "aria-labelledby": idNome, "aria-describedby": idDetalhe };
  const miolo = (
    <>
      <span className="wl-acao__ic" aria-hidden="true">
        {icone}
      </span>
      <span>
        <span id={idNome} className="wl-acao__nome">
          {rotulo}
        </span>
        <small id={idDetalhe}>{detalhe}</small>
      </span>
    </>
  );
  if (href && !disabled) {
    return externo ? (
      <a href={href} target="_blank" rel="noreferrer" className={classe} {...ligacao}>
        {miolo}
      </a>
    ) : (
      <Link href={href} className={classe} {...ligacao}>
        {miolo}
      </Link>
    );
  }
  return (
    <button type="button" className={classe} {...ligacao} onClick={onClick} disabled={disabled} title={title}>
      {miolo}
    </button>
  );
}

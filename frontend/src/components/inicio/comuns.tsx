import type { ReactNode } from "react";
import { KpiGrid, KpiTile, KpiVariacao } from "@/design-system";
import type { Kpi } from "@/lib/api";
import { formatarValor } from "@/lib/painel";

/** Indicadores do painel. Cartão com `valor: null` é de módulo que ainda não existe e não aparece (USR-08). */
export function KpisDoPainel({ kpis }: { kpis: Kpi[] }) {
  return (
    <KpiGrid>
      {(kpis ?? []).flatMap((k) =>
        !k.valor
          ? []
          : [
              <KpiTile
                key={k.chave}
                rotulo={k.rotulo}
                valor={formatarValor(k.valor)}
                destaque={k.destaque}
                contexto={k.contexto ? k.tendencia === "sobe" ? <KpiVariacao>↗ {k.contexto}</KpiVariacao> : k.contexto : undefined}
              />,
            ],
      )}
    </KpiGrid>
  );
}

export function CabecalhoInicio({ saudacao, subtitulo, children }: { saudacao: string; subtitulo?: string; children?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-center gap-x-6 gap-y-3">
      <div>
        <h1 className="text-title md:text-display">{saudacao}</h1>
        {subtitulo && <p className="text-caption text-ink-muted">{subtitulo}</p>}
      </div>
      {children && <div className="flex w-full flex-wrap items-center gap-3 md:ml-auto md:w-auto">{children}</div>}
    </header>
  );
}

export function Vazio({ children }: { children: ReactNode }) {
  return <p className="text-body text-ink-muted">{children}</p>;
}

/** Linhas de lista dentro de um painel: texto principal, apoio e ação à direita. */
export function ListaDoPainel({ children, rotulo }: { children: ReactNode; rotulo: string }) {
  return (
    <ul aria-label={rotulo} className="flex flex-col">
      {children}
    </ul>
  );
}

export function LinhaDoPainel({ titulo, apoio, fim }: { titulo: ReactNode; apoio?: ReactNode; fim?: ReactNode }) {
  return (
    <li className="flex min-h-[56px] items-center justify-between gap-3 border-b border-line py-3 last:border-b-0">
      <div className="min-w-0">
        <div className="text-body-strong">{titulo}</div>
        {apoio && <div className="text-caption text-ink-muted">{apoio}</div>}
      </div>
      {fim && <div className="shrink-0">{fim}</div>}
    </li>
  );
}

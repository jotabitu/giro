import type { ReactNode } from "react";
import { CabecalhoMarca, RodapeGiro } from "./CabecalhoMarca";

/** Página de acesso de uma coluna (convite, esqueci a senha, 2 etapas): cabeçalho da empresa, conteúdo em painéis, rodapé. */
export function PaginaAcesso({ titulo, descricao, children }: { titulo: string; descricao?: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col gap-6 bg-canvas p-4 md:p-8">
      <CabecalhoMarca />
      <div className="mx-auto flex w-full max-w-[720px] flex-1 flex-col gap-6">
        <div>
          <h1 className="text-title md:text-display">{titulo}</h1>
          {descricao && <p className="mt-2 text-body text-ink-muted">{descricao}</p>}
        </div>
        {children}
      </div>
      <RodapeGiro />
    </div>
  );
}

export function Passo({ numero, titulo, children }: { numero: number | ReactNode; titulo: string; children: ReactNode }) {
  return (
    <section className="wl-panel flex flex-col gap-4">
      <h2 className="flex items-center gap-3 text-heading">
        <span className="grid size-8 place-items-center rounded-full bg-surface-sunken text-caption">{numero}</span>
        {titulo}
      </h2>
      {children}
    </section>
  );
}

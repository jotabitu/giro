"use client";

import { Contador } from "@/design-system";

export type OpcaoChip = { valor: string; rotulo: string; contagem?: number | null };

/**
 * Filtro por situação em chips com contagem (Frota e Clientes). Não existe no design system
 * (pedido na T-046 como "FiltroChips"); quando existir, trocar por ele.
 * A contagem vem da API; sem contagem, o chip não mostra número.
 */
export function FiltroChips({ rotulo, opcoes, valor, aoMudar }: { rotulo: string; opcoes: OpcaoChip[]; valor: string; aoMudar: (v: string) => void }) {
  return (
    <div role="group" aria-label={rotulo} className="flex gap-2 overflow-x-auto pb-1">
      {opcoes.map((o) => {
        const ativo = o.valor === valor;
        return (
          <button
            key={o.valor}
            type="button"
            aria-pressed={ativo}
            onClick={() => aoMudar(o.valor)}
            className={`inline-flex h-[44px] shrink-0 items-center gap-2 rounded-pill px-4 text-body whitespace-nowrap md:h-10 ${ativo ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
          >
            {o.rotulo}
            {typeof o.contagem === "number" && (
              <span className={ativo ? "[&_.wl-count]:!bg-brand [&_.wl-count]:!text-on-brand" : "[&_.wl-count]:!bg-surface"}>
                <Contador>{o.contagem}</Contador>
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

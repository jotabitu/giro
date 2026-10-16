"use client";

import { Clock, UserRound } from "lucide-react";
import Link from "next/link";
import { Button, Icone } from "@/design-system";
import type { LinhaDaMovimentacao } from "@/lib/api";
import { dinheiro, nomeCurto, placa } from "@/lib/formatos";
import { rotaDaChegada } from "@/lib/movimentacoes";

/**
 * Cartão do quadro (Movimentacoes-Desktop e Movimentacoes-Mobile). A rota, o resumo ("saiu 10:02 · 1 parada") e os botões
 * vêm da API: a tela mostra só o que `acoes` manda como verdadeiro (MOV-02, MOV-03).
 */
export function CartaoDaMovimentacao({ m, ocupado, aoIniciar, aoCancelar }: { m: LinhaDaMovimentacao; ocupado: boolean; aoIniciar: (m: LinhaDaMovimentacao) => void; aoCancelar: (m: LinhaDaMovimentacao) => void }) {
  const emTransito = m.status === "em_transito";
  const apoio = emTransito ? "text-on-solid-muted" : "text-ink-muted";
  return (
    <article aria-label={`${m.codigo} · ${m.veiculo.modelo}`} className={`flex flex-col gap-2 rounded-[20px] p-[14px] ${emTransito ? "bg-solid text-on-solid" : "bg-surface-sunken"}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-body font-semibold">{m.veiculo.modelo}</span>
        <span className={`wl-mono whitespace-nowrap text-caption ${apoio}`}>{m.codigo}</span>
      </div>
      <p className="m-0 text-caption">{m.rota}</p>
      <div className={`flex flex-wrap gap-x-3 gap-y-1 text-caption ${apoio}`}>
        <span className="wl-mono">{placa(m.veiculo.placa)}</span>
        <span className="inline-flex items-center gap-1">
          <Icone de={UserRound} />
          {nomeCurto(m.levado_por.nome)}
        </span>
        <span className="inline-flex items-center gap-1">
          <Icone de={Clock} />
          {m.resumo}
        </span>
      </div>
      <div className="mt-[2px] flex flex-wrap items-center gap-2">
        {m.acoes.iniciar && (
          <Button compacto variante="solido" disabled={ocupado} onClick={() => aoIniciar(m)}>
            Iniciar
          </Button>
        )}
        {m.acoes.registrar_chegada && (
          <Link href={rotaDaChegada(m.id)} className="wl-btn wl-btn--brand wl-btn--sm">
            Registrar chegada
          </Link>
        )}
        {m.acoes.cancelar && (
          <Button compacto variante="quieto" disabled={ocupado} onClick={() => aoCancelar(m)}>
            Cancelar
          </Button>
        )}
        {m.status === "concluida" && m.custo_centavos !== undefined && <b className="ml-auto whitespace-nowrap text-caption font-semibold">{dinheiro(m.custo_centavos)}</b>}
      </div>
    </article>
  );
}

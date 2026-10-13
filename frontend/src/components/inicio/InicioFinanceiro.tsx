"use client";

import Link from "next/link";
import { Panel, StatusBadge } from "@/design-system";
import type { InicioDe, StatusDoCaixa } from "@/lib/api";
import { dinheiro } from "@/lib/formatos";
import { diaDaSemanaEData, ROTULO_STATUS_DO_CAIXA, TOM_STATUS_DO_CAIXA } from "@/lib/financeiro";
import { hrefDoDestino } from "@/lib/menu";
import { CabecalhoInicio, KpisDoPainel, LinhaDoPainel, ListaDoPainel, Vazio } from "./comuns";

const ACAO = { reembolso: "Devolver", despesa: "Pagar" } as const;

/** Início do financeiro (USR-08): o que entra e sai hoje. Sem aprovações; saldo, fluxo e conciliação são fase 2. */
export function InicioFinanceiro({ d }: { d: InicioDe<"financeiro"> }) {
  // Bloco ou lista `null` não quebra a tela: `para_hoje` e `caixas_do_dia` sem conteúdo caem no estado vazio.
  const paraHoje = d.para_hoje ?? [];
  const caixas = d.caixas_do_dia ?? [];
  // O dia vem de `atualizado_em` (instante da API) no fuso da empresa; a tela só formata.
  const dia = new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo" }).format(new Date(d.atualizado_em));
  return (
    <div className="flex flex-col gap-6">
      <CabecalhoInicio saudacao={d.saudacao} subtitulo={`${diaDaSemanaEData(dia)} · todas as filiais`} />
      <KpisDoPainel kpis={d.kpis} />

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel titulo="Para hoje">
          {paraHoje.length === 0 ? (
            <Vazio>Nada para pagar ou devolver hoje.</Vazio>
          ) : (
            <ListaDoPainel rotulo="Para hoje">
              {paraHoje.map((t) => (
                <LinhaDoPainel
                  key={`${t.tipo}-${t.destino.id}`}
                  titulo={t.texto}
                  fim={
                    <Link href={hrefDoDestino(t.destino.chave, t.destino.filtro, t.destino.id) ?? "/inicio"} className="wl-btn wl-btn--quiet wl-btn--sm">
                      {ACAO[t.tipo]}
                    </Link>
                  }
                />
              ))}
            </ListaDoPainel>
          )}
        </Panel>

        <Panel titulo="Caixas do dia">
            {caixas.length === 0 ? (
              <Vazio>Nenhum caixa aberto hoje.</Vazio>
            ) : (
              <ListaDoPainel rotulo="Caixas do dia">
                {caixas.map((c) => (
                  <LinhaDoPainel
                    key={c.filial}
                    titulo={
                      <Link href="/financeiro/caixa" className="text-ink no-underline hover:underline">
                        {c.filial}
                      </Link>
                    }
                    apoio={`${c.aberto_por ? `Aberto por ${c.aberto_por} · ` : ""}esperado na gaveta ${dinheiro(c.esperado_gaveta_centavos)}`}
                    fim={
                      <StatusBadge tom={TOM_STATUS_DO_CAIXA[c.status as StatusDoCaixa] ?? "neutro"} compacto>
                        {ROTULO_STATUS_DO_CAIXA[c.status as StatusDoCaixa] ?? c.status}
                      </StatusBadge>
                    }
                  />
                ))}
              </ListaDoPainel>
            )}
        </Panel>
      </div>
    </div>
  );
}

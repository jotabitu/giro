"use client";

import Link from "next/link";
import { Panel, StatusBadge } from "@/design-system";
import type { InicioDe } from "@/lib/api";
import { dinheiro } from "@/lib/formatos";
import { hrefDoDestino } from "@/lib/menu";
import { CabecalhoInicio, KpisDoPainel, LinhaDoPainel, ListaDoPainel, Vazio } from "./comuns";

const STATUS_DO_CAIXA: Record<string, string> = { aberto: "Aberto", fechado: "Fechado", nao_aberto: "Não aberto" };
const ACAO = { reembolso: "Devolver", despesa: "Pagar" } as const;

/** Início do financeiro (USR-08): o que entra e sai hoje. Sem aprovações; saldo, fluxo e conciliação são fase 2. */
export function InicioFinanceiro({ d }: { d: InicioDe<"financeiro"> }) {
  return (
    <div className="flex flex-col gap-6">
      <CabecalhoInicio saudacao={d.saudacao} subtitulo="todas as filiais" />
      <KpisDoPainel kpis={d.kpis} />

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel titulo="Para hoje">
          {d.para_hoje.length === 0 ? (
            <Vazio>Nada para pagar ou devolver hoje.</Vazio>
          ) : (
            <ListaDoPainel rotulo="Para hoje">
              {d.para_hoje.map((t) => (
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

        {d.caixas_do_dia && (
          <Panel titulo="Caixas do dia">
            {d.caixas_do_dia.length === 0 ? (
              <Vazio>Nenhum caixa aberto hoje.</Vazio>
            ) : (
              <ListaDoPainel rotulo="Caixas do dia">
                {d.caixas_do_dia.map((c) => (
                  <LinhaDoPainel
                    key={c.filial}
                    titulo={c.filial}
                    apoio={`${c.aberto_por ? `Aberto por ${c.aberto_por} · ` : ""}esperado na gaveta ${dinheiro(c.esperado_gaveta_centavos)}`}
                    fim={
                      <StatusBadge tom={c.status === "aberto" ? "sucesso" : "neutro"} compacto>
                        {STATUS_DO_CAIXA[c.status] ?? c.status}
                      </StatusBadge>
                    }
                  />
                ))}
              </ListaDoPainel>
            )}
          </Panel>
        )}
      </div>
    </div>
  );
}

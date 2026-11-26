"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { Icone, Panel, StatusBadge } from "@/design-system";
import type { InicioDe } from "@/lib/api";
import { dataCurta, dinheiro } from "@/lib/formatos";
import { temNoMenu } from "@/lib/menu";
import { tomDoStatus } from "@/lib/painel";
import { useSessao } from "@/lib/sessao";
import { CabecalhoInicio, KpisDoPainel, LinhaDoPainel, ListaDoPainel, Vazio } from "./comuns";
import { PropostasDoVendedor } from "./PropostasDoVendedor";

/**
 * Início do vendedor (USR-08, fase 1: locação). "Meus" = locações que ele criou.
 * Meta, funil e comissão vêm `null` até o resumo de vendas da 1c (T-502) e não aparecem. As propostas para retornar
 * vêm da lista de vendas (T-503), para quem tem vendas no menu.
 */
export function InicioVendedor({ d }: { d: InicioDe<"vendedor"> }) {
  const { eu } = useSessao();
  const parcelas = d.parcelas_atrasadas ?? [];
  const precisamAcao = d.precisam_acao ?? [];
  const vende = eu.pode.vendas_criar && ["minhas_vendas", "propostas", "vendas"].some((c) => temNoMenu(eu.navegacao, c));
  return (
    <div className="flex flex-col gap-6">
      <CabecalhoInicio saudacao={d.saudacao}>
        {vende && (
          <Link href="/vendas/nova" className="wl-btn">
            <Icone de={Plus} />
            Nova proposta
          </Link>
        )}
        {eu.pode.locacoes_criar && (
          <Link href="/locacoes/nova" className="wl-btn wl-btn--solid">
            <Icone de={Plus} />
            Nova locação
          </Link>
        )}
      </CabecalhoInicio>

      <KpisDoPainel kpis={d.kpis} />

      {vende && <PropostasDoVendedor />}

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel titulo="Parcelas atrasadas" subtitulo="das suas locações">
          {parcelas.length === 0 ? (
            <Vazio>Nenhuma parcela atrasada nas suas locações.</Vazio>
          ) : (
            <ListaDoPainel rotulo="Parcelas atrasadas">
              {parcelas.map((p) => (
                <LinhaDoPainel
                  key={p.conta_id}
                  titulo={p.cliente}
                  apoio={
                    <>
                      <span className="wl-mono">{p.locacao}</span> · venceu {dataCurta(p.vencimento)} · {p.dias} {p.dias === 1 ? "dia" : "dias"} de atraso
                    </>
                  }
                  fim={
                    <div className="flex items-center gap-3">
                      <span className="wl-mono">{dinheiro(p.valor_centavos)}</span>
                      <Link href={`/financeiro/receber?conta=${p.conta_id}`} className="wl-btn wl-btn--quiet wl-btn--sm">
                        Cobrar
                      </Link>
                    </div>
                  }
                />
              ))}
            </ListaDoPainel>
          )}
        </Panel>

        <Panel titulo="Precisam de ação">
          {precisamAcao.length === 0 ? (
            <Vazio>Nenhuma locação sua pede ação agora.</Vazio>
          ) : (
            <ListaDoPainel rotulo="Locações que precisam de ação">
              {precisamAcao.map((l) => (
                <LinhaDoPainel
                  key={l.locacao_id}
                  titulo={l.cliente}
                  apoio={<span className="wl-mono">{l.codigo}</span>}
                  fim={
                    <Link href={`/locacoes/${l.locacao_id}`} className="inline-flex min-h-[44px] items-center">
                      <StatusBadge tom={tomDoStatus(l.situacao.tom)} compacto>
                        {l.situacao.rotulo}
                      </StatusBadge>
                    </Link>
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

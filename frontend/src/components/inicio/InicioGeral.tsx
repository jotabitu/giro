"use client";

import { ArrowUpRight, Plus, TriangleAlert } from "lucide-react";
import Link from "next/link";
import {
  AlertCard,
  CelulaDupla,
  DataTable,
  FleetBar,
  Icone,
  Panel,
  SearchField,
  SegmentedControl,
  StatusBadge,
  type ColunaTabela,
} from "@/design-system";
import type { InicioDe, PendenciaInicio, Periodo } from "@/lib/api";
import { dataCurta, dinheiro, placa } from "@/lib/formatos";
import { hrefDoDestino } from "@/lib/menu";
import { atualizadoHa, tomDoStatus } from "@/lib/painel";
import { useSessao } from "@/lib/sessao";
import { CabecalhoInicio, KpisDoPainel } from "./comuns";

type Linha = InicioDe<"geral">["devolucoes_semana"]["linhas"][number];

const COLUNAS: ColunaTabela<Linha>[] = [
  { chave: "placa", titulo: "Placa", mono: true, celula: (l) => placa(l.placa) },
  { chave: "veiculo", titulo: "Veículo e cliente", celula: (l) => <CelulaDupla principal={l.veiculo} secundaria={l.cliente} /> },
  { chave: "data", titulo: "Devolução", mono: true, celula: (l) => dataCurta(l.data) },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (l) => (
      <StatusBadge tom={tomDoStatus(l.situacao.tom)} compacto>
        {l.situacao.rotulo}
      </StatusBadge>
    ),
  },
];

/** Gravidade da API (`critica`, `alerta`, `info`) no vocabulário do AlertCard; `info` não leva marcação. */
const GRAVIDADE_DO_ALERTA: Record<PendenciaInicio["gravidade"], "critica" | "atencao" | undefined> = { critica: "critica", alerta: "atencao", info: undefined };

const DESTAQUE_DA_FROTA: Record<string, "marca" | "solido"> = { alugado: "marca", a_venda: "solido" };

/** Main: visão geral do administrador (USR-08, variante `geral`). Todos os números e textos vêm da API. */
export function InicioGeral({ d, periodo, aoMudarPeriodo }: { d: InicioDe<"geral">; periodo: Periodo; aoMudarPeriodo: (p: Periodo) => void }) {
  const { eu } = useSessao();
  const controlePeriodo = (
    <SegmentedControl
      rotulo="Período"
      valor={periodo}
      aoMudar={aoMudarPeriodo}
      opcoes={[
        { valor: "hoje", rotulo: "Hoje" },
        { valor: "7d", rotulo: "7 dias" },
        { valor: "30d", rotulo: "30 dias" },
      ]}
    />
  );
  const ha = atualizadoHa(d.atualizado_em);
  const caixa = d.caixa_hoje;
  // Blocos `null` da API não quebram a tela (USR-08): o que falta vira lista vazia.
  const segmentos = d.frota?.segmentos ?? [];
  const devolucoes = d.devolucoes_semana?.linhas ?? [];
  const pendencias = d.pendencias?.itens ?? [];

  return (
    <div className="flex flex-col gap-6">
      <CabecalhoInicio saudacao={d.saudacao}>
        {d.atencao && d.atencao.quantidade > 0 && (
          <StatusBadge tom="marca" icone={<Icone de={TriangleAlert} />}>
            {d.atencao.texto}
          </StatusBadge>
        )}
        <SearchField placeholder="Buscar placa, cliente ou contrato" />
        {eu.pode.locacoes_criar && (
          <Link href="/locacoes/nova" className="wl-btn wl-btn--solid">
            <Icone de={Plus} />
            Nova locação
          </Link>
        )}
      </CabecalhoInicio>

      <Panel titulo="Frota" subtitulo={`atualizado ${ha}`} acao={<div className="hidden md:block">{controlePeriodo}</div>}>
        <div className="flex flex-col gap-4">
          <div className="md:hidden">{controlePeriodo}</div>
          <KpisDoPainel kpis={d.kpis} />
          <FleetBar
            nota={d.frota?.nota ?? ""}
            segmentos={segmentos.map((s) => ({ chave: s.status, rotulo: s.rotulo, contagem: s.quantidade, destaque: DESTAQUE_DA_FROTA[s.status] }))}
          />
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel titulo="Devoluções da semana" subtitulo={d.devolucoes_semana?.subtitulo}>
          <DataTable colunas={COLUNAS} linhas={devolucoes} chaveDaLinha={(l) => l.codigo} legenda="Devoluções da semana" />
        </Panel>
        <div className="flex flex-col gap-6">
          <AlertCard
            atualizadoHa={ha}
            titulo={d.pendencias?.titulo ?? "Nenhum contrato precisa de ação hoje"}
            itens={pendencias.map((i) => ({ texto: i.texto, gravidade: GRAVIDADE_DO_ALERTA[i.gravidade] }))}
            acao={
              <Link href={hrefDoDestino("locacoes", "aba=precisam_acao") ?? "/locacoes"} className="wl-btn wl-btn--brand">
                Ver pendências
              </Link>
            }
          />
          {caixa && (
            <Panel
              titulo="Caixa de hoje"
              subtitulo={`${dataCurta(caixa.data)} · ${caixa.filial}`}
              acao={
                <Link href="/financeiro/caixa" aria-label="Abrir financeiro" className="wl-icon-btn wl-icon-btn--sunken wl-icon-btn--sm">
                  <Icone de={ArrowUpRight} />
                </Link>
              }
            >
              <div className="text-title">{dinheiro(caixa.saldo_dia_centavos)}</div>
              <div className="text-caption text-ink-muted">saldo do dia</div>
              <dl className="mt-4 flex flex-col">
                {[
                  ["Recebido", caixa.recebido_centavos],
                  ["A receber hoje", caixa.a_receber_hoje_centavos],
                  ["Despesas", caixa.despesas_centavos],
                ].map(([rotulo, centavos]) => (
                  <div key={rotulo} className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
                    <dt className="text-ink-muted">{rotulo}</dt>
                    <dd className="wl-mono">{dinheiro(Number(centavos))}</dd>
                  </div>
                ))}
              </dl>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

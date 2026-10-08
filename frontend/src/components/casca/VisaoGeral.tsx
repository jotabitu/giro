"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, TriangleAlert, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import {
  AlertCard,
  CelulaDupla,
  DataTable,
  FleetBar,
  Icone,
  KpiGrid,
  KpiTile,
  Panel,
  SearchField,
  SegmentedControl,
  StatusBadge,
  type ColunaTabela,
} from "@/design-system";
import { relatorios, type Inicio } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { saudacao } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";

type Periodo = "hoje" | "7d" | "30d";
type Devolucao = Inicio["devolucoes"]["linhas"][number];

const COLUNAS: ColunaTabela<Devolucao>[] = [
  { chave: "placa", titulo: "Placa", mono: true },
  { chave: "veiculo", titulo: "Veículo e cliente", celula: (l) => <CelulaDupla principal={l.veiculo} secundaria={l.cliente} /> },
  { chave: "data", titulo: "Devolução", mono: true },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (l) => (
      <StatusBadge tom={l.tom} compacto>
        {l.situacao}
      </StatusBadge>
    ),
  },
];

/** Main: visão geral do administrador. Todos os números e status vêm da API; a tela só os mostra. */
export function VisaoGeral() {
  const { eu } = useSessao();
  const [periodo, setPeriodo] = useState<Periodo>("7d");
  const temPainel = eu.pode.painel !== "nao";
  const consulta = useQuery({ queryKey: ["inicio", periodo], queryFn: () => relatorios.inicio(periodo), enabled: temPainel });

  if (!temPainel) {
    return (
      <div className="wl-panel">
        <h1 className="text-title">Olá, {eu.nome.split(" ")[0]}</h1>
        <p className="mt-2 text-body text-ink-muted">Seu perfil não tem painel de visão geral. Use o menu para chegar ao que você faz.</p>
      </div>
    );
  }

  const d = consulta.data;
  const controlePeriodo = (
    <SegmentedControl
      rotulo="Período"
      valor={periodo}
      aoMudar={setPeriodo}
      opcoes={[
        { valor: "hoje", rotulo: "Hoje" },
        { valor: "7d", rotulo: "7 dias" },
        { valor: "30d", rotulo: "30 dias" },
      ]}
    />
  );
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <h1 className="text-title md:text-display">
          {saudacao()}, {eu.nome.split(" ")[0]}
        </h1>
        {d && d.atencao > 0 && (
          <StatusBadge tom="marca" icone={<Icone de={TriangleAlert} />}>
            {d.atencao} contratos pedem atenção
          </StatusBadge>
        )}
        <div className="flex w-full flex-wrap items-center gap-3 md:ml-auto md:w-auto">
          <SearchField placeholder="Buscar placa, cliente ou contrato" />
          {eu.pode.locacoes_criar && (
            <Link href="/locacoes/nova" className="wl-btn wl-btn--solid">
              <Icone de={Plus} />
              Nova locação
            </Link>
          )}
        </div>
      </header>

      {consulta.isError && (
        <p role="alert" className="wl-panel text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && temPainel && (
        <p className="wl-panel text-body text-ink-muted" aria-busy="true">
          Carregando a visão geral…
        </p>
      )}

      {d && (
        <>
          <Panel
            titulo="Frota"
            acao={<div className="hidden md:block">{controlePeriodo}</div>}
          >
            <div className="flex flex-col gap-4">
              <div className="md:hidden">{controlePeriodo}</div>
              <KpiGrid>
                {d.kpis.map((k) => (
                  <KpiTile key={k.rotulo} rotulo={k.rotulo} valor={k.valor} contexto={k.contexto} destaque={k.destaque} />
                ))}
              </KpiGrid>
              <FleetBar nota={d.frota.nota} segmentos={d.frota.segmentos} />
            </div>
          </Panel>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <Panel
              titulo="Devoluções da semana"
              subtitulo={d.devolucoes.subtitulo}
            >
              <DataTable colunas={COLUNAS} linhas={d.devolucoes.linhas} chaveDaLinha={(l) => l.id} legenda="Devoluções da semana" />
            </Panel>
            <div className="flex flex-col gap-6">
              <AlertCard
                atualizadoHa={d.pendencias.atualizadoHa}
                titulo={d.pendencias.titulo}
                itens={d.pendencias.itens}
                acao={
                  <Link href="/locacoes" className="wl-btn wl-btn--brand">
                    Ver pendências
                  </Link>
                }
              />
              <Panel
                titulo="Caixa de hoje"
                subtitulo={d.caixa.subtitulo}
                acao={
                  <Link href="/financeiro/caixa" aria-label="Abrir financeiro" className="wl-icon-btn wl-icon-btn--sunken wl-icon-btn--sm">
                    <Icone de={ArrowUpRight} />
                  </Link>
                }
              >
                <div className="text-title">{d.caixa.saldo}</div>
                <div className="text-caption text-ink-muted">saldo do dia</div>
                <dl className="mt-4 flex flex-col">
                  {d.caixa.linhas.map((l) => (
                    <div key={l.rotulo} className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
                      <dt className="text-ink-muted">{l.rotulo}</dt>
                      <dd className="wl-mono">{l.valor}</dd>
                    </div>
                  ))}
                </dl>
              </Panel>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { CelulaDupla, DataTable, Panel, StatusBadge, type ColunaTabela } from "@/design-system";
import { useAmbiente } from "@/lib/ambiente";
import type { InicioDe, ItemAgenda } from "@/lib/api";
import { placa } from "@/lib/formatos";
import { horaCurta, horarioDaAgenda, tomDoStatus } from "@/lib/painel";
import { CabecalhoInicio, Vazio } from "./comuns";

const TIPO = { saida: "Saída", devolucao: "Devolução" } as const;
const hrefDaAcao = (i: ItemAgenda) => `/locacoes/${i.locacao.id}/${i.tipo === "saida" ? "vistoria" : "devolucao"}`;

const COLUNAS: ColunaTabela<ItemAgenda>[] = [
  { chave: "horario", titulo: "Horário", mono: true, celula: (i) => <span className="whitespace-nowrap">{horarioDaAgenda(i.horario)}</span> },
  { chave: "tipo", titulo: "Tipo", celula: (i) => TIPO[i.tipo] },
  { chave: "veiculo", titulo: "Veículo", celula: (i) => <CelulaDupla principal={<span className="wl-mono whitespace-nowrap">{placa(i.veiculo.placa)}</span>} secundaria={i.veiculo.modelo} /> },
  { chave: "cliente", titulo: "Cliente", celula: (i) => i.cliente.nome },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (i) => (
      <StatusBadge tom={tomDoStatus(i.situacao.tom)} compacto>
        {i.situacao.rotulo}
      </StatusBadge>
    ),
  },
  {
    chave: "acao",
    titulo: "Ação",
    celula: (i) => (
      <Link href={hrefDaAcao(i)} className="wl-btn wl-btn--quiet wl-btn--sm">
        {i.acao.rotulo}
      </Link>
    ),
  },
];

/** Início do vistoriador (USR-08): agenda do dia e avarias abertas. Sem valores em dinheiro. */
export function InicioVistoriador({ d }: { d: InicioDe<"vistoriador"> }) {
  useAmbiente(); // o "hoje" da API muda o texto dos horários e períodos
  const agenda = d.agenda ?? { resumo: "", proxima: null, avarias_abertas: 0, resultados: [] };
  const proxima = agenda.proxima ? agenda.resultados.find((i) => i.id === agenda.proxima?.item_id) : undefined;
  return (
    <div className="flex flex-col gap-6">
      <CabecalhoInicio saudacao={d.saudacao}>
        <Link href="/veiculos" className="wl-btn wl-btn--quiet">
          Consultar veículo
        </Link>
        <Link href="/vistorias/avarias" className="wl-btn wl-btn--quiet">
          Avarias abertas
          <span className="wl-count">{d.avarias_abertas}</span>
        </Link>
      </CabecalhoInicio>
      <p className="text-caption text-ink-muted">Seu perfil mostra só vistorias e veículos. Valores e dados de pagamento ficam ocultos.</p>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
        <Panel titulo="Vistorias de hoje" subtitulo={agenda.resumo}>
          {agenda.resultados.length === 0 ? (
            <Vazio>Nenhuma vistoria para hoje.</Vazio>
          ) : (
            <DataTable colunas={COLUNAS} linhas={agenda.resultados} chaveDaLinha={(i) => i.id} legenda="Vistorias de hoje" />
          )}
        </Panel>
        {proxima && agenda.proxima && (
          <Panel titulo="Próxima vistoria" subtitulo={`em ${agenda.proxima.em_minutos} min`}>
            <div className="text-body-strong">
              {TIPO[proxima.tipo]} às <span className="wl-mono">{horaCurta(proxima.horario)}</span>
            </div>
            <div className="text-body">
              {proxima.veiculo.modelo} · <span className="wl-mono">{placa(proxima.veiculo.placa)}</span>
            </div>
            <div className="mb-4 text-caption text-ink-muted">{proxima.cliente.nome}</div>
            <Link href={hrefDaAcao(proxima)} className="wl-btn wl-btn--solid">
              {proxima.acao.rotulo}
            </Link>
          </Panel>
        )}
      </div>
    </div>
  );
}

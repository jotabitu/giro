"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { CelulaDupla, DataTable, Icone, Panel, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { vistorias, type DiaDaAgenda, type ItemDaAgenda } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useFiltrosNaUrl } from "@/lib/filtros-url";
import { placa } from "@/lib/formatos";
import { horaCurta, horarioDaAgenda } from "@/lib/painel";
import { tomDoStatus } from "@/lib/tom";

// Referência: docs/telas/html/Vistoriador-Desktop.dc.html e Vistoriador-Mobile.dc.html (agenda, VIS-05).
// Os itens, a situação, a ação e o "em 20 min" vêm de GET /api/vistorias/agenda/?dia=; sem valores em dinheiro.

const TIPO = { saida: "Saída", devolucao: "Devolução" } as const;
const NOME_DA_ABA: Record<DiaDaAgenda, string> = { hoje: "Hoje", amanha: "Amanhã", semana: "Semana" };
const ordenado = (i: ItemDaAgenda[]) => [...i].sort((a, b) => a.horario.localeCompare(b.horario));

/** Para onde a ação do item leva: a vistoria de saída ou a devolução da locação. */
export const rotaDoItemDaAgenda = (i: Pick<ItemDaAgenda, "tipo" | "locacao">) => `/locacoes/${i.locacao.id}/${i.tipo === "saida" ? "vistoria" : "devolucao"}`;

const COLUNAS: ColunaTabela<ItemDaAgenda>[] = [
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
    titulo: "",
    celula: (i) => (
      <Link href={rotaDoItemDaAgenda(i)} className={`wl-btn wl-btn--sm ${i.acao.codigo === "abrir" ? "wl-btn--quiet" : "wl-btn--solid"}`}>
        {i.acao.rotulo}
      </Link>
    ),
  },
];

function Linha({ i }: { i: ItemDaAgenda }) {
  return (
    <Link href={rotaDoItemDaAgenda(i)} className="flex min-h-[56px] items-center gap-3 rounded-lg bg-surface px-4 py-3 text-ink no-underline">
      <span className="wl-mono w-[60px] shrink-0 text-caption text-ink-muted">{horarioDaAgenda(i.horario)}</span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-body font-medium">
          {placa(i.veiculo.placa)} · {i.veiculo.modelo}
        </span>
        <small className="block text-caption text-ink-muted">{i.cliente.nome}</small>
      </span>
      <StatusBadge tom={tomDoStatus(i.situacao.tom)} compacto>
        {i.situacao.rotulo}
      </StatusBadge>
      <Icone de={ChevronRight} className="text-ink-muted" />
    </Link>
  );
}

function Grupo({ um, varios, itens }: { um: string; varios: string; itens: ItemDaAgenda[] }) {
  if (itens.length === 0) return null;
  const titulo = varios.charAt(0).toUpperCase() + varios.slice(1);
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between px-1 text-body font-medium">
        {titulo}
        <span className="text-caption font-normal text-ink-muted">
          {itens.length} {itens.length === 1 ? um : varios}
        </span>
      </div>
      {itens.map((i) => (
        <Linha key={i.id} i={i} />
      ))}
    </section>
  );
}

/** Agenda do vistoriador: retiradas e devoluções do dia, a próxima vistoria e a ação de cada uma. */
export function AgendaDoVistoriador() {
  const { valor, definir } = useFiltrosNaUrl();
  const dia = (["hoje", "amanha", "semana"].includes(valor("dia") ?? "") ? valor("dia") : "hoje") as DiaDaAgenda;
  const consulta = useQuery({ queryKey: ["agenda", dia], queryFn: () => vistorias.agenda(dia), placeholderData: (a) => a });
  const outros = useQuery({ queryKey: ["agenda", dia === "hoje" ? "amanha" : "hoje"], queryFn: () => vistorias.agenda(dia === "hoje" ? "amanha" : "hoje") });
  const d = consulta.data;
  const itens = ordenado(d?.resultados ?? []);
  const proxima = d?.proxima ? itens.find((i) => i.id === d.proxima?.item_id) : undefined;
  const contagem = (alvo: DiaDaAgenda) => (alvo === dia ? d?.resultados.length : outros.data && (alvo === "hoje" || alvo === "amanha") ? outros.data.resultados.length : undefined);
  const abas = (["hoje", "amanha", "semana"] as DiaDaAgenda[]).map((a) => ({ valor: a, rotulo: NOME_DA_ABA[a] }));
  const abasCelular = (["hoje", "amanha"] as DiaDaAgenda[]).map((a) => ({ valor: a, rotulo: `${NOME_DA_ABA[a]}${contagem(a) === undefined ? "" : ` · ${contagem(a)}`}` }));
  const mudar = (v: string) => definir({ dia: v === "hoje" ? null : v });

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <h1 className="text-title md:text-display">Vistorias de {dia === "hoje" ? "hoje" : dia === "amanha" ? "amanhã" : "a semana"}</h1>
          {d && <p className="mt-1 text-body text-ink-muted">{d.resumo}</p>}
        </div>
        <div className="md:ml-auto">
          <div className="hidden md:block">
            <SegmentedControl rotulo="Dia" valor={dia} aoMudar={mudar} opcoes={abas} />
          </div>
          <div className="md:hidden">
            <SegmentedControl rotulo="Dia" valor={dia === "semana" ? "hoje" : dia} aoMudar={mudar} opcoes={abasCelular} />
          </div>
        </div>
      </header>

      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando a agenda…
        </p>
      )}

      {d && (
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-w-0">
            {itens.length === 0 ? (
              <Panel>
                <p className="py-6 text-center text-body text-ink-muted">Nenhuma vistoria para {dia === "hoje" ? "hoje" : dia === "amanha" ? "amanhã" : "a semana"}.</p>
              </Panel>
            ) : (
              <>
                <div className="hidden md:block">
                  <Panel>
                    <div className="overflow-x-auto">
                      <DataTable colunas={COLUNAS} linhas={itens} chaveDaLinha={(i) => i.id} legenda="Vistorias" />
                    </div>
                  </Panel>
                </div>
                <div className="flex flex-col gap-5 md:hidden">
                  <Grupo um="saída" varios="saídas" itens={itens.filter((i) => i.tipo === "saida")} />
                  <Grupo um="devolução" varios="devoluções" itens={itens.filter((i) => i.tipo === "devolucao")} />
                </div>
              </>
            )}
          </div>

          <aside className="flex flex-col gap-6">
            {proxima && d.proxima && (
              <Panel titulo="Próxima vistoria" acao={<StatusBadge tom="marca" compacto>em {d.proxima.em_minutos} min</StatusBadge>}>
                <div className="text-title font-semibold">
                  {proxima.tipo === "saida" ? "Check-out" : "Devolução"} às <span className="wl-mono">{horaCurta(proxima.horario)}</span>
                </div>
                <div className="mb-4 mt-1 text-body">
                  {proxima.veiculo.modelo} · <span className="wl-mono">{placa(proxima.veiculo.placa)}</span>
                  <br />
                  <span className="text-ink-muted">{proxima.cliente.nome}</span>
                </div>
                <Link href={rotaDoItemDaAgenda(proxima)} className="wl-btn wl-btn--brand">
                  {proxima.acao.rotulo} {proxima.tipo === "saida" ? "vistoria" : "devolução"}
                </Link>
              </Panel>
            )}
            <div className="hidden md:block">
              <Panel>
                <p className="text-body text-ink-muted">Dica: a vistoria é mais rápida no celular, com as fotos tiradas direto pela câmera.</p>
              </Panel>
            </div>
            <Link href="/vistorias/avarias" className="wl-btn wl-btn--quiet">
              Avarias abertas
              <span className="wl-count">{d.avarias_abertas}</span>
            </Link>
          </aside>
        </div>
      )}
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, CelulaDupla, DataTable, Icone, KpiGrid, KpiTile, SearchField, StatusBadge, type ColunaTabela } from "@/design-system";
import { FiltroChips, type OpcaoChip } from "@/components/lista/FiltroChips";
import { Paginacao } from "@/components/lista/Paginacao";
import { useAmbiente } from "@/lib/ambiente";
import { locacoes, type AbaLocacoes, type LocacaoResumo, type Periodicidade } from "@/lib/api";
import { ROTULO_PERIODICIDADE } from "@/lib/clientes";
import { mensagemDoErro } from "@/lib/erros";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { dinheiro, placa, percentual } from "@/lib/formatos";
import { periodoDaLocacao, rotaDaAcaoLocacao } from "@/lib/locacoes";
import { useSessao } from "@/lib/sessao";
import { tomDoStatus } from "@/lib/tom";

// Referência: docs/telas/html/Locacoes-Desktop.dc.html e Locacoes-Mobile.dc.html.
// Situação, pagamento e ação principal vêm da API; a tela não calcula nada.

const ABAS: { valor: AbaLocacoes; rotulo: string; curto: string; chave: "abertas" | "precisam_acao" | "devolvem_hoje" | "encerradas" | "canceladas" | "rascunhos" }[] = [
  { valor: "abertas", rotulo: "Todas", curto: "Todas", chave: "abertas" },
  { valor: "precisam_acao", rotulo: "Precisam de ação", curto: "Ação", chave: "precisam_acao" },
  { valor: "devolvem_hoje", rotulo: "Devolvem hoje", curto: "Hoje", chave: "devolvem_hoje" },
  { valor: "encerradas", rotulo: "Encerradas", curto: "Encerradas", chave: "encerradas" },
  { valor: "canceladas", rotulo: "Canceladas", curto: "Canceladas", chave: "canceladas" },
  { valor: "rascunhos", rotulo: "Rascunhos", curto: "Rascunhos", chave: "rascunhos" },
];

/** As abas da referência aparecem sempre; Canceladas e Rascunhos só quando há o que ver. */
const SEMPRE = new Set<AbaLocacoes>(["abertas", "precisam_acao", "devolvem_hoje", "encerradas"]);
const CURTAS_NO_CELULAR = new Set<AbaLocacoes>(["precisam_acao", "devolvem_hoje", "abertas"]);
const PLANOS: { valor: Periodicidade | "todos"; rotulo: string }[] = [
  { valor: "todos", rotulo: "Plano: todos" },
  { valor: "diaria", rotulo: "Plano: diária" },
  { valor: "semanal", rotulo: "Plano: semanal" },
  { valor: "mensal", rotulo: "Plano: mensal" },
];

function Situacao({ l }: { l: LocacaoResumo }) {
  return (
    <StatusBadge tom={tomDoStatus(l.situacao.tom)} compacto>
      {l.situacao.rotulo}
    </StatusBadge>
  );
}

const COLUNAS: ColunaTabela<LocacaoResumo>[] = [
  { chave: "cliente", titulo: "Cliente", celula: (l) => <CelulaDupla principal={l.cliente.nome} secundaria={<span className="wl-mono">{l.codigo}</span>} /> },
  { chave: "veiculo", titulo: "Veículo", celula: (l) => <CelulaDupla principal={<span className="font-normal">{l.veiculo.modelo}</span>} secundaria={placa(l.veiculo.placa)} /> },
  { chave: "plano", titulo: "Plano e período", celula: (l) => <CelulaDupla principal={ROTULO_PERIODICIDADE[l.periodicidade]} secundaria={periodoDaLocacao(l)} /> },
  { chave: "situacao", titulo: "Situação", celula: (l) => <Situacao l={l} /> },
  { chave: "pagamento", titulo: "Pagamento", celula: (l) => <span className="text-caption">{l.pagamento?.rotulo ?? "—"}</span> },
  {
    chave: "acao",
    titulo: "",
    celula: (l) => (
      <Link href={rotaDaAcaoLocacao(l)} onClick={(e) => e.stopPropagation()} className="wl-btn wl-btn--quiet wl-btn--sm whitespace-nowrap">
        {l.acao_principal.rotulo}
      </Link>
    ),
  },
];

function CartaoDaLocacao({ l }: { l: LocacaoResumo }) {
  return (
    <Link href={`/locacoes/${l.id}`} className="flex flex-col gap-2 rounded-lg bg-surface p-4 text-ink no-underline">
      <span className="flex items-center justify-between gap-3">
        <span className="min-w-0 truncate text-body font-medium">{l.cliente.nome}</span>
        <span className="wl-mono shrink-0 text-caption text-ink-muted">{l.codigo}</span>
      </span>
      <span className="text-caption text-ink-muted">
        {l.veiculo.modelo} · {placa(l.veiculo.placa)} · {periodoDaLocacao(l)}
      </span>
      <span className="flex flex-wrap items-center gap-2">
        <Situacao l={l} />
        {l.pagamento && <span className="text-caption text-ink-muted">{l.pagamento.rotulo}</span>}
        <Icone de={ChevronRight} className="ml-auto text-ink-muted" />
      </span>
    </Link>
  );
}

/** Locações: indicadores, abas, filtros e lista. */
export function ListaLocacoes() {
  useAmbiente(); // o "hoje" da API muda o texto dos horários e períodos
  const router = useRouter();
  const { eu } = useSessao();
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("aba") ?? "abertas") as AbaLocacoes;
  const plano = (valor("periodicidade") ?? "todos") as Periodicidade | "todos";
  const cursor = valor("cursor") ?? undefined;
  const buscaNaUrl = valor("busca") ?? "";
  const [busca, setBusca] = useBuscaNaUrl(definir, buscaNaUrl);

  const consulta = useQuery({
    queryKey: ["locacoes", { aba, plano, busca: buscaNaUrl, cursor }],
    queryFn: () => locacoes.listar({ aba, periodicidade: plano === "todos" ? undefined : plano, busca: buscaNaUrl || undefined, cursor }),
    placeholderData: (anterior) => anterior,
  });
  const d = consulta.data;
  const c = d?.contagens;
  const ind = d?.indicadores;
  const filial = eu.filiais[0]?.nome;

  const visiveis = ABAS.filter((a) => SEMPRE.has(a.valor) || a.valor === aba || (c?.[a.chave] ?? 0) > 0);
  const opcoes: OpcaoChip[] = visiveis.map((a) => ({ valor: a.valor, rotulo: a.rotulo, contagem: c?.[a.chave] }));
  const opcoesCelular: OpcaoChip[] = visiveis.filter((a) => CURTAS_NO_CELULAR.has(a.valor) || a.valor === aba).map((a) => ({ valor: a.valor, rotulo: a.curto, contagem: c?.[a.chave] }));
  const ordemCelular = ["precisam_acao", "devolvem_hoje", "abertas"];
  opcoesCelular.sort((x, y) => (ordemCelular.indexOf(x.valor) + 1 || 9) - (ordemCelular.indexOf(y.valor) + 1 || 9));
  const total = c?.[ABAS.find((a) => a.valor === aba)?.chave ?? "abertas"];

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <h1 className="text-title md:text-display">Locações</h1>
          {ind && (
            <p className="mt-1 text-body text-ink-muted">
              {filial ? `${filial} · ` : ""}
              {ind.ativas} ativas
            </p>
          )}
        </div>
        <div className="flex w-full flex-wrap items-center gap-3 md:ml-auto md:w-auto">
          <SearchField placeholder="Cliente, placa ou contrato" value={busca} onChange={(e) => setBusca(e.target.value)} />
          {eu.pode.locacoes_criar && (
            <Link href="/locacoes/nova" className="wl-btn wl-btn--solid">
              <Icone de={Plus} />
              Nova locação
            </Link>
          )}
        </div>
      </header>

      {ind && (
        <>
          <div className="hidden md:block">
            <KpiGrid>
              <KpiTile destaque rotulo="Ativas" valor={String(ind.ativas)} contexto={ind.frota_alugada_pct ? `${percentual(ind.frota_alugada_pct)} da frota alugada` : undefined} />
              <KpiTile rotulo="Devolvem hoje" valor={String(ind.devolvem_hoje)} contexto={ind.devolvem_hoje_ate_12h > 0 ? `${ind.devolvem_hoje_ate_12h} até as 12:00` : undefined} />
              <KpiTile rotulo="Devolução atrasada" valor={String(ind.devolucao_atrasada)} contexto={ind.devolucao_atrasada_destaque ?? undefined} />
              <KpiTile rotulo="Pagamentos atrasados" valor={String(ind.pagamentos_atrasados)} contexto={dinheiro(ind.pagamentos_atrasados_centavos)} />
            </KpiGrid>
          </div>
          <div className="md:hidden">
            <KpiGrid>
              <KpiTile rotulo="Devolvem hoje" valor={String(ind.devolvem_hoje)} contexto={ind.devolvem_hoje_ate_12h > 0 ? `${ind.devolvem_hoje_ate_12h} até 12:00` : undefined} />
              <KpiTile rotulo="Atrasados" valor={String(ind.pagamentos_atrasados)} contexto={dinheiro(ind.pagamentos_atrasados_centavos)} />
            </KpiGrid>
          </div>
        </>
      )}

      <section className="wl-panel">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <div className="hidden md:block">
              <FiltroChips rotulo="Situação" opcoes={opcoes} valor={aba} aoMudar={(v) => definir({ aba: v === "abertas" ? null : v })} />
            </div>
            <div className="md:hidden">
              <FiltroChips rotulo="Situação" opcoes={opcoesCelular} valor={aba} aoMudar={(v) => definir({ aba: v === "abertas" ? null : v })} />
            </div>
          </div>
          <div className="ml-auto hidden items-center gap-2 md:flex">
            <label className="wl-btn wl-btn--sm">
              <span className="sr-only">Plano</span>
              <select
                aria-label="Plano"
                value={plano}
                onChange={(e) => definir({ periodicidade: e.target.value === "todos" ? null : e.target.value })}
                className="cursor-pointer appearance-none border-0 bg-transparent text-inherit outline-none [font:inherit]"
              >
                {PLANOS.map((p) => (
                  <option key={p.valor} value={p.valor}>
                    {p.rotulo}
                  </option>
                ))}
              </select>
            </label>
            <Button compacto disabled title="Ainda não está disponível">
              Veículo: todos
            </Button>
          </div>
        </div>

        {consulta.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {consulta.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando as locações…
          </p>
        )}
        {d && d.resultados.length === 0 && <p className="py-6 text-center text-body text-ink-muted">Nenhuma locação com esses filtros. Tire um filtro ou mude a busca.</p>}
        {d && d.resultados.length > 0 && (
          <>
            <div className="hidden overflow-x-auto md:block">
              <DataTable colunas={COLUNAS} linhas={d.resultados} chaveDaLinha={(r) => String(r.id)} aoAbrir={(r) => router.push(`/locacoes/${r.id}`)} legenda="Locações" />
            </div>
            <div className="flex flex-col gap-3 md:hidden">
              {d.resultados.map((r) => (
                <CartaoDaLocacao key={r.id} l={r} />
              ))}
            </div>
            <Paginacao
              texto={total === null || total === undefined ? `Mostrando ${d.resultados.length}` : `Mostrando ${d.resultados.length} de ${total}`}
              anterior={d.anterior}
              proximo={d.proximo}
              aoIr={(cur) => definir({ cursor: cur })}
            />
          </>
        )}
      </section>
    </div>
  );
}

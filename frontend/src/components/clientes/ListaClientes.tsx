"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CelulaDupla, DataTable, Icone, KpiGrid, KpiTile, SearchField, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { FiltroChips, type OpcaoChip } from "@/components/lista/FiltroChips";
import { Paginacao } from "@/components/lista/Paginacao";
import { clientes, type ClienteResumo, type FiltroClientes, type SituacaoCliente } from "@/lib/api";
import { rotaDaAcao } from "@/lib/clientes";
import { mensagemDoErro } from "@/lib/erros";
import { celular, dinheiro, iniciais, mesAno, percentual } from "@/lib/formatos";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { tomDoStatus } from "@/lib/tom";
import { useSessao } from "@/lib/sessao";

type Ordem = NonNullable<FiltroClientes["ordem"]>;

function Avatar({ nome }: { nome: string }) {
  return (
    <span aria-hidden="true" className="grid h-9 w-9 shrink-0 place-items-center rounded-sm bg-solid text-caption font-semibold text-on-solid">
      {iniciais(nome)}
    </span>
  );
}

/** Texto de valor ao lado da situação: o que a API calculou, em reais. */
function valorDestacado(c: ClienteResumo): string | null {
  const f = c.financeiro;
  if (!f) return null;
  if (f.em_aberto_centavos > 0) return `${dinheiro(f.em_aberto_centavos)} em aberto`;
  if (f.a_devolver_centavos > 0) return `${dinheiro(f.a_devolver_centavos)} a devolver`;
  return null;
}

function textoDaLocacao(c: ClienteResumo): string {
  const l = c.locacao_atual;
  if (l) return [l.codigo, l.veiculo, l.detalhe].filter(Boolean).join(" · ");
  if (c.venda_aberta) return `${c.venda_aberta.codigo} · ${c.venda_aberta.veiculo}`;
  return c.ultima_locacao ? `última: ${c.ultima_locacao.codigo}` : "Sem locação";
}

const COLUNAS: ColunaTabela<ClienteResumo>[] = [
  {
    chave: "cliente",
    titulo: "Cliente",
    celula: (c) => (
      <span className="flex items-center gap-3">
        <Avatar nome={c.nome} />
        <span>
          <CelulaDupla principal={c.nome} secundaria={c.tipo === "pj" ? `CNPJ ${c.documento_mascarado}` : `CPF ${c.documento_mascarado}`} />
        </span>
      </span>
    ),
  },
  { chave: "contato", titulo: "Contato", celula: (c) => <CelulaDupla principal={celular(c.celular)} secundaria="WhatsApp" /> },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (c) => (
      <span className="flex flex-col items-start gap-1">
        <StatusBadge tom={tomDoStatus(c.situacao.tom)} compacto>
          {c.situacao.rotulo}
        </StatusBadge>
        {valorDestacado(c) && <span className="text-caption text-ink-muted">{valorDestacado(c)}</span>}
      </span>
    ),
  },
  { chave: "locacao", titulo: "Locação", celula: (c) => <span className="text-caption text-ink-muted">{textoDaLocacao(c)}</span> },
  {
    chave: "pago",
    titulo: "Total pago",
    celula: (c) => <CelulaDupla principal={<span className="wl-mono">{dinheiro(c.financeiro?.total_pago_centavos ?? 0)}</span>} secundaria="pago no total" />,
  },
  { chave: "desde", titulo: "Cliente desde", mono: true, celula: (c) => mesAno(c.cliente_desde) },
  {
    chave: "acao",
    titulo: "",
    celula: (c) =>
      c.acao_principal ? (
        <Link
          href={rotaDaAcao(c.acao_principal)}
          onClick={(e) => e.stopPropagation()}
          className="wl-btn wl-btn--quiet wl-btn--sm"
        >
          {c.acao_principal.rotulo}
        </Link>
      ) : null,
  },
];

function CartaoDoCliente({ c }: { c: ClienteResumo }) {
  const destaque = valorDestacado(c);
  return (
    <Link href={c.acao_principal ? rotaDaAcao(c.acao_principal) : `/clientes/${c.id}`} className="flex flex-col gap-2 rounded-lg bg-surface p-4 text-ink no-underline">
      <span className="flex items-center gap-3">
        <Avatar nome={c.nome} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-body font-medium">{c.nome}</span>
          <span className="block text-caption text-ink-muted">{celular(c.celular)}</span>
        </span>
        <Icone de={ChevronRight} className="text-ink-muted" />
      </span>
      <span className="text-caption text-ink-muted">{textoDaLocacao(c)}</span>
      <span className="flex flex-wrap items-center gap-2">
        <StatusBadge tom={tomDoStatus(c.situacao.tom)} compacto>
          {c.situacao.rotulo}
        </StatusBadge>
        {destaque && <span className="text-caption text-ink-muted">{destaque}</span>}
      </span>
    </Link>
  );
}

const SITUACOES: { valor: string; rotulo: string; chave: "todos" | "com_locacao" | "em_aberto" | "bloqueados" | "incompletos" }[] = [
  { valor: "todos", rotulo: "Todos", chave: "todos" },
  { valor: "com_locacao", rotulo: "Com locação", chave: "com_locacao" },
  { valor: "em_aberto", rotulo: "Em aberto", chave: "em_aberto" },
  { valor: "bloqueados", rotulo: "Bloqueados", chave: "bloqueados" },
  { valor: "incompletos", rotulo: "Cadastro incompleto", chave: "incompletos" },
];

/** Clientes: indicadores, filtro por situação e lista. Situação, valores e ação principal vêm da API. */
export function ListaClientes() {
  const router = useRouter();
  const { eu } = useSessao();
  const { valor, definir } = useFiltrosNaUrl();
  const situacao = valor("situacao") ?? "todos";
  const ordem = (valor("ordem") ?? "-criado_em") as Ordem;
  const cursor = valor("cursor") ?? undefined;
  const buscaNaUrl = valor("busca") ?? "";
  const [busca, setBusca] = useBuscaNaUrl(definir, buscaNaUrl);

  const consulta = useQuery({
    queryKey: ["clientes", { situacao, ordem, busca: buscaNaUrl, cursor }],
    queryFn: () => clientes.listar({ situacao: situacao === "todos" ? undefined : (situacao as SituacaoCliente), ordem, busca: buscaNaUrl || undefined, cursor }),
    placeholderData: (anterior) => anterior,
  });
  const d = consulta.data;
  const c = d?.contagens;
  const ind = d?.indicadores;

  const opcoes: OpcaoChip[] = SITUACOES.map((s) => ({ valor: s.valor, rotulo: s.rotulo, contagem: c?.[s.chave] }));
  const total = c?.[SITUACOES.find((s) => s.valor === situacao)?.chave ?? "todos"];
  const filial = eu.filiais[0]?.nome;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <h1 className="text-title md:text-display">Clientes</h1>
          {c && (
            <p className="mt-1 text-body text-ink-muted">
              {c.todos} clientes{filial ? ` · ${filial}` : ""}
            </p>
          )}
        </div>
        <div className="flex w-full flex-wrap items-center gap-3 md:ml-auto md:w-auto">
          <SearchField placeholder="Nome, CPF ou telefone" value={busca} onChange={(e) => setBusca(e.target.value)} />
          {eu.pode.clientes_cadastrar && (
            <Link href="/clientes/novo" className="wl-btn wl-btn--solid">
              <Icone de={Plus} />
              Novo cliente
            </Link>
          )}
        </div>
      </header>

      {c && ind && (
        <KpiGrid>
          <KpiTile destaque rotulo="Clientes" valor={String(c.todos)} contexto={`${ind.novos_no_mes_anterior} novos no mês passado`} />
          <KpiTile rotulo="Com locação ativa" valor={c.com_locacao === null ? "—" : String(c.com_locacao)} contexto={ind.com_locacao_pct ? `${percentual(ind.com_locacao_pct)} da base` : undefined} />
          <KpiTile
            rotulo="Com pagamento em aberto"
            valor={c.em_aberto === null ? "—" : String(c.em_aberto)}
            contexto={ind.em_aberto_total_centavos === null ? undefined : dinheiro(ind.em_aberto_total_centavos)}
          />
          <KpiTile rotulo="Cadastro incompleto" valor={String(c.incompletos)} contexto="faltam documentos" />
        </KpiGrid>
      )}

      <section className="wl-panel">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <FiltroChips rotulo="Situação" opcoes={opcoes} valor={situacao} aoMudar={(v) => definir({ situacao: v === "todos" ? null : v })} />
          </div>
          <div className="hidden md:block">
            <SegmentedControl
              rotulo="Ordenar por"
              valor={ordem}
              aoMudar={(v) => definir({ ordem: v === "-criado_em" ? null : v })}
              opcoes={[
                { valor: "-criado_em", rotulo: "Recentes" },
                { valor: "nome", rotulo: "Nome" },
                { valor: "-total_pago", rotulo: "Mais pagos" },
              ]}
            />
          </div>
        </div>

        {consulta.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {consulta.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando os clientes…
          </p>
        )}
        {d && d.resultados.length === 0 && <p className="py-6 text-center text-body text-ink-muted">Nenhum cliente com esses filtros. Tire um filtro ou mude a busca.</p>}
        {d && d.resultados.length > 0 && (
          <>
            <div className="hidden overflow-x-auto md:block">
              <DataTable colunas={COLUNAS} linhas={d.resultados} chaveDaLinha={(r) => String(r.id)} aoAbrir={(r) => router.push(`/clientes/${r.id}`)} legenda="Clientes" />
            </div>
            <div className="flex flex-col gap-3 md:hidden">
              {d.resultados.map((r) => (
                <CartaoDoCliente key={r.id} c={r} />
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

      <p className="text-caption text-ink-muted">Cliente bloqueado não consegue fazer nova locação até quitar o que deve. O bloqueio é automático após 15 dias de atraso.</p>
    </div>
  );
}

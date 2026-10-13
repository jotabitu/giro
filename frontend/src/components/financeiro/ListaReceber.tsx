"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { MessageCircle, Plus } from "lucide-react";
import { useState } from "react";
import { Button, CelulaDupla, DataTable, Icone, KpiGrid, KpiTile, SearchField, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { FiltroChips, type OpcaoChip } from "@/components/lista/FiltroChips";
import { Paginacao } from "@/components/lista/Paginacao";
import { financeiro, type ContaReceber, type PeriodoReceber, type SituacaoReceber } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { rotuloDaForma, rotuloDaParcela, origemDaConta, situacaoDaConta } from "@/lib/financeiro";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { dataCurta, dinheiro, percentual } from "@/lib/formatos";
import { dinheiroCurto } from "@/lib/painel";
import { useFilial } from "@/lib/filial-escolhida";
import { useSessao } from "@/lib/sessao";
import { BaixaDaConta } from "./BaixaDaConta";
import { Confirmacao, ErroDoFinanceiro } from "./Comuns";
import { DetalheDaConta } from "./DetalheDaConta";
import { NovoLancamento } from "./NovoLancamento";

// Referência: docs/telas/html/Receber-Desktop.dc.html e Receber-Mobile.dc.html.
// Situação, dias de atraso, valor do dia e indicadores vêm da API (FIN-01, FIN-02, FIN-03, FIN-15); a tela não calcula nada.

type Aba = "todas" | SituacaoReceber;

const ABAS: { valor: Aba; rotulo: string; curto: string; chave: "todas" | "atrasadas" | "vencem_hoje" | "a_vencer" | "pagas" }[] = [
  { valor: "todas", rotulo: "Todas", curto: "Todas", chave: "todas" },
  { valor: "atrasadas", rotulo: "Em atraso", curto: "Em atraso", chave: "atrasadas" },
  { valor: "vencem_hoje", rotulo: "Vencem hoje", curto: "Hoje", chave: "vencem_hoje" },
  { valor: "a_vencer", rotulo: "A vencer", curto: "A vencer", chave: "a_vencer" },
  { valor: "pagas", rotulo: "Pagas", curto: "Pagas", chave: "pagas" },
];

const PERIODOS = [
  { valor: "hoje", rotulo: "Hoje" },
  { valor: "semana", rotulo: "Semana" },
  { valor: "mes", rotulo: "Mês" },
] as const;

type Pendente = { tipo: "baixa" | "detalhe"; conta: ContaReceber } | { tipo: "novo" } | null;

function Situacao({ c }: { c: ContaReceber }) {
  const s = situacaoDaConta(c);
  return (
    <StatusBadge tom={s.tom} compacto>
      {s.rotulo}
    </StatusBadge>
  );
}

function BotaoCobrar({ c, aoCobrar, ocupado }: { c: ContaReceber; aoCobrar: (c: ContaReceber) => void; ocupado: boolean }) {
  if (!c.acoes.cobrar) return null;
  return (
    <Button
      compacto
      variante="quieto"
      disabled={ocupado}
      onClick={(e) => {
        e.stopPropagation();
        aoCobrar(c);
      }}
    >
      Cobrar
    </Button>
  );
}

function CartaoDaConta({ c, aoCobrar, aoDarBaixa, aoAbrir, ocupado }: { c: ContaReceber; aoCobrar: (c: ContaReceber) => void; aoDarBaixa: (c: ContaReceber) => void; aoAbrir: (c: ContaReceber) => void; ocupado: boolean }) {
  const rotulo = c.tipo === "parcela" ? `parcela ${rotuloDaParcela(c)}` : rotuloDaParcela(c).toLowerCase();
  return (
    <article className="flex flex-col gap-3 rounded-lg bg-surface p-4">
      <button type="button" onClick={() => aoAbrir(c)} className="flex flex-col gap-3 text-left text-ink">
        <span className="flex items-start gap-3">
          <span className="min-w-0 flex-1">
            <span className="block text-body font-medium">{c.cliente.nome}</span>
            <span className="wl-mono block text-caption text-ink-muted">
              {c.origem.codigo} · {rotulo}
            </span>
          </span>
          <span className="shrink-0 text-body font-semibold">{dinheiro(c.valor_centavos)}</span>
        </span>
        <span className="flex items-center justify-between gap-2 border-t border-line pt-3 text-caption text-ink-muted">
          <Situacao c={c} />
          <span>
            {rotuloDaForma(c.forma_prevista)} · {c.status === "atrasada" ? "venceu" : "vence"} {dataCurta(c.vencimento)}
          </span>
        </span>
      </button>
      {(c.acoes.cobrar || c.acoes.receber) && (
        <div className="grid grid-cols-2 gap-2">
          {c.acoes.cobrar ? (
            <Button compacto variante="marca" disabled={ocupado} onClick={() => aoCobrar(c)}>
              Cobrar no WhatsApp
            </Button>
          ) : (
            <span />
          )}
          {c.acoes.receber && (
            <Button compacto variante="quieto" onClick={() => aoDarBaixa(c)}>
              Dar baixa
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

/** Faixas de atraso (FIN-02): a largura de cada coluna acompanha o valor que a API devolveu. */
function FaixasDeAtraso({ faixas, totalCentavos, parcelas }: { faixas: Record<"1_7" | "8_30" | "mais_30", number>; totalCentavos: number; parcelas: number }) {
  const itens = [
    { chave: "1_7", rotulo: "1 a 7 dias", classe: "wl-pipe__col--brand" },
    { chave: "8_30", rotulo: "8 a 30 dias", classe: "" },
    { chave: "mais_30", rotulo: "Mais de 30 dias", classe: "wl-pipe__col--solid" },
  ] as const;
  const piso = Math.max(totalCentavos / 10, 1);
  return (
    <div className="wl-pipe mt-3 hidden md:block">
      <div className="wl-pipe__head">
        <span className="wl-pipe__title">Atraso por faixa</span>
        <span className="wl-pipe__note">
          {dinheiro(totalCentavos)} em {parcelas} {parcelas === 1 ? "parcela" : "parcelas"}
        </span>
      </div>
      <div className="wl-pipe__row">
        {itens.map((i) => (
          <div key={i.chave} className={`wl-pipe__col ${i.classe}`} style={{ flex: Math.max(faixas[i.chave], piso) }}>
            <div className="wl-pipe__bar" />
            <div className="wl-pipe__num">{dinheiro(faixas[i.chave])}</div>
            <div className="wl-pipe__label">{i.rotulo}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Contas a receber: indicadores, faixas de atraso, abas, busca e lista com as ações de cobrança e baixa. */
export function ListaReceber() {
  const { eu } = useSessao();
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("aba") ?? "atrasadas") as Aba;
  const periodo = (valor("periodo") ?? "mes") as PeriodoReceber;
  const buscaNaUrl = valor("busca") ?? "";
  const [busca, setBusca] = useBuscaNaUrl(definir, buscaNaUrl);
  const [aberto, setAberto] = useState<Pendente>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const consulta = useQuery({
    queryKey: ["contas-receber", { aba, periodo, busca: buscaNaUrl }],
    queryFn: () => financeiro.listarContas({ periodo, situacao: aba === "todas" ? undefined : aba, busca: buscaNaUrl || undefined }),
    placeholderData: (anterior) => anterior,
    enabled: eu.pode.caixa_receber,
  });
  const d = consulta.data;
  const ind = d?.indicadores;
  const c = d?.contagens;

  const cobrar = useMutation({
    mutationFn: (conta: ContaReceber) => financeiro.cobrar(conta.id).then((r) => ({ ...r, nome: conta.cliente.nome })),
    onSuccess: (r) => setAviso(r.enviadas > 0 ? `Cobrança enviada a ${r.nome}.` : `Nada foi enviado a ${r.nome}: a conta já foi cobrada hoje ou o cliente não tem contato.`),
  });
  const cobrarTodos = useMutation({
    mutationFn: (ids: number[]) => financeiro.cobrarEmLote(ids),
    onSuccess: (r) => setAviso(r.enviadas === 1 ? "1 cobrança enviada pelo WhatsApp." : `${r.enviadas} cobranças enviadas pelo WhatsApp.`),
  });

  const contas = d?.resultados ?? [];
  const paraCobrar = contas.filter((x) => x.acoes.cobrar).map((x) => x.id);
  const ocupado = cobrar.isPending || cobrarTodos.isPending;
  const mostrar = ABAS.map((a) => ({ valor: a.valor, rotulo: a.rotulo, contagem: c?.[a.chave] }) satisfies OpcaoChip);
  const mostrarCelular = ABAS.filter((a) => a.valor !== "todas").map((a) => ({ valor: a.valor, rotulo: a.curto, contagem: c?.[a.chave] }) satisfies OpcaoChip);
  const filial = useFilial()?.nome ?? eu.filiais[0]?.nome;
  // Lançamento avulso: administrador, gerente e financeiro (contrato financeiro.md, "Quem pode"). Nenhum
  // `pode` cobre os três; a união abaixo exclui vendedor e vistoriador (USR-05).
  const podeLancar = eu.pode.despesas_aprovar || eu.pode.financeiro_pagar;
  const mes = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", month: "long", year: "numeric" }).format(new Date());
  const total = c?.[ABAS.find((a) => a.valor === aba)?.chave ?? "todas"];

  const colunas: ColunaTabela<ContaReceber>[] = [
    { chave: "vencimento", titulo: "Vencimento", mono: true, celula: (x) => <span className="wl-mono">{dataCurta(x.vencimento)}</span> },
    { chave: "cliente", titulo: "Cliente e contrato", celula: (x) => <CelulaDupla principal={x.cliente.nome} secundaria={<span className="wl-mono">{origemDaConta(x)}</span>} /> },
    { chave: "parcela", titulo: "Parcela", celula: (x) => rotuloDaParcela(x) },
    { chave: "forma", titulo: "Forma", celula: (x) => rotuloDaForma(x.status === "paga" ? x.forma : x.forma_prevista) },
    { chave: "valor", titulo: "Valor", celula: (x) => <span className="block text-right font-medium whitespace-nowrap">{dinheiro(x.valor_centavos)}</span> },
    { chave: "situacao", titulo: "Situação", celula: (x) => <Situacao c={x} /> },
    { chave: "acao", titulo: "", celula: (x) => <BotaoCobrar c={x} aoCobrar={(y) => cobrar.mutate(y)} ocupado={ocupado} /> },
  ];

  // USR-09: quem não recebe (vistoriador) não tem a tela; a rota mostra só o aviso.
  if (!eu.pode.caixa_receber)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Seu perfil não tem acesso a Contas a receber.
      </p>
    );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="min-w-0 flex-1 md:flex-none">
          <h1 className="text-title md:text-display">Contas a receber</h1>
          <p className="mt-1 text-body text-ink-muted">
            {mes.charAt(0).toUpperCase() + mes.slice(1)}
            {filial ? ` · ${filial}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 md:ml-auto">
          <div className="hidden md:block">
            <SegmentedControl rotulo="Período" opcoes={PERIODOS} valor={periodo} aoMudar={(v) => definir({ periodo: v === "mes" ? null : v })} />
          </div>
          {podeLancar && (
            <Button variante="solido" icone={<Icone de={Plus} />} onClick={() => setAberto({ tipo: "novo" })}>
              Novo lançamento
            </Button>
          )}
        </div>
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}

      {ind && (
        <section className="wl-panel">
          <KpiGrid>
            <KpiTile destaque rotulo="Previsto no mês" valor={dinheiroCurto(ind.previsto_mes_centavos)} contexto={`${ind.previsto_mes_parcelas} parcelas`} />
            <KpiTile rotulo="Recebido" valor={dinheiroCurto(ind.recebido_mes_centavos)} contexto={ind.recebido_pct ? `${percentual(ind.recebido_pct)} do previsto` : undefined} />
            <KpiTile rotulo="Vence hoje" valor={dinheiroCurto(ind.vence_hoje_centavos)} contexto={`${ind.vence_hoje_parcelas} parcelas`} />
            <KpiTile rotulo="Em atraso" valor={dinheiroCurto(ind.em_atraso_centavos)} contexto={`${ind.em_atraso_clientes} ${ind.em_atraso_clientes === 1 ? "cliente" : "clientes"}`} />
          </KpiGrid>
          <FaixasDeAtraso faixas={ind.faixas} totalCentavos={ind.em_atraso_centavos} parcelas={ind.em_atraso_parcelas} />
        </section>
      )}

      <section className="wl-panel">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <div className="hidden md:block">
              <FiltroChips rotulo="Situação" opcoes={mostrar} valor={aba} aoMudar={(v) => definir({ aba: v === "atrasadas" ? null : v })} />
            </div>
            <div className="md:hidden">
              <FiltroChips rotulo="Situação" opcoes={mostrarCelular} valor={aba === "todas" ? "atrasadas" : aba} aoMudar={(v) => definir({ aba: v === "atrasadas" ? null : v })} />
            </div>
          </div>
          <div className="w-full md:ml-auto md:w-auto">
            <SearchField placeholder="Cliente, contrato ou placa" aria-label="Buscar lançamentos" value={busca} onChange={(e) => setBusca(e.target.value)} />
          </div>
        </div>

        {consulta.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {consulta.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando as contas…
          </p>
        )}
        {(cobrar.isError || cobrarTodos.isError) && <ErroDoFinanceiro erro={cobrar.error ?? cobrarTodos.error} />}
        {d && contas.length === 0 && (
          <p className="py-6 text-center text-body text-ink-muted">{aba === "atrasadas" && !buscaNaUrl ? "Nenhuma conta em atraso." : "Nenhuma conta com esses filtros. Tire um filtro ou mude a busca."}</p>
        )}
        {d && contas.length > 0 && (
          <>
            <div className="hidden overflow-x-auto md:block">
              <DataTable colunas={colunas} linhas={contas} chaveDaLinha={(x) => String(x.id)} aoAbrir={(x) => setAberto({ tipo: "detalhe", conta: x })} legenda="Contas a receber" />
            </div>
            <div className="flex flex-col gap-3 md:hidden">
              {contas.map((x) => (
                <CartaoDaConta key={x.id} c={x} ocupado={ocupado} aoCobrar={(y) => cobrar.mutate(y)} aoDarBaixa={(y) => setAberto({ tipo: "baixa", conta: y })} aoAbrir={(y) => setAberto({ tipo: "detalhe", conta: y })} />
              ))}
            </div>
            <Paginacao
              texto={total === undefined ? `Mostrando ${contas.length}` : `Mostrando ${contas.length} de ${total} ${aba === "atrasadas" ? "parcelas em atraso" : "parcelas"}`}
              anterior={d.anterior}
              proximo={d.proximo}
              aoIr={(cur) => definir({ cursor: cur })}
              extra={
                aba === "atrasadas" && paraCobrar.length > 0 ? (
                  <Button compacto variante="marca" icone={<Icone de={MessageCircle} />} disabled={ocupado} onClick={() => cobrarTodos.mutate(paraCobrar.slice(0, 100))}>
                    Cobrar todos pelo WhatsApp
                  </Button>
                ) : undefined
              }
            />
          </>
        )}
      </section>

      {aberto?.tipo === "novo" && <NovoLancamento aoFechar={() => setAberto(null)} aoConcluir={setAviso} />}
      {aberto?.tipo === "baixa" && <BaixaDaConta conta={aberto.conta} aoFechar={() => setAberto(null)} aoConcluir={setAviso} />}
      {aberto?.tipo === "detalhe" && (
        <DetalheDaConta id={aberto.conta.id} aoFechar={() => setAberto(null)} aoDarBaixa={() => setAberto({ tipo: "baixa", conta: aberto.conta })} aoConcluir={setAviso} />
      )}
    </div>
  );
}

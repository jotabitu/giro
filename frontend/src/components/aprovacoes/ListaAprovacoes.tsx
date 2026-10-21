"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Dialogo, Icone, KpiGrid, KpiTile, StatusBadge, TextField } from "@/design-system";
import { Confirmacao, ErroDoFinanceiro } from "@/components/financeiro/Comuns";
import { aprovacoes, type PedidoDeAprovacao, type StatusDoPedido, type TipoDoPedido } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { atualizarAposDecisao, haQuanto, linhaDaDecisao, linkDaOrigem, rotuloDoTipo, TIPOS_DE_PEDIDO } from "@/lib/aprovacoes";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { useFiltrosNaUrl } from "@/lib/filtros-url";
import { useFilial } from "@/lib/filial-escolhida";
import { dinheiro } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";

// Referência: docs/telas/html/Aprovacoes-Desktop.dc.html e Aprovacoes-Mobile.dc.html.
// Título, detalhe, indicadores, contagens, resumo e quem pode decidir/cancelar vêm da API (APR-01 a APR-12); a tela não calcula nada.

type Aba = "pendente" | "aprovado" | "recusado" | "meus";

const ABAS: { valor: Aba; rotulo: string }[] = [
  { valor: "pendente", rotulo: "Pendentes" },
  { valor: "aprovado", rotulo: "Aprovadas" },
  { valor: "recusado", rotulo: "Recusadas" },
  { valor: "meus", rotulo: "Meus pedidos" },
];

function Celula({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-md bg-surface px-3.5 py-3">
      <small className="block text-caption text-ink-muted">{rotulo}</small>
      <b className="font-semibold">{valor}</b>
    </div>
  );
}

/** As células do pedido vêm prontas em `p.resumo.celulas` (APR-01 a APR-06); quando `resumo` é `null`, o cartão mostra só título e detalhe. */
function Celulas({ p }: { p: PedidoDeAprovacao }) {
  if (!p.resumo || p.resumo.celulas.length === 0) return null;
  return (
    <div className="grid gap-2 md:grid-cols-[repeat(auto-fit,minmax(150px,1fr))]">
      {p.resumo.celulas.map((c) => (
        <Celula key={c.rotulo} {...c} />
      ))}
    </div>
  );
}

function CartaoDoPedido({ p, agora, maisAntigo, destaque, aoDecidir, aoRecusar, aoCancelar, ocupado }: { p: PedidoDeAprovacao; agora: Date; maisAntigo: boolean; destaque: boolean; aoDecidir: (p: PedidoDeAprovacao) => void; aoRecusar: (p: PedidoDeAprovacao) => void; aoCancelar: (p: PedidoDeAprovacao) => void; ocupado: boolean }) {
  const ver = linkDaOrigem(p.origem);
  const pendente = p.status === "pendente";
  return (
    <article className={`flex flex-col gap-3.5 rounded-[26px] bg-surface-sunken p-5 ${destaque ? "outline outline-2 outline-offset-2 outline-ink" : ""}`} aria-label={p.titulo}>
      <div className="flex flex-wrap items-center gap-2.5">
        <StatusBadge compacto>{rotuloDoTipo(p.tipo)}</StatusBadge>
        <span className="wl-mono text-caption text-ink-muted">{p.tipo}</span>
        {maisAntigo && (
          <StatusBadge tom="alerta" compacto>
            Mais antigo
          </StatusBadge>
        )}
        {!pendente && (
          <StatusBadge tom={p.status === "aprovado" ? "sucesso" : "neutro"} compacto>
            {p.status === "aprovado" ? "Aprovado" : p.status === "recusado" ? "Recusado" : "Cancelado"}
          </StatusBadge>
        )}
        <span className="ml-auto text-caption text-ink-muted md:hidden">{haQuanto(p.pedido_em, agora)}</span>
      </div>
      <div>
        <div className="text-body font-medium">{p.titulo}</div>
        <div className="text-caption text-ink-muted">
          {p.solicitante.nome}
          <span className="hidden md:inline"> · {haQuanto(p.pedido_em, agora)}</span>
          {p.detalhe ? ` · ${p.detalhe}` : ""}
        </div>
      </div>
      <Celulas p={p} />
      {p.resumo?.nota && <p className="m-0 hidden text-caption text-ink-muted md:block">{p.resumo.nota}</p>}
      {!pendente && p.status === "recusado" && p.motivo_recusa && <p className="m-0 text-caption">Motivo da recusa: {p.motivo_recusa}</p>}
      <div className="flex flex-wrap items-center gap-2">
        {ver && (
          <Link href={ver.href} className="wl-btn wl-btn--sm">
            <span className="hidden md:inline">{ver.rotulo}</span>
            <span className="md:hidden">Detalhes</span>
          </Link>
        )}
        <span className="flex-1" />
        {pendente && p.pode_decidir && (
          <>
            <Button compacto disabled={ocupado} onClick={() => aoRecusar(p)}>
              Recusar
            </Button>
            <Button compacto variante="solido" disabled={ocupado} onClick={() => aoDecidir(p)}>
              Aprovar
            </Button>
          </>
        )}
        {p.pode_cancelar && (
          <Button compacto variante="quieto" disabled={ocupado} onClick={() => aoCancelar(p)}>
            Cancelar pedido
          </Button>
        )}
      </div>
    </article>
  );
}

/** Aprovações: os pedidos que a pessoa decide na filial escolhida (aprovar, recusar com motivo) e os que ela mesma fez (cancelar). */
export function ListaAprovacoes({ destaqueId }: { destaqueId?: number }) {
  const { eu } = useSessao();
  const cliente = useQueryClient();
  const agora = useAgora();
  const filial = useFilial()?.nome ?? eu.filiais[0]?.nome;
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("aba") ?? "pendente") as Aba;
  const tipo = (valor("tipo") ?? "") as TipoDoPedido | "";
  const [recusando, setRecusando] = useState<PedidoDeAprovacao | null>(null);
  const [motivo, setMotivo] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);

  const status: StatusDoPedido | undefined = aba === "meus" ? undefined : aba;
  const lista = useQuery({ queryKey: ["aprovacoes", "lista", { aba, tipo }], queryFn: () => aprovacoes.listar({ status, tipo: tipo || undefined, minhas: aba === "meus" }), placeholderData: (a) => a });
  // Contagem do que espera e histórico: duas consultas fixas, independentes da aba escolhida.
  const esperando = useQuery({ queryKey: ["aprovacoes", "esperando"], queryFn: () => aprovacoes.listar({ status: "pendente" }) });
  const aprovadas = useQuery({ queryKey: ["aprovacoes", "decididas", "aprovado"], queryFn: () => aprovacoes.listar({ status: "aprovado" }) });
  const recusadas = useQuery({ queryKey: ["aprovacoes", "decididas", "recusado"], queryFn: () => aprovacoes.listar({ status: "recusado" }) });

  const atualizar = () => atualizarAposDecisao(cliente);
  const aprovar = useMutation({ mutationFn: (p: PedidoDeAprovacao) => aprovacoes.aprovar(p.id).then(() => p), onSuccess: async (p) => (await atualizar(), setAviso(`Aprovado: ${p.titulo}.`)) });
  const recusar = useMutation({
    mutationFn: () => aprovacoes.recusar(recusando?.id ?? 0, motivo.trim()),
    onSuccess: async () => {
      const t = recusando?.titulo;
      setRecusando(null);
      setMotivo("");
      await atualizar();
      setAviso(`Recusado: ${t}. Quem pediu recebe o motivo.`);
    },
  });
  const cancelar = useMutation({ mutationFn: (p: PedidoDeAprovacao) => aprovacoes.cancelar(p.id).then(() => p), onSuccess: async (p) => (await atualizar(), setAviso(`Pedido cancelado: ${p.titulo}.`)) });
  const ocupado = aprovar.isPending || recusar.isPending || cancelar.isPending;

  const pedidos = lista.data?.resultados ?? [];
  const contagens = esperando.data?.contagens ?? lista.data?.contagens;
  const ind = esperando.data?.indicadores ?? lista.data?.indicadores;
  const nEsperando = ind?.esperando.quantidade ?? contagens?.pendente;
  const maisAntigoEm = ind?.esperando.mais_antigo_em ?? esperando.data?.resultados[0]?.pedido_em ?? null;
  const contextoEsperando = ind?.esperando.contexto ?? (maisAntigoEm ? `mais antigo ${haQuanto(maisAntigoEm, agora)}` : null);
  const recentes = [...(aprovadas.data?.resultados ?? []), ...(recusadas.data?.resultados ?? [])].sort((a, b) => (b.decidido_em ?? "").localeCompare(a.decidido_em ?? "")).slice(0, 4);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-3">
        <Link href="/mais" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0">
          <h1 className="text-title md:text-display">Aprovações</h1>
          <p className="mt-1 mb-0 text-body text-ink-muted">
            <span className="hidden md:inline">{filial ? `${filial} · ` : ""}pedidos que dependem de você</span>
            <span className="md:hidden">
              {nEsperando === undefined ? "" : `${nEsperando} esperando você`}
              {contextoEsperando ? ` · ${contextoEsperando}` : ""}
            </span>
          </p>
        </div>
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}

      <div className="hidden md:block">
        <KpiGrid>
          <KpiTile destaque rotulo="Esperando você" valor={String(nEsperando ?? 0)} contexto={contextoEsperando ?? "nenhum pedido esperando"} />
          <KpiTile rotulo={ind?.aprovadas.titulo ?? "Aprovadas"} valor={String(ind?.aprovadas.quantidade ?? 0)} contexto={ind?.aprovadas.contexto ?? undefined} />
          <KpiTile rotulo={ind?.recusadas.titulo ?? "Recusadas"} valor={String(ind?.recusadas.quantidade ?? 0)} contexto={ind?.recusadas.contexto ?? "sempre com motivo"} />
          <KpiTile rotulo={ind?.descontos.titulo ?? "Descontos aprovados"} valor={dinheiro(ind?.descontos.valor_centavos ?? 0)} contexto={ind?.descontos.contexto ?? "em 0 pedidos"} />
        </KpiGrid>
      </div>

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <section className="md:wl-panel flex min-w-0 flex-col gap-4 md:flex-[999_1_560px]" aria-label="Pedidos">
          <div className="flex flex-wrap items-center gap-2">
            <div role="group" aria-label="Situação" className="flex flex-1 gap-2 overflow-x-auto pb-1">
              {ABAS.map((a) => {
                const n = a.valor === "meus" ? undefined : contagens?.[a.valor];
                return (
                  <button
                    key={a.valor}
                    type="button"
                    aria-pressed={a.valor === aba}
                    onClick={() => definir({ aba: a.valor === "pendente" ? null : a.valor })}
                    className={`inline-flex h-[44px] shrink-0 items-center gap-2 rounded-pill px-4 text-body whitespace-nowrap md:h-10 ${a.valor === aba ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
                  >
                    {a.rotulo}
                    {n !== undefined && <span className={`wl-count ${a.valor === aba ? "!bg-brand !text-on-brand" : "!bg-surface"}`}>{n}</span>}
                  </button>
                );
              })}
            </div>
            <select aria-label="Tipo de pedido" value={tipo} onChange={(e) => definir({ tipo: e.target.value })} className="wl-input hidden w-auto md:block">
              <option value="">Todos os tipos</option>
              {TIPOS_DE_PEDIDO.map((t) => (
                <option key={t.valor} value={t.valor}>
                  {t.rotulo}
                </option>
              ))}
            </select>
          </div>

          {lista.isError && (
            <p role="alert" className="text-body">
              {mensagemDoErro(lista.error)}
            </p>
          )}
          {lista.isPending && (
            <p className="text-body text-ink-muted" aria-busy="true">
              Carregando os pedidos…
            </p>
          )}
          {(aprovar.isError || cancelar.isError) && <ErroDoFinanceiro erro={aprovar.error ?? cancelar.error} />}
          {lista.data && pedidos.length === 0 && (
            <p className="py-6 text-center text-body text-ink-muted">
              {aba === "pendente" ? "Nenhum pedido esperando você." : aba === "meus" ? "Você não tem pedido esperando resposta." : "Nenhum pedido nesta situação."}
            </p>
          )}
          {pedidos.map((p, i) => (
            <CartaoDoPedido
              key={p.id}
              p={p}
              agora={agora}
              maisAntigo={aba === "pendente" && i === 0 && pedidos.length > 1}
              destaque={p.id === destaqueId}
              aoDecidir={(x) => aprovar.mutate(x)}
              aoRecusar={(x) => {
                setMotivo("");
                recusar.reset();
                setRecusando(x);
              }}
              aoCancelar={(x) => cancelar.mutate(x)}
              ocupado={ocupado}
            />
          ))}
        </section>

        <aside className="flex min-w-0 flex-col gap-6 md:flex-[1_1_320px]">
          <section className="wl-panel" aria-label="Decididas recentemente">
            <h2 className="mb-2 text-heading">Decididas recentemente</h2>
            {recentes.length === 0 && <p className="text-caption text-ink-muted">Nada decidido ainda.</p>}
            {recentes.map((p) => (
              <div key={p.id} className="flex items-start gap-3 border-b border-line py-3 last:border-b-0">
                <span className={`grid size-7 shrink-0 place-items-center rounded-full ${p.status === "aprovado" ? "bg-success-soft text-success-ink" : "bg-critical-soft text-critical-ink"}`} aria-hidden="true">
                  <Icone de={p.status === "aprovado" ? Check : X} />
                </span>
                <div>
                  <div className="text-body">{p.titulo}</div>
                  <small className="block text-caption text-ink-muted">{linhaDaDecisao(p)}</small>
                </div>
              </div>
            ))}
          </section>
          <section className="wl-panel hidden flex-col gap-3 text-caption md:flex" aria-label="O que passa por aqui">
            <div className="text-body font-medium">O que passa por aqui</div>
            <div>Descontos acima de 5%, cancelamentos de locação, despesas e orçamentos acima de R$ 500, diferença no caixa, desbloqueio de cliente e correção de km para baixo.</div>
            <div>Recusar pede um motivo, que vai para quem pediu.</div>
            <div>Você não aprova pedidos feitos por você mesmo. Tudo fica na auditoria.</div>
          </section>
          <p className="m-0 text-caption text-ink-muted md:hidden">Recusar pede um motivo. Você não aprova pedidos feitos por você.</p>
        </aside>
      </div>

      {recusando && (
        <Dialogo
          aberto
          aoFechar={() => setRecusando(null)}
          fecharAoClicarFora={false}
          titulo="Recusar pedido"
          descricao={recusando.titulo}
          acoes={
            <>
              <Button variante="quieto" onClick={() => setRecusando(null)}>
                Voltar
              </Button>
              <Button variante="solido" disabled={motivo.trim() === "" || recusar.isPending} onClick={() => recusar.mutate()}>
                {recusar.isPending ? "Recusando…" : "Recusar pedido"}
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-3">
            <TextField cheio data-autofocus rotulo="Motivo da recusa" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(recusar.error, "motivo")} dica="Quem pediu recebe o motivo." />
            {recusar.isError && !campoDoErro(recusar.error, "motivo") && <ErroDoFinanceiro erro={recusar.error} />}
          </div>
        </Dialogo>
      )}
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, CelulaDupla, DataTable, KpiGrid, KpiTile, SearchField, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { Paginacao } from "@/components/lista/Paginacao";
import { ErroApi, financeiro, type PendenciaPagamento, type StatusDaPendencia } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { dataHoraCurta, dinheiro } from "@/lib/formatos";
import { Confirmacao } from "./Comuns";
import { DialogoResolverPendencia } from "./DialogoResolverPendencia";

// Referência: docs/telas/html/Pendencias-Pagamento-Desktop.dc.html e Pendencias-Pagamento-Mobile.dc.html.
// O motivo, o detalhe (com o valor do dia e a diferença), a resolução e as ações vêm prontos da API (AUT-05, FIN-03, T-380); a tela não faz conta.

type Aba = "todas" | StatusDaPendencia;

const origemDe = (p: PendenciaPagamento) => [p.origem.codigo, p.origem.parcela].filter(Boolean).join(" · ");

function Situacao({ p }: { p: PendenciaPagamento }) {
  return (
    <StatusBadge tom={p.status === "aberta" ? "alerta" : "sucesso"} compacto>
      {p.status_rotulo}
    </StatusBadge>
  );
}

function Resolver({ p, aoResolver }: { p: PendenciaPagamento; aoResolver: (p: PendenciaPagamento) => void }) {
  if (p.status === "resolvida") return p.resolucao ? <span className="text-caption text-ink-muted">{p.resolucao.texto}</span> : null;
  if (!p.acoes.resolver) return null;
  return (
    <Button variante="solido" compacto onClick={() => aoResolver(p)}>
      Resolver
    </Button>
  );
}

function CartaoDaPendencia({ p, aoResolver }: { p: PendenciaPagamento; aoResolver: (p: PendenciaPagamento) => void }) {
  return (
    <article className="flex flex-col gap-2 border-b border-line py-[14px] last:border-b-0">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="m-0 text-body font-medium">{p.cliente.nome}</p>
          <p className="m-0 wl-mono text-caption text-ink-muted">
            {origemDe(p)} · {p.cobranca.id_no_parceiro}
          </p>
        </div>
        {p.valor_pago_centavos !== null && <span className="shrink-0 text-body font-semibold">{dinheiro(p.valor_pago_centavos)}</span>}
      </div>
      <p className="m-0 text-caption text-ink-muted">
        <span className="font-medium text-ink">{p.motivo_rotulo}.</span> {p.detalhe}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <Situacao p={p} />
        <span className="text-caption text-ink-muted">{dataHoraCurta(p.criado_em)}</span>
      </div>
      <Resolver p={p} aoResolver={aoResolver} />
    </article>
  );
}

/** Pendências do pagamento: avisos do parceiro que a baixa automática não resolveu e que o financeiro decide. */
export function ListaPendencias() {
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("aba") ?? "aberta") as Aba;
  const cursor = valor("cursor") ?? undefined;
  const buscaNaUrl = valor("busca") ?? "";
  const [busca, setBusca] = useBuscaNaUrl(definir, buscaNaUrl);
  const [resolvendo, setResolvendo] = useState<PendenciaPagamento | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const consulta = useQuery({
    queryKey: ["pendencias-pagamento", { aba, cursor, busca: buscaNaUrl }],
    queryFn: () => financeiro.listarPendencias({ status: aba, busca: buscaNaUrl || undefined, cursor }),
    placeholderData: (anterior) => anterior,
    retry: false,
  });
  const d = consulta.data;
  const c = d?.contagens;
  const pendencias = d?.resultados ?? [];
  const total = c ? (aba === "aberta" ? c.aberta : aba === "resolvida" ? c.resolvida : c.todas) : pendencias.length;
  // Plano sem recebimento pelo parceiro (PLT-12): a API recusa e a tela explica, sem lista nem indicadores.
  const semPlano = consulta.error instanceof ErroApi && consulta.error.codigo === "PLT-12";

  const colunas: ColunaTabela<PendenciaPagamento>[] = [
    { chave: "data", titulo: "Data e hora", mono: true, celula: (x) => <span className="wl-mono">{dataHoraCurta(x.criado_em)}</span> },
    { chave: "parceiro", titulo: "ID no parceiro", celula: (x) => <CelulaDupla principal={<span className="wl-mono">{x.cobranca.id_no_parceiro}</span>} secundaria={x.cobranca.forma_rotulo} /> },
    { chave: "cliente", titulo: "Cliente e origem", celula: (x) => <CelulaDupla principal={x.cliente.nome} secundaria={origemDe(x)} /> },
    { chave: "motivo", titulo: "Motivo da pendência", celula: (x) => <CelulaDupla principal={x.motivo_rotulo} secundaria={x.detalhe} /> },
    { chave: "valor", titulo: "Valor no parceiro", celula: (x) => <span className="font-medium whitespace-nowrap">{x.valor_pago_centavos === null ? "—" : dinheiro(x.valor_pago_centavos)}</span> },
    { chave: "situacao", titulo: "Situação", celula: (x) => <Situacao p={x} /> },
    { chave: "resolver", titulo: "", celula: (x) => <Resolver p={x} aoResolver={setResolvendo} /> },
  ];
  const abas = [
    { valor: "aberta", rotulo: `Abertas${c ? ` ${c.aberta}` : ""}` },
    { valor: "resolvida", rotulo: `Resolvidas${c ? ` ${c.resolvida}` : ""}` },
    { valor: "todas", rotulo: `Todas${c ? ` ${c.todas}` : ""}` },
  ] as const;

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-title md:text-display">Pendências do pagamento</h1>
        <p className="mt-1 text-body text-ink-muted">
          <span className="hidden md:inline">Avisos do parceiro com divergência ou sem cobrança ativa</span>
          <span className="md:hidden">Avisos do parceiro de pagamento</span>
        </p>
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}

      {semPlano && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}

      {!semPlano && (
        <>
          <p className="rounded-lg bg-surface-sunken p-4 text-body text-ink-muted">
            <strong className="font-medium text-ink">Proteção do caixa.</strong> Quando o parceiro avisa um pagamento com valor diferente do previsto, uma conta que já não estava aberta ou um estorno, a baixa automática é bloqueada e a decisão fica com você.
          </p>

          {d && (
            <KpiGrid>
              <KpiTile destaque rotulo="Pendências abertas" valor={String(d.indicadores.abertas.quantidade)} contexto={d.indicadores.abertas.texto} />
              <KpiTile rotulo="Resolvidas no mês" valor={String(d.indicadores.resolvidas.quantidade)} contexto={d.indicadores.resolvidas.texto} />
            </KpiGrid>
          )}

          <section className="wl-panel" aria-label="Pendências do pagamento">
            <div className="mb-5 flex flex-wrap items-center gap-3">
              <SegmentedControl rotulo="Situação" opcoes={abas} valor={aba} aoMudar={(v) => definir({ aba: v === "aberta" ? null : v })} />
              <div className="ml-auto w-full md:w-[260px] [&_.wl-search]:!w-full">
                <SearchField placeholder="Buscar cliente, locação ou cobrança" aria-label="Buscar pendência" value={busca} onChange={(e) => setBusca(e.target.value)} />
              </div>
            </div>

            {consulta.isError && (
              <p role="alert" className="text-body">
                {mensagemDoErro(consulta.error)}
              </p>
            )}
            {consulta.isPending && (
              <p className="text-body text-ink-muted" aria-busy="true">
                Carregando as pendências…
              </p>
            )}
            {d && pendencias.length === 0 && (
              <p className="py-6 text-center text-body text-ink-muted">{buscaNaUrl ? "Nenhuma pendência com essa busca. Mude o termo." : aba === "aberta" ? "Nenhuma pendência aberta." : "Nenhuma pendência nesta situação."}</p>
            )}
            {d && pendencias.length > 0 && (
              <>
                <div className="hidden overflow-x-auto md:block">
                  <DataTable colunas={colunas} linhas={pendencias} chaveDaLinha={(x) => String(x.id)} legenda="Pendências do pagamento" />
                </div>
                <div className="flex flex-col md:hidden">
                  {pendencias.map((x) => (
                    <CartaoDaPendencia key={x.id} p={x} aoResolver={setResolvendo} />
                  ))}
                </div>
                <Paginacao texto={`Mostrando ${pendencias.length} de ${total}`} anterior={d.anterior} proximo={d.proximo} aoIr={(cur) => definir({ cursor: cur })} />
              </>
            )}
          </section>
        </>
      )}

      {resolvendo && (
        <DialogoResolverPendencia
          pendencia={resolvendo}
          aoFechar={() => setResolvendo(null)}
          aoConcluir={(texto) => {
            setResolvendo(null);
            setAviso(texto);
          }}
        />
      )}
    </div>
  );
}

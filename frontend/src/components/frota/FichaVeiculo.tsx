"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { ArrowLeftRight, ChevronLeft, Ellipsis, Tag, Wrench } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Button, DataTable, Icone, KpiGrid, KpiTile, Panel, StatusBadge, type ColunaTabela } from "@/design-system";
import {
  veiculos,
  type DocumentoVeiculo,
  type LocacaoDoVeiculo,
  type LocacoesDoVeiculo,
  type ManutencaoDoVeiculo,
  type ManutencoesDoVeiculo,
  type VeiculoDetalhe,
} from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, dinheiro, dinheiroSemZeros, iniciais, km, mesAno, percentual, placa } from "@/lib/formatos";
import { situacaoDoDocumento } from "@/lib/frota";
import { temNoMenu } from "@/lib/menu";
import { useSessao } from "@/lib/sessao";
import { tomDoStatus } from "@/lib/tom";

// Referência: docs/telas/html/Veiculo-Desktop.dc.html e Veiculo-Mobile.dc.html.
// As duas versões são árvores separadas, escolhidas por um <div> com hidden / md:hidden. A classe wl- define `display`
// e vence o utilitário, então hidden e md:hidden nunca vão no mesmo elemento que uma classe wl-.

const EM_BREVE = "Ainda não está disponível";

function Linha({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

const COLUNAS_LOCACOES: ColunaTabela<LocacaoDoVeiculo>[] = [
  { chave: "codigo", titulo: "Contrato", mono: true },
  { chave: "cliente_nome", titulo: "Cliente" },
  { chave: "periodo", titulo: "Período", celula: (l) => `${dataCurta(l.inicio)} → ${dataCurta(l.fim)}` },
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

const COLUNAS_MANUTENCOES: ColunaTabela<ManutencaoDoVeiculo>[] = [
  { chave: "servico", titulo: "Serviço" },
  { chave: "data", titulo: "Data", celula: (m) => dataCurta(m.data) },
  { chave: "km", titulo: "Km", celula: (m) => km(m.km) },
  { chave: "custo", titulo: "Custo", celula: (m) => dinheiro(m.custo_centavos) },
];

type Consultas = {
  docs: UseQueryResult<DocumentoVeiculo[]>;
  locacoes: UseQueryResult<LocacoesDoVeiculo>;
  /** `null` enquanto o módulo de manutenção não está no menu: a seção não aparece (lista vazia diria "nenhuma manutenção"). */
  manutencoes: UseQueryResult<ManutencoesDoVeiculo> | null;
};

const proximaManutencao = (v: VeiculoDetalhe) => (v.manutencao?.proxima ? `próxima: ${v.manutencao.proxima.servico.toLowerCase()} aos ${km(v.manutencao.proxima.km)}` : undefined);

function SituacaoDocumento({ d }: { d: DocumentoVeiculo }) {
  const s = situacaoDoDocumento(d.situacao, d.dias_para_vencer, d.situacao_rotulo);
  return (
    <StatusBadge tom={s.tom} compacto>
      {s.rotulo}
    </StatusBadge>
  );
}

function ListaDeDocumentos({ docs }: { docs: UseQueryResult<DocumentoVeiculo[]> }) {
  if (docs.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(docs.error)}
      </p>
    );
  if (!docs.data) return <p className="text-body text-ink-muted">Carregando os documentos…</p>;
  if (docs.data.length === 0) return <p className="text-body text-ink-muted">Nenhum documento cadastrado.</p>;
  return (
    <dl>
      {docs.data.map((d) => (
        <Linha key={d.id} rotulo={d.rotulo}>
          <SituacaoDocumento d={d} />
        </Linha>
      ))}
    </dl>
  );
}

/** Próxima manutenção como a API manda (serviço e km). "Faltam X km", a barra e o "depois" ficam para quando a API devolver (pedido ao arquiteto, T-242). */
function ProximaManutencao({ v }: { v: VeiculoDetalhe }) {
  const proxima = v.manutencao?.proxima;
  if (!proxima) return null;
  return (
    <div className="flex flex-col gap-1">
      <span className="text-caption text-ink-muted">Próxima manutenção</span>
      <span className="text-body font-medium">{proxima.servico}</span>
      <span className="text-caption text-ink-muted">aos {km(proxima.km)}</span>
      {v.manutencao?.alerta && <span className="text-caption text-ink-muted">{v.manutencao.alerta}</span>}
    </div>
  );
}

/** "Agora" do desktop: a locação em curso e a próxima manutenção, só com o que a API manda. */
function AgoraDesktop({ v }: { v: VeiculoDetalhe }) {
  const atual = v.locacao_atual;
  if (!atual && !v.manutencao?.proxima) return null;
  return (
    <Panel
      titulo="Agora"
      acao={
        <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
          {atual ? `${v.situacao.rotulo} desde ${dataCurta(atual.inicio)}` : v.situacao.rotulo}
        </StatusBadge>
      }
    >
      <div className="grid gap-6 md:grid-cols-2">
        {atual && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <div aria-hidden="true" className="grid size-10 shrink-0 place-items-center rounded-full bg-brand text-[13px] font-semibold text-on-brand">
                {iniciais(atual.cliente_nome)}
              </div>
              <div className="min-w-0">
                <div className="text-body font-medium">{atual.cliente_nome}</div>
                <div className="wl-mono text-caption text-ink-muted">{atual.codigo}</div>
              </div>
            </div>
            <dl>
              <Linha rotulo="Período">
                {dataCurta(atual.inicio)} → {dataCurta(atual.fim_previsto)}
              </Linha>
              {atual.alerta && (
                <Linha rotulo="Alerta">
                  <StatusBadge tom="alerta" compacto>
                    {atual.alerta}
                  </StatusBadge>
                </Linha>
              )}
            </dl>
            <div>
              <Link href={`/locacoes/${atual.id}`} className="wl-btn wl-btn--sm">
                Ver locação
              </Link>
            </div>
          </div>
        )}
        <ProximaManutencao v={v} />
      </div>
    </Panel>
  );
}

function FichaDesktop({ v, docs, locacoes, manutencoes }: { v: VeiculoDetalhe } & Consultas) {
  const fin = v.indicadores_financeiros;
  const podeAgir = v.acoes.editar;
  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Caminho" className="flex gap-[6px] text-caption text-ink-muted">
        <Link href="/veiculos" className="text-ink-muted no-underline">
          Veículos
        </Link>{" "}
        / <span>{placa(v.placa)}</span>
      </nav>

      <header className="-mt-2 flex flex-wrap items-center gap-4">
        <div>
          <h1 className="text-display">
            {v.marca} {v.modelo}
          </h1>
          <div className="mt-2 flex items-center gap-2">
            <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
              {v.situacao.rotulo}
            </StatusBadge>
            <span className="wl-mono text-[13px] text-ink-muted">{placa(v.placa)}</span>
            <span className="text-[13px] text-ink-muted">
              · {v.ano_modelo} · {v.cor} · {v.filial.nome}
            </span>
          </div>
        </div>
        {podeAgir && (
          <div className="ml-auto flex flex-wrap gap-2">
            <Button disabled title={EM_BREVE}>
              Editar
            </Button>
            <Button disabled title={EM_BREVE} icone={<Icone de={ArrowLeftRight} />}>
              Movimentar
            </Button>
            <Button disabled title={EM_BREVE} icone={<Icone de={Wrench} />}>
              Mandar para oficina
            </Button>
            <Button variante="solido" disabled title={v.acoes.colocar_a_venda ? EM_BREVE : "Só um veículo disponível pode ir à venda"} icone={<Icone de={Tag} />}>
              Colocar à venda
            </Button>
          </div>
        )}
      </header>

      <KpiGrid>
        {fin && <KpiTile destaque rotulo="Rendeu no ano" valor={dinheiroSemZeros(fin.rendeu_no_ano_centavos)} contexto="locações − custos" />}
        <KpiTile rotulo="Ocupação" valor={percentual(v.ocupacao.pct)} contexto={`últimos ${v.ocupacao.periodo_dias} dias`} />
        {fin && <KpiTile rotulo="Custo de manutenção" valor={dinheiroSemZeros(fin.custo_manutencao_ano_centavos)} contexto="no ano" />}
        <KpiTile rotulo="Km atual" valor={new Intl.NumberFormat("pt-BR").format(v.km_atual)} contexto={`atualizado ${dataCurta(v.km_atualizado_em)}`} />
      </KpiGrid>

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-6">
          <AgoraDesktop v={v} />

          <Panel titulo="Locações" acao={locacoes.data ? <span className="text-[13px] text-ink-muted">{locacoes.data.total} no total</span> : undefined}>
            {locacoes.isError && <p role="alert">{mensagemDoErro(locacoes.error)}</p>}
            {locacoes.data?.resultados.length === 0 && <p className="text-body text-ink-muted">Este veículo ainda não foi alugado.</p>}
            {locacoes.data && locacoes.data.resultados.length > 0 && (
              <DataTable colunas={COLUNAS_LOCACOES} linhas={locacoes.data.resultados} chaveDaLinha={(l) => String(l.id)} legenda="Locações do veículo" />
            )}
          </Panel>

          {manutencoes && (
          <Panel titulo="Manutenções" acao={proximaManutencao(v) ? <span className="text-[13px] text-ink-muted">{proximaManutencao(v)}</span> : undefined}>
            {manutencoes.isError && <p role="alert">{mensagemDoErro(manutencoes.error)}</p>}
            {manutencoes.data?.resultados.length === 0 && <p className="text-body text-ink-muted">Nenhuma manutenção registrada.</p>}
            {manutencoes.data && manutencoes.data.resultados.length > 0 && (
              <DataTable colunas={COLUNAS_MANUTENCOES} linhas={manutencoes.data.resultados} chaveDaLinha={(m) => String(m.id)} legenda="Manutenções do veículo" />
            )}
          </Panel>
          )}
        </div>

        <aside className="flex min-w-0 flex-[1_1_340px] flex-col gap-6">
          <section className="wl-panel">
            <h2 className="mb-1 text-[20px] font-semibold leading-[26px]">Dados</h2>
            <dl>
              <Linha rotulo="Chassi">{v.chassi}</Linha>
              {v.renavam && <Linha rotulo="Renavam">{v.renavam}</Linha>}
              {v.valor_compra_centavos != null && (
                <Linha rotulo="Compra">
                  {v.data_compra ? `${mesAno(v.data_compra)} · ` : ""}
                  {dinheiroSemZeros(v.valor_compra_centavos)}
                </Linha>
              )}
              {v.referencia_fipe_centavos != null && <Linha rotulo="Valor de venda (FIPE)">{dinheiroSemZeros(v.referencia_fipe_centavos)}</Linha>}
              {v.valor_venda_centavos != null && <Linha rotulo="À venda por">{dinheiroSemZeros(v.valor_venda_centavos)}</Linha>}
              <Linha rotulo="Categoria">{v.categoria.nome}</Linha>
              {v.preco_vigente && <Linha rotulo="Preço de hoje">Semanal {dinheiro(v.preco_vigente.semanal_centavos)}</Linha>}
            </dl>
          </section>
          <section className="wl-panel">
            <h2 className="mb-1 text-[20px] font-semibold leading-[26px]">Documentos</h2>
            <ListaDeDocumentos docs={docs} />
          </section>
        </aside>
      </div>
    </div>
  );
}

function CartaoDoCelular({ titulo, acao, children }: { titulo: string; acao?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-heading">{titulo}</h2>
        {acao}
      </div>
      {children}
    </section>
  );
}

// O KpiTile não tem variante de celular: o cartão da referência (fundo surface, 28px) entra por seletor de descendente.
const KPI_DO_CELULAR = "[&_.wl-kpi]:bg-surface [&_.wl-kpi]:px-4 [&_.wl-kpi]:py-[14px] [&_.wl-kpi__value]:text-[28px] [&_.wl-kpi__value]:leading-8 [&_.wl-kpi__meta]:text-[13px]";

function FichaCelular({ v, docs, manutencoes }: { v: VeiculoDetalhe } & Omit<Consultas, "locacoes">) {
  const fin = v.indicadores_financeiros;
  const atual = v.locacao_atual;
  return (
    <div className="flex flex-col gap-3">
      <header className="flex items-center gap-3 pt-2">
        <Link href="/veiculos" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm shrink-0" style={{ width: 44, height: 44 }}>
          <Icone de={ChevronLeft} />
        </Link>
        <div className="flex min-w-0 flex-1 flex-col">
          <h1 className="truncate text-[20px] font-semibold leading-normal tracking-[-0.01em]">
            {v.marca} {v.modelo}
          </h1>
          <span className="text-[13px] leading-[18px] text-ink-muted">
            {placa(v.placa)} · {v.ano_modelo} · {v.situacao.rotulo.toLowerCase()}
          </span>
        </div>
        <button type="button" className="wl-icon-btn wl-icon-btn--sm" aria-label="Mais ações" disabled title={EM_BREVE} style={{ width: 44, height: 44 }}>
          <Icone de={Ellipsis} />
        </button>
      </header>

      <div className={`grid grid-cols-2 gap-2 ${KPI_DO_CELULAR}`}>
        {fin && <KpiTile rotulo="Rendeu no ano" valor={dinheiroSemZeros(fin.rendeu_no_ano_centavos)} contexto="locações − custos" />}
        <KpiTile rotulo="Ocupação" valor={percentual(v.ocupacao.pct)} contexto={`${v.ocupacao.periodo_dias} dias`} />
      </div>

      {atual && (
        <CartaoDoCelular
          titulo="Agora"
          acao={
            <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
              {v.situacao.rotulo}
            </StatusBadge>
          }
        >
          <dl>
            <Linha rotulo="Cliente">{atual.cliente_nome}</Linha>
            <Linha rotulo="Contrato">
              <span className="wl-mono">{atual.codigo}</span>
            </Linha>
            <Linha rotulo="Devolve">{dataCurta(atual.fim_previsto)}</Linha>
            {atual.alerta && (
              <Linha rotulo="Alerta">
                <StatusBadge tom="alerta" compacto>
                  {atual.alerta}
                </StatusBadge>
              </Linha>
            )}
          </dl>
        </CartaoDoCelular>
      )}

      {v.manutencao?.proxima && (
        <CartaoDoCelular titulo="Próxima manutenção">
          <p className="mt-2 text-body">
            {v.manutencao.proxima.servico} aos {km(v.manutencao.proxima.km)}
          </p>
          {v.manutencao.alerta && <p className="mt-1 text-caption text-ink-muted">{v.manutencao.alerta}</p>}
        </CartaoDoCelular>
      )}

      <CartaoDoCelular titulo="Documentos">
        <ListaDeDocumentos docs={docs} />
      </CartaoDoCelular>

      {manutencoes && (
      <CartaoDoCelular titulo="Manutenções">
        {manutencoes.isError && <p role="alert">{mensagemDoErro(manutencoes.error)}</p>}
        {manutencoes.data?.resultados.length === 0 && <p className="text-body text-ink-muted">Nenhuma manutenção registrada.</p>}
        {manutencoes.data && manutencoes.data.resultados.length > 0 && (
          <dl>
            {manutencoes.data.resultados.map((m) => (
              <Linha key={m.id} rotulo={`${m.servico} · ${dataCurta(m.data)}`}>
                {dinheiro(m.custo_centavos)}
              </Linha>
            ))}
          </dl>
        )}
      </CartaoDoCelular>
      )}

      {v.acoes.editar && (
        <div className="grid grid-cols-2 gap-2">
          <Button disabled title={EM_BREVE}>
            Oficina
          </Button>
          <Button variante="solido" disabled title={v.acoes.colocar_a_venda ? EM_BREVE : "Só um veículo disponível pode ir à venda"}>
            Colocar à venda
          </Button>
        </div>
      )}
    </div>
  );
}

/** Ficha do veículo (T-102). Tudo vem da API: situação, indicadores, documentos, locações e manutenções. O bloco financeiro some quando ela não o devolve. */
export function FichaVeiculo({ id }: { id: number }) {
  const ficha = useQuery({ queryKey: ["veiculo", id], queryFn: () => veiculos.obter(id) });
  const docs = useQuery({ queryKey: ["veiculo", id, "documentos"], queryFn: () => veiculos.documentos(id) });
  const locacoes = useQuery({ queryKey: ["veiculo", id, "locacoes"], queryFn: () => veiculos.locacoes(id) });
  const { eu } = useSessao();
  const comManutencoes = temNoMenu(eu.navegacao, "manutencoes");
  const consultaManutencoes = useQuery({ queryKey: ["veiculo", id, "manutencoes"], queryFn: () => veiculos.manutencoes(id), enabled: comManutencoes });
  const manutencoes = comManutencoes ? consultaManutencoes : null;

  if (ficha.isError) {
    return (
      <div className="flex flex-col gap-4">
        <Link href="/veiculos" className="text-body text-ink-muted">
          Veículos
        </Link>
        <p role="alert" className="wl-panel text-body">
          {mensagemDoErro(ficha.error)}
        </p>
      </div>
    );
  }
  const v = ficha.data;
  if (!v) {
    return (
      <p className="wl-panel text-body text-ink-muted" aria-busy="true">
        Carregando o veículo…
      </p>
    );
  }

  return (
    <>
      <div className="hidden md:block">
        <FichaDesktop v={v} docs={docs} locacoes={locacoes} manutencoes={manutencoes} />
      </div>
      <div className="md:hidden">
        <FichaCelular v={v} docs={docs} manutencoes={manutencoes} />
      </div>
    </>
  );
}

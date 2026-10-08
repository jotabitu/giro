"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import type { ReactNode } from "react";
import { DataTable, KpiGrid, KpiTile, Panel, StatusBadge, type ColunaTabela } from "@/design-system";
import { veiculos, type DocumentoVeiculo, type LocacaoDoVeiculo, type ManutencaoDoVeiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, dinheiro, km, mesAno, percentual, placa } from "@/lib/formatos";
import { situacaoDoDocumento } from "@/lib/frota";
import { tomDoStatus } from "@/lib/tom";

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
  { chave: "km", titulo: "Km", mono: true, celula: (m) => km(m.km) },
  { chave: "custo", titulo: "Custo", mono: true, celula: (m) => dinheiro(m.custo_centavos) },
];

function Documentos({ itens }: { itens: DocumentoVeiculo[] }) {
  return (
    <Panel titulo="Documentos">
      {itens.length === 0 ? (
        <p className="text-body text-ink-muted">Nenhum documento cadastrado.</p>
      ) : (
        <dl>
          {itens.map((d) => {
            const s = situacaoDoDocumento(d.situacao, d.dias_para_vencer);
            return (
              <Linha key={d.id} rotulo={d.rotulo}>
                <StatusBadge tom={s.tom} compacto>
                  {s.rotulo}
                </StatusBadge>
              </Linha>
            );
          })}
        </dl>
      )}
    </Panel>
  );
}

/** Ficha do veículo. Indicadores, situação, documentos e listas vêm da API; o bloco financeiro some quando ela não o devolve. */
export function FichaVeiculo({ id }: { id: number }) {
  const ficha = useQuery({ queryKey: ["veiculo", id], queryFn: () => veiculos.obter(id) });
  const docs = useQuery({ queryKey: ["veiculo", id, "documentos"], queryFn: () => veiculos.documentos(id) });
  const locacoes = useQuery({ queryKey: ["veiculo", id, "locacoes"], queryFn: () => veiculos.locacoes(id) });
  const manutencoes = useQuery({ queryKey: ["veiculo", id, "manutencoes"], queryFn: () => veiculos.manutencoes(id) });

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

  const fin = v.indicadores_financeiros;
  const atual = v.locacao_atual;
  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Caminho" className="text-body text-ink-muted">
        <Link href="/veiculos" className="text-ink">
          Veículos
        </Link>{" "}
        / <span className="wl-mono">{placa(v.placa)}</span>
      </nav>

      <header>
        <h1 className="text-title md:text-display">
          {v.marca} {v.modelo}
        </h1>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
          <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
            {v.situacao.rotulo}
          </StatusBadge>
          <span className="wl-mono text-caption text-ink-muted">{placa(v.placa)}</span>
          <span className="text-caption text-ink-muted">
            · {v.ano_modelo} · {v.cor} · {v.filial.nome}
          </span>
        </div>
      </header>

      <KpiGrid>
        {fin && <KpiTile destaque rotulo="Rendeu no ano" valor={dinheiro(fin.rendeu_no_ano_centavos)} contexto="locações − custos" />}
        <KpiTile rotulo="Ocupação" valor={percentual(v.ocupacao.pct)} contexto={`últimos ${v.ocupacao.periodo_dias} dias`} />
        {fin && <KpiTile rotulo="Custo de manutenção" valor={dinheiro(fin.custo_manutencao_ano_centavos)} contexto="no ano" />}
        <KpiTile rotulo="Km atual" valor={km(v.km_atual)} contexto={`atualizado ${dataCurta(v.km_atualizado_em)}`} />
      </KpiGrid>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-6">
          {atual && (
            <Panel
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
              </dl>
            </Panel>
          )}

          <Panel titulo="Locações" subtitulo={locacoes.data ? `${locacoes.data.length} no total` : undefined}>
            {locacoes.isError && <p role="alert">{mensagemDoErro(locacoes.error)}</p>}
            {locacoes.data?.length === 0 && <p className="text-body text-ink-muted">Este veículo ainda não foi alugado.</p>}
            {locacoes.data && locacoes.data.length > 0 && (
              <DataTable colunas={COLUNAS_LOCACOES} linhas={locacoes.data} chaveDaLinha={(l) => String(l.id)} legenda="Locações do veículo" />
            )}
          </Panel>

          <Panel titulo="Manutenções" subtitulo={manutencoes.data?.proxima ? `próxima: ${manutencoes.data.proxima}` : undefined}>
            {manutencoes.isError && <p role="alert">{mensagemDoErro(manutencoes.error)}</p>}
            {manutencoes.data?.resultados.length === 0 && <p className="text-body text-ink-muted">Nenhuma manutenção registrada.</p>}
            {manutencoes.data && manutencoes.data.resultados.length > 0 && (
              <DataTable colunas={COLUNAS_MANUTENCOES} linhas={manutencoes.data.resultados} chaveDaLinha={(m) => String(m.id)} legenda="Manutenções do veículo" />
            )}
          </Panel>
        </div>

        <aside className="flex flex-col gap-6">
          <Panel titulo="Dados">
            <dl>
              <Linha rotulo="Chassi">
                <span className="wl-mono">{v.chassi}</span>
              </Linha>
              {v.renavam && (
                <Linha rotulo="Renavam">
                  <span className="wl-mono">{v.renavam}</span>
                </Linha>
              )}
              <Linha rotulo="Categoria">{v.categoria.nome}</Linha>
              {v.valor_compra_centavos !== null && (
                <Linha rotulo="Compra">
                  {v.data_compra ? `${mesAno(v.data_compra)} · ` : ""}
                  {dinheiro(v.valor_compra_centavos)}
                </Linha>
              )}
              {v.referencia_fipe_centavos !== null && <Linha rotulo="Referência FIPE">{dinheiro(v.referencia_fipe_centavos)}</Linha>}
              {v.valor_venda_centavos !== null && <Linha rotulo="Valor de venda">{dinheiro(v.valor_venda_centavos)}</Linha>}
              <Linha rotulo="Diária">{dinheiro(v.preco_vigente.diaria_centavos)}</Linha>
              <Linha rotulo="Semanal">{dinheiro(v.preco_vigente.semanal_centavos)}</Linha>
              <Linha rotulo="Mensal">{dinheiro(v.preco_vigente.mensal_centavos)}</Linha>
              <Linha rotulo="Caução">{dinheiro(v.preco_vigente.caucao_centavos)}</Linha>
            </dl>
          </Panel>
          {docs.isError ? <p role="alert">{mensagemDoErro(docs.error)}</p> : <Documentos itens={docs.data ?? []} />}
        </aside>
      </div>
    </div>
  );
}


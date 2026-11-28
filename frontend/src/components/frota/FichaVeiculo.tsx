"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowLeftRight, ChevronLeft, Pencil, Tag, Trash2, Truck, Wrench } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { type AcaoDeStatus, AvisoDaAcao, JanelaDeStatus, MaisAcoesDoCelular } from "./AcoesDeStatus";
import { AluguelDesativado } from "./AluguelDesativado";
import { ExcluirCadastro } from "@/components/comum/ExcluirCadastro";
import { Button, DataTable, Icone, KpiGrid, KpiTile, LinhaDeAcao, Panel, PainelDeAcoes, SeparadorDeAcoes, StatusBadge, type ColunaTabela } from "@/design-system";
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
import { dataCurta, dinheiro, dinheiroSemZeros, km, mesAno, percentual, placa } from "@/lib/formatos";
import { situacaoDoDocumento } from "@/lib/frota";
import { temNoMenu } from "@/lib/menu";
import { DespesasDoVeiculo } from "./DespesasDoVeiculo";
import { PrecosNaFicha } from "@/components/precos-veiculo/PrecosNaFicha";
import {
  AgoraDesktop,
  FotosEAvarias,
  FotosEAvariasCelular,
  LimiteDaEmpresa,
  MovimentacoesCelular,
  MovimentacoesDoVeiculo,
  mostraEstoque,
  SeloDoEstoque,
  VendasDoVeiculo,
} from "./FichaBlocos";
import { GaleriaNaFicha, GaleriaNaFichaCelular } from "./GaleriaNaFicha";
import { useSessao } from "@/lib/sessao";
import { tomDoStatus } from "@/lib/tom";
import { rotuloDaEspecie, rotuloDoCombustivel } from "@/lib/veiculos";

// Referência: docs/telas/html/Veiculo-Desktop.dc.html e Veiculo-Mobile.dc.html.
// As duas versões são árvores separadas, escolhidas por um <div> com hidden / md:hidden. A classe wl- define `display`
// e vence o utilitário, então hidden e md:hidden nunca vão no mesmo elemento que uma classe wl-.

const EM_BREVE = "Ainda não está disponível";

function Linha({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

const VAZIO = "—";
const numeroBr = (n: number) => new Intl.NumberFormat("pt-BR").format(n);

/**
 * Combustível, dados do CRLV-e, rastreador e anotações (VEI-09). Campo vazio é "—". O número do motor e as observações só têm linha quando a API os
 * mandou (administrador e gerente); para os outros perfis a ficha não deixa espaço (CA-421-12). A API decide, a tela mostra.
 */
function LinhasDoDocumento({ v }: { v: VeiculoDetalhe }) {
  const d = v.documento;
  const especieETipo = [rotuloDaEspecie(d.especie), d.tipo].filter(Boolean).join(" · ");
  const { numero, empresa } = v.rastreador;
  return (
    <dl>
      <Linha rotulo="Combustível">{rotuloDoCombustivel(v.combustivel) ?? VAZIO}</Linha>
      <Linha rotulo="Potência">{d.potencia_cv != null ? `${numeroBr(d.potencia_cv)} cv` : VAZIO}</Linha>
      <Linha rotulo="Cilindrada">{d.cilindrada_cc != null ? `${numeroBr(d.cilindrada_cc)} cc` : VAZIO}</Linha>
      <Linha rotulo="Espécie e tipo">{especieETipo || VAZIO}</Linha>
      <Linha rotulo="Carroceria">{d.carroceria ?? VAZIO}</Linha>
      <Linha rotulo="Lotação">{d.lotacao != null ? (d.lotacao === 1 ? "1 pessoa" : `${d.lotacao} pessoas`) : VAZIO}</Linha>
      <Linha rotulo="Peso bruto total">{d.peso_bruto_kg != null ? `${numeroBr(d.peso_bruto_kg)} kg` : VAZIO}</Linha>
      {"numero_motor" in d && <Linha rotulo="Número do motor">{d.numero_motor ? <span className="wl-mono">{d.numero_motor}</span> : VAZIO}</Linha>}
      {"observacoes" in d && <Linha rotulo="Observações do CRLV-e">{d.observacoes ? <span className="whitespace-pre-line">{d.observacoes}</span> : VAZIO}</Linha>}
      <Linha rotulo="Rastreador">
        {numero || empresa ? (
          <>
            {numero && <span className="wl-mono">{numero}</span>}
            {numero && empresa ? " · " : ""}
            {empresa}
          </>
        ) : (
          VAZIO
        )}
      </Linha>
      <Linha rotulo="Anotações">{v.anotacoes ? <span className="whitespace-pre-line">{v.anotacoes}</span> : VAZIO}</Linha>
    </dl>
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
  /** `null` sem `pode.locacoes_ver` (T-458): a seção não aparece e a ficha nem pede as locações. */
  locacoes: UseQueryResult<LocacoesDoVeiculo> | null;
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
          <span className="inline-flex flex-wrap items-center justify-end gap-3">
            <SituacaoDocumento d={d} />
            <AbrirDocumento d={d} />
          </span>
        </Linha>
      ))}
    </dl>
  );
}

/** Abre o PDF ou a imagem numa aba nova pela URL assinada da API (vale 15 min, AUD-05). Sem arquivo, diz isso em texto. */
export function AbrirDocumento({ d }: { d: Pick<DocumentoVeiculo, "rotulo" | "arquivo"> }) {
  if (!d.arquivo) return <span className="text-caption text-ink-muted">Sem arquivo</span>;
  return (
    <a href={d.arquivo.url} target="_blank" rel="noopener noreferrer" aria-label={`Abrir ${d.rotulo}: ${d.arquivo.nome}`} className="inline-flex min-h-[44px] items-center text-body text-ink underline md:min-h-0">
      Abrir
    </a>
  );
}

/** Histórico do veículo: todos os documentos, os renovados ficam como "Substituído". Carrega só quando a pessoa abre. */
function HistoricoDeDocumentos({ id }: { id: number }) {
  const [aberto, setAberto] = useState(false);
  const historico = useQuery({ queryKey: ["veiculo", id, "documentos", "historico"], queryFn: () => veiculos.historicoDeDocumentos(id), enabled: aberto });
  return (
    <div className="mt-3">
      <button type="button" aria-expanded={aberto} onClick={() => setAberto((a) => !a)} className="wl-btn wl-btn--quiet wl-btn--sm">
        {aberto ? "Esconder o histórico" : "Ver o histórico"}
      </button>
      {aberto && historico.isPending && <p className="mt-2 text-body text-ink-muted">Carregando o histórico…</p>}
      {aberto && historico.isError && (
        <p role="alert" className="mt-2 text-body">
          {mensagemDoErro(historico.error)}
        </p>
      )}
      {aberto && historico.data && (
        <ul className="m-0 mt-2 list-none p-0" aria-label="Histórico de documentos">
          {historico.data.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 border-t border-line py-2 text-body">
              <span>
                {d.rotulo}
                {d.validade ? ` · até ${dataCurta(d.validade)}` : ""}
              </span>
              <span className="inline-flex items-center gap-3">
                <span className="text-caption text-ink-muted">{d.ativo === false ? "Substituído" : "Em uso"}</span>
                <AbrirDocumento d={d} />
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * VEI-22: "Excluir" para quem `acoes.excluir` vem (administrador e gerente). Sem histórico, a confirmação; com histórico, o aviso com o
 * motivo e o caminho da API, e "Colocar à venda" quando `acoes.colocar_a_venda` vem (T-518): fecha o aviso e abre o diálogo da VEN-01.
 */
export function ExcluirVeiculo({ v, celular, abertoDeInicio, aoColocarAVenda, noPainel }: { v: VeiculoDetalhe; celular?: boolean; abertoDeInicio?: boolean; aoColocarAVenda?: () => void; noPainel?: boolean }) {
  const acao = v.acoes.excluir;
  if (!acao) return null;
  return (
    <ExcluirCadastro
      acao={acao}
      celular={celular}
      rotulo={celular ? "Excluir veículo" : "Excluir"}
      botao={noPainel ? (abrir) => <LinhaDeAcao perigo rotulo="Excluir" detalhe="Só para cadastro feito por engano" icone={<Icone de={Trash2} />} onClick={abrir} /> : undefined}
      coisa="veículo"
      executar={() => veiculos.excluir(v.id)}
      chaveDaFicha={["veiculo", v.id]}
      chavesDasListas={[["veiculos"], ["contadores"]]}
      lista="/veiculos"
      caminho={
        v.acoes.colocar_a_venda && aoColocarAVenda
          ? (fechar) => (
              <Button
                variante="solido"
                icone={celular ? undefined : <Icone de={Tag} />}
                onClick={() => {
                  fechar();
                  aoColocarAVenda();
                }}
              >
                Colocar à venda
              </Button>
            )
          : undefined
      }
      estiloDoBotao={celular ? { height: 48 } : undefined}
      abertoDeInicio={abertoDeInicio}
    />
  );
}

/** A API recusa (403) a lista de locações a quem não tem acesso; o painel some em vez de mostrar o aviso (T-278). */
/** Abre o diálogo de uma ação de status (VEI-23) na árvore que pediu. */
type Abrir = (acao: AcaoDeStatus) => void;

function FichaDesktop({ v, docs, locacoes, manutencoes, abrir }: { v: VeiculoDetalhe; abrir: Abrir } & Consultas) {
  const fin = v.indicadores_financeiros;
  const podeAgir = v.acoes.editar;
  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Caminho" className="flex gap-[6px] text-[14px] text-ink-muted">
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
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
              {v.situacao.rotulo}
            </StatusBadge>
            <AluguelDesativado v={v} />
            {v.reserva && (
              <Link href={`/locacoes/${v.reserva.locacao_id}`} className="text-body text-ink underline">
                Ver {v.reserva.codigo}
              </Link>
            )}
            <span className="wl-mono text-[13px] text-ink-muted">{placa(v.placa)}</span>
            <span className="text-[13px] text-ink-muted">
              · {v.ano_modelo} · {v.cor} · {v.filial.nome}
            </span>
          </div>
        </div>
        {podeAgir && (
          <div className="wl-acoes-topo">
            <Link href={`/veiculos/${v.id}/editar`} className="wl-btn">
              <Icone de={Pencil} />
              Editar
            </Link>
            {/* VEI-23: só o que `acoes` libera; "Colocar à venda" (disponível) ou "Voltar para a frota" (à venda). */}
            {v.acoes.colocar_a_venda && (
              <Button variante="solido" icone={<Icone de={Tag} />} onClick={() => abrir("colocar_a_venda")}>
                Colocar à venda
              </Button>
            )}
            {v.acoes.voltar_para_frota && (
              <Button variante="solido" onClick={() => abrir("voltar_para_frota")}>
                Voltar para a frota
              </Button>
            )}
          </div>
        )}
      </header>

      <KpiGrid colunas={fin ? undefined : 2}>
        {fin && <KpiTile destaque rotulo="Rendeu no ano" valor={dinheiroSemZeros(fin.rendeu_no_ano_centavos)} contexto="locações − custos" />}
        <KpiTile rotulo="Ocupação" valor={percentual(v.ocupacao.pct)} contexto={`últimos ${v.ocupacao.periodo_dias} dias`} />
        {fin && <KpiTile rotulo="Custo de manutenção" valor={dinheiroSemZeros(fin.custo_manutencao_ano_centavos)} contexto="no ano" />}
        <KpiTile rotulo="Km atual" valor={new Intl.NumberFormat("pt-BR").format(v.km_atual)} contexto={`atualizado ${dataCurta(v.km_atualizado_em)}`} />
      </KpiGrid>

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-6">
          <AgoraDesktop v={v} />

          <GaleriaNaFicha v={v} />

          <FotosEAvarias vistoria={v.vistoria_recente} />

          {locacoes && (
          <Panel titulo="Locações" acao={locacoes.data ? <span className="text-[13px] text-ink-muted">{locacoes.data.total} no total</span> : undefined}>
            {locacoes.isError && <p role="alert">{mensagemDoErro(locacoes.error)}</p>}
            {locacoes.data?.resultados.length === 0 && <p className="text-body text-ink-muted">Este veículo ainda não foi alugado.</p>}
            {locacoes.data && locacoes.data.resultados.length > 0 && (
              <DataTable colunas={COLUNAS_LOCACOES} linhas={locacoes.data.resultados} chaveDaLinha={(l) => String(l.id)} legenda="Locações do veículo" />
            )}
          </Panel>
          )}

          {manutencoes && (
          <Panel titulo="Manutenções" acao={proximaManutencao(v) ? <span className="text-[13px] text-ink-muted">{proximaManutencao(v)}</span> : undefined}>
            {manutencoes.isError && <p role="alert">{mensagemDoErro(manutencoes.error)}</p>}
            {manutencoes.data?.resultados.length === 0 && <p className="text-body text-ink-muted">Nenhuma manutenção registrada.</p>}
            {manutencoes.data && manutencoes.data.resultados.length > 0 && (
              <DataTable colunas={COLUNAS_MANUTENCOES} linhas={manutencoes.data.resultados} chaveDaLinha={(m) => String(m.id)} legenda="Manutenções do veículo" />
            )}
          </Panel>
          )}

          <PrecosNaFicha id={v.id} />

          <MovimentacoesDoVeiculo v={v} />

          <DespesasDoVeiculo v={v} />
        </div>

        <aside className="flex min-w-0 flex-[1_1_340px] flex-col gap-6">
          {podeAgir && (
            <PainelDeAcoes>
              {v.acoes.movimentar ? (
                <LinhaDeAcao rotulo="Movimentar" detalhe="Levar ao lava-jato, à oficina ou ao despachante" icone={<Icone de={Truck} />} href={`/veiculos/movimentacoes/nova?veiculo=${v.id}`} />
              ) : (
                v.acoes.motivo_movimentar && <LinhaDeAcao rotulo="Movimentar" detalhe={v.acoes.motivo_movimentar} icone={<Icone de={Truck} />} disabled title={v.acoes.motivo_movimentar} />
              )}
              {/* `acoes.transferir` abre a Nova movimentação com o destino em outra filial e a vistoria rápida marcada (MOV-06, CA-246-16). */}
              {v.acoes.transferir && (
                <LinhaDeAcao rotulo="Transferir" detalhe="Mudar de filial, com vistoria rápida" icone={<Icone de={ArrowLeftRight} />} href={`/veiculos/movimentacoes/nova?veiculo=${v.id}&transferir=1`} />
              )}
              <LinhaDeAcao rotulo="Mandar para oficina" detalhe="Em breve" icone={<Icone de={Wrench} />} disabled title={EM_BREVE} />
              {(v.acoes.baixar || v.acoes.excluir) && <SeparadorDeAcoes />}
              {/* VEI-23: "Dar baixa" só para o administrador. */}
              {v.acoes.baixar && <LinhaDeAcao perigo rotulo="Dar baixa" detalhe="Tirar da frota de vez" icone={<Icone de={ArrowDownToLine} />} onClick={() => abrir("baixar")} />}
              <ExcluirVeiculo v={v} noPainel aoColocarAVenda={() => abrir("colocar_a_venda")} />
            </PainelDeAcoes>
          )}
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
              {/* VEI-21: com o aluguel desligado, a ficha não mostra preço de aluguel. */}
              {v.preco_vigente && v.aluguel_ligado !== false && <Linha rotulo="Preço de hoje">Semanal {dinheiro(v.preco_vigente.semanal_centavos)}</Linha>}
            </dl>
          </section>
          <section className="wl-panel">
            <h2 className="mb-1 text-[20px] font-semibold leading-[26px]">Dados do documento</h2>
            <LinhasDoDocumento v={v} />
          </section>
          <section className="wl-panel">
            <h2 className="mb-1 text-[20px] font-semibold leading-[26px]">Documentos</h2>
            <ListaDeDocumentos docs={docs} />
            <HistoricoDeDocumentos id={v.id} />
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

function FichaCelular({ v, docs, manutencoes, abrir }: { v: VeiculoDetalhe; abrir: Abrir } & Omit<Consultas, "locacoes">) {
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
            {placa(v.placa)} · {v.ano_modelo} · {v.reserva ? v.situacao.rotulo : v.situacao.rotulo.toLowerCase()}
          </span>
          {v.reserva && (
            <Link href={`/locacoes/${v.reserva.locacao_id}`} className="inline-flex min-h-[44px] items-center text-body text-ink underline">
              Ver {v.reserva.codigo}
            </Link>
          )}
        </div>
        <MaisAcoesDoCelular v={v} aoEscolher={abrir} />
      </header>

      <GaleriaNaFichaCelular v={v} />

      <FotosEAvariasCelular vistoria={v.vistoria_recente} />

      <div className={`grid ${fin ? "grid-cols-2" : "grid-cols-1"} gap-2 ${KPI_DO_CELULAR}`}>
        {fin && <KpiTile rotulo="Rendeu no ano" valor={dinheiroSemZeros(fin.rendeu_no_ano_centavos)} contexto="locações − custos" />}
        <KpiTile rotulo="Ocupação" valor={percentual(v.ocupacao.pct)} contexto={`${v.ocupacao.periodo_dias} dias`} />
      </div>

      {!atual && mostraEstoque(v) && (
        <CartaoDoCelular titulo="Agora" acao={<SeloDoEstoque v={v} />}>
          {v.dias_em_estoque != null && (
            <dl>
              <LimiteDaEmpresa v={v} Linha={Linha} />
            </dl>
          )}
        </CartaoDoCelular>
      )}

      {atual && (
        <CartaoDoCelular
          titulo="Agora"
          acao={
            <span className="flex flex-wrap justify-end gap-1">
              <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
                {v.situacao.rotulo}
              </StatusBadge>
              <AluguelDesativado v={v} />
            </span>
          }
        >
          <dl>
            <Linha rotulo="Cliente">{atual.cliente_nome}</Linha>
            <Linha rotulo="Contrato">
              <span className="wl-mono">{atual.codigo}</span>
            </Linha>
            <Linha rotulo="Devolve">{dataCurta(atual.fim_previsto)}</Linha>
            {atual.pagamento && (
              <Linha rotulo="Pagamento">
                <StatusBadge tom={atual.pagamento.situacao === "em_dia" ? "sucesso" : "alerta"} compacto>
                  {atual.pagamento.rotulo}
                </StatusBadge>
              </Linha>
            )}
            {atual.alerta && (
              <Linha rotulo="Alerta">
                <StatusBadge tom={tomDoStatus(atual.alerta.tom)} compacto>
                  {atual.alerta.rotulo}
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
          {v.manutencao.alerta && <p className="mt-1 text-caption text-ink-muted">{v.manutencao.alerta.rotulo}</p>}
        </CartaoDoCelular>
      )}

      <CartaoDoCelular titulo="Dados do documento">
        <LinhasDoDocumento v={v} />
      </CartaoDoCelular>

      <CartaoDoCelular titulo="Documentos">
        <ListaDeDocumentos docs={docs} />
        <HistoricoDeDocumentos id={v.id} />
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

      <PrecosNaFicha id={v.id} />

      <VendasDoVeiculo v={v} celular />

      <MovimentacoesCelular v={v} />

      <DespesasDoVeiculo v={v} celular />

      {v.acoes.editar && (
        <div className={`grid ${v.acoes.colocar_a_venda ? "grid-cols-2" : "grid-cols-1"} gap-2`}>
          <Button disabled title={EM_BREVE}>
            Oficina
          </Button>
          {/* VEI-23: o "Colocar à venda" do celular fica aqui e não se repete no menu Mais ações. */}
          {v.acoes.colocar_a_venda && (
            <Button variante="solido" onClick={() => abrir("colocar_a_venda")}>
              Colocar à venda
            </Button>
          )}
        </div>
      )}

      {/* VEI-22: no fim da ficha, depois da última seção, longe das ações do dia a dia. */}
      <ExcluirVeiculo v={v} celular aoColocarAVenda={() => abrir("colocar_a_venda")} />
    </div>
  );
}

/** Ficha do veículo (T-102). Tudo vem da API: situação, indicadores, documentos, locações e manutenções. O bloco financeiro some quando ela não o devolve. */
export function FichaVeiculo({ id }: { id: number }) {
  const ficha = useQuery({ queryKey: ["veiculo", id], queryFn: () => veiculos.obter(id) });
  const docs = useQuery({ queryKey: ["veiculo", id, "documentos"], queryFn: () => veiculos.documentos(id) });
  const { eu } = useSessao();
  // USR-05/USR-09 (T-458): só pede as locações com a chave da API; sem ela nenhuma chamada sai e o painel não aparece.
  const comLocacoes = eu.pode.locacoes_ver;
  const consultaLocacoes = useQuery({ queryKey: ["veiculo", id, "locacoes"], queryFn: () => veiculos.locacoes(id), enabled: comLocacoes });
  const locacoes = comLocacoes ? consultaLocacoes : null;
  const comManutencoes = temNoMenu(eu.navegacao, "manutencoes");
  const consultaManutencoes = useQuery({ queryKey: ["veiculo", id, "manutencoes"], queryFn: () => veiculos.manutencoes(id), enabled: comManutencoes });
  const manutencoes = comManutencoes ? consultaManutencoes : null;
  // VEI-23: um diálogo por vez, aberto pela árvore do desktop ou do celular; o aviso verde fica no alto da ficha até a próxima ação.
  const [janela, setJanela] = useState<{ acao: AcaoDeStatus; celular: boolean } | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const abrir = (celular: boolean) => (acao: AcaoDeStatus) => {
    setAviso(null);
    setJanela({ acao, celular });
  };

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
      {aviso && (
        <div className="mb-4">
          <AvisoDaAcao mensagem={aviso} />
        </div>
      )}
      <div className="hidden md:block">
        <FichaDesktop v={v} docs={docs} locacoes={locacoes} manutencoes={manutencoes} abrir={abrir(false)} />
      </div>
      <div className="md:hidden">
        <FichaCelular v={v} docs={docs} manutencoes={manutencoes} abrir={abrir(true)} />
      </div>
      {janela && (
        <JanelaDeStatus
          key={janela.acao}
          acao={janela.acao}
          celular={janela.celular}
          v={v}
          aoFechar={() => setJanela(null)}
          aoConcluir={(mensagem) => {
            setJanela(null);
            setAviso(mensagem);
          }}
        />
      )}
    </>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { Bike, Camera, Car, Check, ChevronLeft, Download, Eye, EyeOff, MessageCircle, Pencil, Info } from "lucide-react";
import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";
import { Button, DataTable, CelulaDupla, Icone, KpiGrid, KpiTile, Panel, StatusBadge, type ColunaTabela } from "@/design-system";
import {
  clientes,
  type ClienteCompleto,
  type ClienteResumo,
  type LocacaoDoCliente,
  type LocacoesDoCliente,
  type TipoDocumentoCliente,
} from "@/lib/api";
import { cnhMascarada, linhasDoEndereco, ROTULO_PERIODICIDADE, textoDePendencias, textoDeParcelas } from "@/lib/clientes";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { celular, dataCompleta, dataCurta, dinheiro, dinheiroSemZeros, horaCurta, iniciais, mascaraCnpj, mascaraCpf, mesAno, placa, soDigitos } from "@/lib/formatos";
import { tomDoStatus } from "@/lib/tom";
import { useSessao } from "@/lib/sessao";
import { AnaliseDoCadastro } from "./AnaliseDoCadastro";
import { ROTULO_DOCUMENTO } from "./BotaoDocumento";

// Referência: docs/telas/html/Cliente-Detalhe-Desktop.dc.html e Cliente-Detalhe-Mobile.dc.html.
// As duas versões são árvores separadas, escolhidas por um <div> com hidden / md:hidden. A classe wl- define `display`
// e vence o utilitário, então hidden e md:hidden nunca vão no mesmo elemento que uma classe wl-.

const EM_BREVE = "Ainda não está disponível";

const completo = (c: ClienteResumo | ClienteCompleto): c is ClienteCompleto => "documentos" in c;

type Documentos = {
  enviando: TipoDocumentoCliente | null;
  erros: Partial<Record<TipoDocumentoCliente, string>>;
  enviar: ((tipo: TipoDocumentoCliente, arquivo: File) => void) | null;
};

type Dados = {
  c: ClienteResumo | ClienteCompleto;
  locacoes: UseQueryResult<LocacoesDoCliente>;
  docs: Documentos;
  podeLocar: boolean;
  administrador: boolean;
};

function Linha({ rotulo, children, mono }: { rotulo: ReactNode; children: ReactNode; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className={`text-right font-medium ${mono ? "wl-mono" : ""}`}>{children}</dd>
    </div>
  );
}

function Avatar({ nome }: { nome: string }) {
  return (
    <span aria-hidden="true" className="grid h-[72px] w-[72px] shrink-0 place-items-center rounded-lg bg-solid text-[24px] font-bold text-on-solid">
      {iniciais(nome)}
    </span>
  );
}

function Selos({ c }: { c: ClienteResumo | ClienteCompleto }) {
  const pendente = completo(c) ? c.pendencias.length > 0 : c.status === "incompleto";
  return (
    <>
      <StatusBadge tom={tomDoStatus(c.situacao.tom)} compacto>
        {c.situacao.rotulo}
      </StatusBadge>
      {c.situacao.codigo !== "incompleto" && <StatusBadge compacto>{pendente ? "Cadastro incompleto" : "Cadastro completo"}</StatusBadge>}
    </>
  );
}

const linkWhatsApp = (c: ClienteResumo) => `https://wa.me/55${soDigitos(c.celular)}`;

function BotaoWhatsApp({ c, altura }: { c: ClienteResumo; altura?: boolean }) {
  return (
    <a href={linkWhatsApp(c)} target="_blank" rel="noreferrer" className="wl-btn justify-center no-underline" style={altura ? { height: 56 } : undefined}>
      <Icone de={MessageCircle} />
      WhatsApp
    </a>
  );
}

function ComIcone({ tipo }: { tipo: "moto" | "carro" }) {
  return <Icone de={tipo === "moto" ? Bike : Car} />;
}

/** Locação em curso mostra quando devolve (info); com sinal da API (atraso, devolve hoje, cancelamento) vale o rótulo dela. */
function selo(l: LocacaoDoCliente, curto?: boolean): ReactNode {
  const emCurso = l.situacao.codigo === "ativa";
  const texto = emCurso ? `Devolução em ${dataCurta(l.fim_previsto)}${curto ? " " : " às "}${horaCurta(l.fim_previsto)}` : l.situacao.rotulo;
  return (
    <StatusBadge tom={emCurso ? "info" : tomDoStatus(l.situacao.tom)} compacto>
      {texto}
    </StatusBadge>
  );
}

const periodoDaLocacao = (l: LocacaoDoCliente) => {
  const aberta = l.status === "ativa" || l.status === "aguardando_retirada" || l.status === "devolucao_atrasada";
  return `${dataCurta(l.inicio)} → ${dataCurta(l.fim_previsto)}${aberta ? ` ${horaCurta(l.fim_previsto)}` : ""}`;
};

const COLUNAS_LOCACOES: ColunaTabela<LocacaoDoCliente>[] = [
  { chave: "codigo", titulo: "Contrato", mono: true },
  {
    chave: "veiculo",
    titulo: "Veículo",
    celula: (l) => <CelulaDupla principal={`${l.veiculo.modelo} · ${placa(l.veiculo.placa)}`} secundaria={`${ROTULO_PERIODICIDADE[l.periodicidade]} · ${periodoDaLocacao(l)}`} />,
  },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (l) => (
      <StatusBadge tom={tomDoStatus(l.situacao.tom)} compacto>
        {l.situacao.rotulo}
      </StatusBadge>
    ),
  },
  { chave: "pago", titulo: "Pago", celula: (l) => dinheiro(l.pago_centavos) },
];

function Estado({ consulta, vazio, children }: { consulta: UseQueryResult<unknown>; vazio?: boolean; children: ReactNode }) {
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  if (!consulta.data) return <p className="text-body text-ink-muted">Carregando…</p>;
  if (vazio) return <p className="text-body text-ink-muted">Nada por aqui ainda.</p>;
  return <>{children}</>;
}

/** Quadro do documento: enviado (com o visto) ou, para quem cadastra, um botão de envio. */
function Documento({ tipo, rotulo, detalhe, enviado, docs, parado }: { tipo: TipoDocumentoCliente; rotulo: string; detalhe?: string; enviado: boolean; docs: Documentos; parado?: boolean }) {
  const entrada = useRef<HTMLInputElement>(null);
  const baseClasse = "relative flex h-[104px] flex-col justify-end gap-[2px] rounded-md px-[14px] py-3 text-left text-[14px]";
  if (enviado || parado || !docs.enviar) {
    return (
      <div className={`${baseClasse} bg-surface-sunken`}>
        {enviado && (
          <span className="absolute right-[10px] top-[10px] grid h-[26px] w-[26px] place-items-center rounded-pill bg-success text-on-solid">
            <Icone de={Check} className="!h-[15px] !w-[15px]" />
            <span className="sr-only">enviado</span>
          </span>
        )}
        {rotulo}
        <small className="text-[12px] text-ink-muted">{detalhe ?? (enviado ? "" : "pendente")}</small>
      </div>
    );
  }
  const enviando = docs.enviando === tipo;
  return (
    <div className="flex flex-col gap-1">
      <button type="button" disabled={enviando} onClick={() => entrada.current?.click()} className={`${baseClasse} w-full border border-dashed border-line bg-surface disabled:opacity-60`}>
        <span className="absolute right-[10px] top-[10px] grid h-[26px] w-[26px] place-items-center rounded-pill bg-surface-sunken text-ink-muted">
          <Icone de={Camera} className="!h-[15px] !w-[15px]" />
        </span>
        {rotulo}
        <small className="text-[12px] text-ink-muted">{enviando ? "Enviando…" : "Toque para enviar"}</small>
      </button>
      <input
        ref={entrada}
        type="file"
        hidden
        accept="image/jpeg,image/png,application/pdf"
        aria-label={rotulo}
        onChange={(e) => {
          const arquivo = e.target.files?.[0];
          if (arquivo) docs.enviar?.(tipo, arquivo);
          e.target.value = "";
        }}
      />
      {docs.erros[tipo] && (
        <span role="alert" className="text-caption text-critical-ink">
          {docs.erros[tipo]}
        </span>
      )}
    </div>
  );
}

const dataDoDocumento = (c: ClienteCompleto, tipo: TipoDocumentoCliente) => {
  const d = c.documentos.find((x) => x.tipo === tipo)?.enviado_em;
  return d ? dataCurta(d) : undefined;
};

// ---------------------------------------------------------------------------------------------- desktop

function DesktopCompleto({ c, locacoes, docs, podeLocar, administrador }: Dados & { c: ClienteCompleto }) {
  const [mostrar, setMostrar] = useState(false);
  const fin = c.financeiro;
  const lista = locacoes.data;
  const atual = lista?.resultados.find((l) => l.id === c.locacao_atual?.id);
  const caucao = atual?.detalhe?.caucao_em_garantia ? atual.detalhe.caucao_centavos : 0;
  const pj = c.tipo === "pj";
  const endereco = linhasDoEndereco(c.endereco);
  const enviados = c.documentos.filter((d) => d.enviado_em !== null).length;
  const documento = pj ? mascaraCnpj(c.documento) : mascaraCpf(c.documento);
  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Caminho" className="flex gap-[6px] text-caption text-ink-muted">
        <Link href="/clientes" className="text-ink-muted no-underline">
          Clientes
        </Link>{" "}
        / <span>{c.nome}</span>
      </nav>

      <header className="-mt-2 flex flex-wrap items-center gap-5">
        <Avatar nome={c.nome} />
        <div>
          <h1 className="text-display">{c.nome}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Selos c={c} />
            <span className="text-[13px] text-ink-muted">
              {pj ? "Pessoa jurídica" : "Pessoa física"} · cliente desde {mesAno(c.cliente_desde)}
            </span>
          </div>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <BotaoWhatsApp c={c} altura />
          {podeLocar && (
            <Button disabled title={EM_BREVE} icone={<Icone de={Pencil} />} style={{ height: 56 }}>
              Editar
            </Button>
          )}
          {podeLocar && (
            <Link href={`/locacoes/nova?cliente=${c.id}`} className="wl-btn wl-btn--solid no-underline" style={{ height: 56, padding: "0 28px" }}>
              <Icone de={Bike} />
              Iniciar locação
            </Link>
          )}
        </div>
      </header>

      <KpiGrid>
        <KpiTile destaque rotulo="Total pago" valor={dinheiroSemZeros(fin?.total_pago_centavos ?? 0)} contexto={lista ? `em ${lista.total} locações` : undefined} />
        <KpiTile rotulo="Em aberto" valor={dinheiroSemZeros(fin?.em_aberto_centavos ?? 0)} contexto={(fin?.em_aberto_centavos ?? 0) > 0 ? "parcelas vencidas" : "nenhuma parcela vencida"} />
        <KpiTile rotulo="Caução em garantia" valor={dinheiroSemZeros(caucao)} contexto={atual && caucao > 0 ? atual.codigo : "sem caução retida"} />
        <KpiTile rotulo="Atrasos" valor={String(lista?.com_atraso ?? 0)} contexto="em pagamentos e devoluções" />
      </KpiGrid>

      {c.bloqueio && (
        <p role="status" className="flex items-start gap-3 rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          <Icone de={Info} />
          <span>{c.bloqueio.descricao}</span>
        </p>
      )}
      {c.pendencias.length > 0 && (
        <p className="flex items-start gap-3 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          <Icone de={Info} />
          <span>{textoDePendencias(c.pendencias)}</span>
        </p>
      )}

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-6">
          <Panel titulo="Locação atual" acao={atual ? selo(atual) : undefined}>
            {c.locacao_atual ? (
              <div className="flex flex-wrap items-center gap-4 rounded-lg bg-surface-sunken p-4">
                <span className="grid h-[52px] w-[52px] shrink-0 place-items-center rounded-md bg-surface text-ink-muted">
                  <ComIcone tipo={atual?.veiculo.tipo ?? "moto"} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-[17px] font-semibold">
                    {atual ? (
                      <>
                        {atual.veiculo.modelo} · <span className="wl-mono font-medium">{placa(atual.veiculo.placa)}</span>
                      </>
                    ) : (
                      c.locacao_atual.veiculo
                    )}
                  </div>
                  <div className="mt-[2px] text-[14px] text-ink-muted">
                    {atual
                      ? `${atual.codigo} · ${ROTULO_PERIODICIDADE[atual.periodicidade]} ${atual.detalhe ? `${dinheiro(atual.detalhe.valor_periodo_centavos)} · ` : ""}${periodoDaLocacao(atual)}${atual.detalhe ? ` · ${textoDeParcelas(atual.detalhe.parcelas_pagas, atual.detalhe.parcelas_total, atual.periodicidade)}` : ""}`
                      : [c.locacao_atual.codigo, c.locacao_atual.detalhe].filter(Boolean).join(" · ")}
                  </div>
                </div>
                <Link href={`/locacoes/${c.locacao_atual.id}`} className="wl-btn wl-btn--sm no-underline">
                  Ver locação
                </Link>
                <Button variante="solido" compacto disabled title={EM_BREVE}>
                  Receber devolução
                </Button>
              </div>
            ) : (
              <p className="text-body text-ink-muted">{c.ultima_locacao ? `Nenhuma locação em andamento. A última foi a ${c.ultima_locacao.codigo}, encerrada em ${dataCurta(c.ultima_locacao.encerrada_em)}.` : "Nenhuma locação em andamento."}</p>
            )}
          </Panel>

          <Panel titulo="Locações" acao={lista ? <span className="text-[13px] text-ink-muted">{lista.total} no total · {lista.com_atraso === 0 ? "nenhuma com atraso" : `${lista.com_atraso} com atraso`}</span> : undefined}>
            <Estado consulta={locacoes} vazio={lista?.resultados.length === 0}>
              {lista && <DataTable colunas={COLUNAS_LOCACOES} linhas={lista.resultados} chaveDaLinha={(l) => String(l.id)} legenda="Locações do cliente" />}
            </Estado>
          </Panel>

          <Panel titulo="Documentos" acao={<span className="text-[13px] text-ink-muted">{enviados} de {c.documentos.length} enviados</span>}>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-3">
              {c.documentos.map((d) => (
                <Documento key={d.tipo} tipo={d.tipo} rotulo={ROTULO_DOCUMENTO[d.tipo]} detalhe={dataDoDocumento(c, d.tipo)} enviado={d.enviado_em !== null} docs={docs} />
              ))}
            </div>
          </Panel>
        </div>

        <aside className="flex min-w-0 flex-[1_1_340px] flex-col gap-6">
          <section className="wl-panel">
            <div className="mb-1 flex items-center justify-between">
              <h2 className="text-[20px] font-semibold leading-[26px]">Dados pessoais</h2>
              <Button variante="quieto" compacto icone={<Icone de={mostrar ? EyeOff : Eye} />} aria-pressed={mostrar} onClick={() => setMostrar((m) => !m)}>
                {mostrar ? "Ocultar" : "Mostrar"}
              </Button>
            </div>
            <dl>
              <Linha rotulo={pj ? "CNPJ" : "CPF"} mono>
                {mostrar ? documento : c.documento_mascarado}
              </Linha>
              {!pj && (
                <Linha rotulo="Nascimento">{c.nascimento ? `${dataCompleta(c.nascimento)}${c.idade !== null ? ` · ${c.idade} anos` : ""}` : "Não informado"}</Linha>
              )}
              <Linha rotulo="Celular">{celular(c.celular)}</Linha>
              <Linha rotulo="E-mail">{c.email ?? "Não informado"}</Linha>
              {pj ? (
                <Linha rotulo="Responsável">
                  {c.responsavel ? (
                    <>
                      {c.responsavel.nome}
                      <br />
                      {celular(c.responsavel.celular)}
                    </>
                  ) : (
                    "Não informado"
                  )}
                </Linha>
              ) : (
                <Linha rotulo="Profissão">{c.profissao ?? "Não informado"}</Linha>
              )}
              <Linha rotulo="Endereço">
                {endereco ? (
                  <>
                    {endereco[0]}
                    <br />
                    {endereco[1]}
                  </>
                ) : (
                  "Não informado"
                )}
              </Linha>
              <Linha rotulo="Referência">
                {c.referencia ? (
                  <>
                    {c.referencia.nome} · {c.referencia.parentesco}
                    <br />
                    {celular(c.referencia.telefone)}
                  </>
                ) : (
                  "Não informado"
                )}
              </Linha>
            </dl>
          </section>

          <AnaliseDoCadastro analise={c.analise} titulo="Pode alugar" />

          <section className="wl-panel">
            <h2 className="mb-1 text-[20px] font-semibold leading-[26px]">Carteira de motorista</h2>
            {c.cnh ? (
              <dl>
                <Linha rotulo="Número" mono>
                  {mostrar ? c.cnh.numero : cnhMascarada(c.cnh.numero)}
                </Linha>
                <Linha rotulo="Categoria">{c.cnh.categoria}</Linha>
                <Linha rotulo="Validade">{dataCompleta(c.cnh.validade)}</Linha>
              </dl>
            ) : (
              <p className="text-body text-ink-muted">CNH não informada.</p>
            )}
          </section>

          <section className="wl-panel flex flex-col gap-[10px]">
            <h2 className="text-[20px] font-semibold leading-[26px]">Dados do cliente (LGPD)</h2>
            <p className="text-[14px] leading-5 text-ink-muted">
              {c.consentimento_em ? `Autorizou o uso dos dados para locação e cobrança em ${dataCompleta(c.consentimento_em)}.` : "Ainda não autorizou o uso dos dados."} Só o administrador exporta ou anonimiza.
            </p>
            {administrador && (
              <Button variante="quieto" disabled title={EM_BREVE} icone={<Icone de={Download} />}>
                Exportar dados do cliente
              </Button>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------- celular

function CartaoDoCelular({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="rounded-lg bg-surface p-4">
      <h2 className="mb-1 text-heading">{titulo}</h2>
      {children}
    </section>
  );
}

// O KpiTile não tem variante de celular: o cartão da referência (28px) entra por seletor de descendente.
const KPI_DO_CELULAR = "[&_.wl-kpi]:px-4 [&_.wl-kpi]:py-[14px] [&_.wl-kpi__value]:text-[28px] [&_.wl-kpi__value]:leading-8 [&_.wl-kpi__meta]:text-[13px]";

function CelularCompleto({ c, locacoes, docs, podeLocar }: Dados & { c: ClienteCompleto }) {
  const fin = c.financeiro;
  const lista = locacoes.data;
  const atual = lista?.resultados.find((l) => l.id === c.locacao_atual?.id);
  const caucao = atual?.detalhe?.caucao_em_garantia ? atual.detalhe.caucao_centavos : 0;
  const pj = c.tipo === "pj";
  const endereco = linhasDoEndereco(c.endereco);
  const cnhEnviada = c.documentos.filter((d) => d.tipo.startsWith("cnh")).every((d) => d.enviado_em !== null);
  const cnhPendente = c.documentos.find((d) => d.tipo.startsWith("cnh") && d.enviado_em === null)?.tipo ?? "cnh_frente";
  return (
    <div className="flex flex-col gap-3">
      <header className="flex items-center gap-3 pt-2">
        <Link href="/clientes" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm shrink-0" style={{ width: 44, height: 44 }}>
          <Icone de={ChevronLeft} />
        </Link>
        <div className="flex-1 text-[13px] text-ink-muted">Clientes</div>
        {podeLocar && (
          <button type="button" className="wl-icon-btn wl-icon-btn--sm" aria-label="Editar" disabled title={EM_BREVE} style={{ width: 44, height: 44 }}>
            <Icone de={Pencil} />
          </button>
        )}
      </header>

      <section className="flex flex-col items-center gap-2 rounded-lg bg-surface px-4 py-[22px] text-center">
        <Avatar nome={c.nome} />
        <h1 className="text-[24px] font-semibold leading-normal tracking-[-0.01em]">{c.nome}</h1>
        <div className="flex flex-wrap justify-center gap-[6px]">
          <Selos c={c} />
        </div>
        <p className="text-[14px] text-ink-muted">
          {celular(c.celular)} · cliente desde {mesAno(c.cliente_desde)}
        </p>
        <div className={`mt-[6px] grid w-full gap-2 ${podeLocar ? "grid-cols-2" : ""}`}>
          <BotaoWhatsApp c={c} />
          {podeLocar && (
            <Button disabled title={EM_BREVE} icone={<Icone de={Pencil} />} style={{ justifyContent: "center" }}>
              Editar
            </Button>
          )}
        </div>
      </section>

      <div className="grid grid-cols-2 gap-2">
        <div className={KPI_DO_CELULAR}>
          <KpiTile destaque rotulo="Total pago" valor={dinheiroSemZeros(fin?.total_pago_centavos ?? 0)} contexto={lista ? `${lista.total} locações` : undefined} />
        </div>
        <div className={`${KPI_DO_CELULAR} [&_.wl-kpi]:bg-surface`}>
          <KpiTile rotulo="Em aberto" valor={dinheiroSemZeros(fin?.em_aberto_centavos ?? 0)} contexto={(fin?.em_aberto_centavos ?? 0) > 0 ? "parcelas vencidas" : "sem atrasos"} />
        </div>
      </div>

      {c.bloqueio && (
        <p role="status" className="flex items-start gap-3 rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          <Icone de={Info} />
          <span>{c.bloqueio.descricao}</span>
        </p>
      )}
      {c.pendencias.length > 0 && (
        <p className="flex items-start gap-3 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          <Icone de={Info} />
          <span>{textoDePendencias(c.pendencias)}</span>
        </p>
      )}

      {c.locacao_atual && (
        <Link href={`/locacoes/${c.locacao_atual.id}`} className="flex flex-col gap-[10px] rounded-lg bg-surface p-4 text-ink no-underline">
          <div className="flex items-center justify-between gap-2">
            <span className="text-heading">Locação atual</span>
            {atual && selo(atual, true)}
          </div>
          <div className="flex items-center gap-3">
            <span className="grid h-[52px] w-[52px] shrink-0 place-items-center rounded-md bg-surface-sunken text-ink-muted">
              <ComIcone tipo={atual?.veiculo.tipo ?? "moto"} />
            </span>
            <div>
              <div className="font-medium">{atual ? atual.veiculo.modelo : c.locacao_atual.veiculo}</div>
              <div className="text-[14px] text-ink-muted">
                {atual ? (
                  <>
                    <span className="wl-mono">{placa(atual.veiculo.placa)}</span> · <span className="wl-mono">{atual.codigo}</span> · {atual.detalhe && <> · {dinheiro(atual.detalhe.valor_periodo_centavos)}/{atual.periodicidade === "semanal" ? "sem" : atual.periodicidade === "mensal" ? "mês" : "dia"}</>}
                  </>
                ) : (
                  <span className="wl-mono">{c.locacao_atual.codigo}</span>
                )}
              </div>
            </div>
          </div>
          {atual?.detalhe && (
            <div className="text-[14px] text-ink-muted">
              {textoDeParcelas(atual.detalhe.parcelas_pagas, atual.detalhe.parcelas_total, atual.periodicidade)}
              {caucao > 0 ? ` · caução ${dinheiro(caucao)}` : ""}
            </div>
          )}
        </Link>
      )}

      <CartaoDoCelular titulo="Dados pessoais">
        <dl>
          <Linha rotulo={pj ? "CNPJ" : "CPF"} mono>
            {c.documento_mascarado}
          </Linha>
          {!pj && <Linha rotulo="Nascimento">{c.nascimento ? dataCompleta(c.nascimento) : "Não informado"}</Linha>}
          <Linha rotulo="E-mail">{c.email ?? "Não informado"}</Linha>
          <Linha rotulo="Endereço">{endereco ? `${endereco[0]} · ${c.endereco?.bairro ?? ""}` : "Não informado"}</Linha>
          <Linha rotulo="CNH">{c.cnh ? `${c.cnh.categoria} · até ${dataCompleta(c.cnh.validade)}` : "Não informada"}</Linha>
        </dl>
      </CartaoDoCelular>

      <CartaoDoCelular titulo="Locações">
        <Estado consulta={locacoes} vazio={lista?.resultados.length === 0}>
          <dl>
            {lista?.resultados.map((l) => (
              <Linha
                key={l.id}
                rotulo={
                  <>
                    <span className="wl-mono">{l.codigo}</span> · {l.veiculo.modelo}
                    <br />
                    <small className="text-[13px]">
                      {ROTULO_PERIODICIDADE[l.periodicidade]} · {periodoDaLocacao(l)}
                    </small>
                  </>
                }
              >
                {dinheiro(l.pago_centavos)}
              </Linha>
            ))}
          </dl>
        </Estado>
      </CartaoDoCelular>

      <section className="rounded-lg bg-surface p-4">
        <h2 className="mb-[10px] text-heading">Documentos</h2>
        <div className="grid grid-cols-2 gap-2">
          <Documento tipo={cnhPendente} rotulo="CNH" detalhe="frente e verso" enviado={cnhEnviada} docs={docs} />
          <Documento tipo="selfie_documento" rotulo="Selfie" detalhe={dataDoDocumento(c, "selfie_documento")} enviado={c.documentos.some((d) => d.tipo === "selfie_documento" && d.enviado_em !== null)} docs={docs} />
          <Documento tipo="comprovante_residencia" rotulo="Comprovante" detalhe={dataDoDocumento(c, "comprovante_residencia")} enviado={c.documentos.some((d) => d.tipo === "comprovante_residencia" && d.enviado_em !== null)} docs={docs} />
          <Documento tipo="cnh_frente" rotulo="Termo LGPD" detalhe={c.consentimento_em ? dataCurta(c.consentimento_em) : undefined} enviado={c.consentimento_em !== null} docs={docs} parado />
        </div>
      </section>

      {podeLocar && (
        <Link href={`/locacoes/nova?cliente=${c.id}`} className="wl-btn wl-btn--solid w-full justify-center no-underline" style={{ height: 56 }}>
          <Icone de={Bike} />
          Iniciar locação
        </Link>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------------------------- resumo

function SoResumo({ c }: { c: ClienteResumo }) {
  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Caminho" className="text-caption text-ink-muted">
        <Link href="/clientes" className="text-ink-muted no-underline">
          Clientes
        </Link>{" "}
        / {c.nome}
      </nav>
      <header className="-mt-2 flex flex-wrap items-center gap-5">
        <Avatar nome={c.nome} />
        <div>
          <h1 className="text-title md:text-display">{c.nome}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge tom={tomDoStatus(c.situacao.tom)} compacto>
              {c.situacao.rotulo}
            </StatusBadge>
            <span className="wl-mono text-[13px] text-ink-muted">{c.documento_mascarado}</span>
          </div>
        </div>
      </header>
      <p className="wl-panel text-body text-ink-muted">Seu perfil vê só o resumo do cliente. Os dados completos e os documentos ficam com quem cadastra.</p>
    </div>
  );
}

/** Detalhe do cliente (T-108). Situação, valores, análise e pendências vêm da API; aqui só se mostra. */
export function DetalheDoCliente({ id }: { id: number }) {
  const { eu } = useSessao();
  const cache = useQueryClient();
  const consulta = useQuery({ queryKey: ["cliente", id], queryFn: () => clientes.obter(id) });
  const locacoes = useQuery({ queryKey: ["cliente", id, "locacoes"], queryFn: () => clientes.locacoes(id) });
  const [erros, setErros] = useState<Documentos["erros"]>({});
  const [enviando, setEnviando] = useState<TipoDocumentoCliente | null>(null);

  const enviar = useMutation({
    mutationFn: ({ tipo, arquivo }: { tipo: TipoDocumentoCliente; arquivo: File }) => clientes.enviarDocumento(id, tipo, arquivo),
    onMutate: ({ tipo }) => {
      setEnviando(tipo);
      setErros((e) => ({ ...e, [tipo]: undefined }));
    },
    onSuccess: (atualizado) => {
      cache.setQueryData(["cliente", id], atualizado);
      void cache.invalidateQueries({ queryKey: ["clientes"] });
    },
    onError: (e, { tipo }) => setErros((x) => ({ ...x, [tipo]: campoDoErro(e, "arquivo") ?? mensagemDoErro(e) })),
    onSettled: () => setEnviando(null),
  });

  if (consulta.isError) {
    return (
      <div className="flex flex-col gap-4">
        <Link href="/clientes" className="text-body text-ink-muted">
          Clientes
        </Link>
        <p role="alert" className="wl-panel text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      </div>
    );
  }
  const c = consulta.data;
  if (!c) {
    return (
      <p className="wl-panel text-body text-ink-muted" aria-busy="true">
        Carregando o cliente…
      </p>
    );
  }
  if (!completo(c)) return <SoResumo c={c} />;

  const podeCadastrar = eu.pode.clientes_cadastrar;
  const dados: Dados = {
    c,
    locacoes,
    docs: { enviando, erros, enviar: podeCadastrar ? (tipo, arquivo) => enviar.mutate({ tipo, arquivo }) : null },
    podeLocar: eu.pode.locacoes_criar && (c.status === "ativo" || c.status === "incompleto"),
    administrador: eu.perfil === "administrador",
  };
  return (
    <>
      <div className="hidden md:block">
        <DesktopCompleto {...dados} c={c} />
      </div>
      <div className="md:hidden">
        <CelularCompleto {...dados} c={c} />
      </div>
    </>
  );
}

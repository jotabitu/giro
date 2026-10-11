"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Bike, Car, ChevronLeft, FileText, User } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Button, Icone, Panel, StatusBadge } from "@/design-system";
import { clientes, ErroApi, locacoes, type ClienteCompleto, type ClienteResumo, type HistoricoDaLocacao, type LocacaoCompleta } from "@/lib/api";
import { ROTULO_PERIODICIDADE } from "@/lib/clientes";
import { mensagemDoErro } from "@/lib/erros";
import { celular, dataCurta, dataHoraCurta, dinheiro, diaDe, horaCurta, km, placa } from "@/lib/formatos";
import { dataEHora, rotuloDaParcela, rotuloDaVistoriaDaTroca, seloDaParcela, textoDoPeriodo, textoFaltam } from "@/lib/locacoes";
import { tomDoStatus } from "@/lib/tom";
import { AcoesDaLocacao } from "./AcoesDaLocacao";
import { TelaDeErro } from "./Comuns";

// Referência: docs/telas/html/Locacao-Detalhe-Desktop.dc.html e Locacao-Detalhe-Mobile.dc.html.
// As duas versões são árvores separadas, escolhidas por um <div> com hidden / md:hidden (nunca no mesmo elemento de uma classe wl-).
// Tudo que é valor, situação e ação vem da API; o vistoriador recebe a locação sem valores e a tela só omite o que não vem.

const ROTULO_CONTA: Record<string, string> = { aberta: "em aberto", vence_hoje: "vence hoje", atrasada: "atrasada", paga: "paga", cancelada: "cancelada" };
const ABREV: Record<string, string> = { diaria: "dia", semanal: "sem", mensal: "mês" };

function Linha({ rotulo, children }: { rotulo: ReactNode; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

function Miniatura({ icone }: { icone: typeof Bike }) {
  return (
    <span aria-hidden="true" className="grid h-[52px] w-[52px] shrink-0 place-items-center rounded-md bg-surface-sunken text-ink-muted">
      <Icone de={icone} />
    </span>
  );
}

type Cliente = ClienteResumo | ClienteCompleto;

function veiculoEhCarro(modelo: string) {
  return /kwid|mobi|argo|onix|hb20|uno|gol|polo|sandero|logan|etios|ka\b/i.test(modelo);
}

/** "(85) 98114-2290 · CNH A": vem do cadastro do cliente, só para quem pode ver. */
function contatoDoCliente(c: Cliente | undefined): string | null {
  if (!c) return null;
  const cnh = "cnh" in c && c.cnh?.categoria ? ` · CNH ${c.cnh.categoria}` : "";
  return `${celular(c.celular)}${cnh}`;
}

function textoDoPeriodoEmDatas(l: LocacaoCompleta): string {
  if (!l.inicio) return "";
  const fim = l.fim_previsto ? ` → ${dataCurta(l.fim_previsto)} ${horaCurta(l.fim_previsto)}` : "";
  return `${dataCurta(l.inicio)}${fim}`;
}

function Prazo({ l, sobreSolido }: { l: LocacaoCompleta; sobreSolido?: boolean }) {
  const mudo = sobreSolido ? "opacity-80" : "text-ink-muted";
  const d = l.devolucao;
  if (!d.prevista_para) return null;
  const atrasada = l.status === "devolucao_atrasada";
  return (
    <>
      <div className="text-title font-semibold">{atrasada ? `Devolução era para ${dataEHora(d.prevista_para)}` : `Devolução em ${dataEHora(d.prevista_para)}`}</div>
      {atrasada ? <div className={`text-body ${mudo}`}>{l.situacao.rotulo}</div> : d.faltam_minutos !== null && <div className={`text-body ${mudo}`}>{textoFaltam(d.faltam_minutos)}</div>}
      {d.aviso_atraso && <div className={`mt-3 text-caption ${mudo}`}>{d.aviso_atraso}</div>}
    </>
  );
}

function Resumo({ l }: { l: LocacaoCompleta }) {
  const p = l.precos;
  if (!p) return null;
  return (
    <Panel titulo="Resumo">
      <dl>
        <Linha rotulo="Plano">
          {ROTULO_PERIODICIDADE[l.periodicidade]} · {dinheiro(p.valor_periodo_centavos)}
        </Linha>
        <Linha rotulo="Período">{textoDoPeriodo(l.periodos, l.periodicidade)}</Linha>
        <Linha rotulo="Km incluído">{l.km_livre ? "livre" : "limitado"}</Linha>
        <Linha rotulo="Extras">{l.extras && l.extras.length > 0 ? l.extras.map((e) => e.nome).join(", ") : "Nenhum"}</Linha>
        <Linha rotulo="Caução">{dinheiro(p.caucao_centavos)}</Linha>
        {l.total_pago_centavos !== undefined && <Linha rotulo="Total pago">{dinheiro(l.total_pago_centavos)}</Linha>}
      </dl>
    </Panel>
  );
}

function Pagamentos({ l }: { l: LocacaoCompleta }) {
  if (!l.parcelas) return null;
  const aberto = l.pagamento?.em_aberto_centavos ?? 0;
  return (
    <Panel titulo="Pagamentos" acao={<span className="text-caption text-ink-muted">{aberto > 0 ? l.pagamento?.rotulo : "tudo em dia"}</span>}>
      <div className="overflow-x-auto">
        <table className="wl-table">
          <thead>
            <tr>
              <th>Parcela</th>
              <th>Vencimento</th>
              <th>Valor</th>
              <th>Situação</th>
            </tr>
          </thead>
          <tbody>
            {l.parcelas.map((p) => {
              const selo = seloDaParcela(p);
              return (
                <tr key={p.id}>
                  <td>{rotuloDaParcela(p)}</td>
                  <td>{dataCurta(p.vencimento)}</td>
                  <td>{dinheiro(p.valor_centavos)}</td>
                  <td>
                    <StatusBadge tom={selo.tom} compacto>
                      {selo.texto}
                    </StatusBadge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function Contrato({ l, aoConcluir }: { l: LocacaoCompleta; aoConcluir: (m: string) => void }) {
  const c = l.contrato;
  const reenviar = useMutation({ mutationFn: () => locacoes.reenviarContrato(l.id), onSuccess: () => aoConcluir(c?.status === "assinado" ? "Contrato reenviado por WhatsApp." : "Link de assinatura reenviado por WhatsApp.") });
  const imprimir = useMutation({ mutationFn: () => locacoes.pdfDoContrato(l.id), onSuccess: (r) => window.open(r.url, "_blank", "noopener") });
  if (!c) return null;
  const assinado = c.status === "assinado";
  const detalhe = assinado && c.assinado_em ? `Modelo “${c.modelo}” · assinado em ${dataCurta(c.assinado_em)}` : `Modelo “${c.modelo}” · aguardando assinatura${c.enviado_em ? `, enviado em ${dataCurta(c.enviado_em)}` : ""}`;
  return (
    <Panel
      titulo="Contrato"
      acao={
        <div className="flex flex-wrap gap-2">
          {l.acoes.imprimir_contrato && c.pdf_disponivel && (
            <Button compacto disabled={imprimir.isPending} onClick={() => imprimir.mutate()}>
              Imprimir
            </Button>
          )}
          {l.acoes.reenviar_contrato && (
            <Button compacto disabled={reenviar.isPending} onClick={() => reenviar.mutate()}>
              {reenviar.isPending ? "Enviando…" : "Reenviar por WhatsApp"}
            </Button>
          )}
        </div>
      }
    >
      <div className="flex items-center gap-3">
        <Miniatura icone={FileText} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-body font-medium">Contrato {l.codigo}.pdf</div>
          <div className="text-caption text-ink-muted">{detalhe}</div>
        </div>
        <StatusBadge tom={assinado ? "sucesso" : "neutro"} compacto>
          {assinado ? "Assinado" : "Aguardando assinatura"}
        </StatusBadge>
      </div>
      {(reenviar.isError || imprimir.isError) && (
        <p role="alert" className="mt-3 text-caption text-critical">
          {mensagemDoErro(reenviar.error ?? imprimir.error)}
        </p>
      )}
    </Panel>
  );
}

function Cancelamento({ l }: { l: LocacaoCompleta }) {
  const c = l.cancelamento;
  if (!c) return null;
  return (
    <Panel titulo={c.status === "pendente" ? "Pedido de cancelamento" : "Encerramento aprovado"} subtitulo={c.status === "pendente" ? "Aguardando o gerente" : "Registre a devolução para fechar a conta"}>
      <dl>
        <Linha rotulo="Motivo">{c.motivo}</Linha>
        <Linha rotulo="Multa de encerramento">{dinheiro(c.multa_centavos)}</Linha>
        {c.credito_centavos > 0 && <Linha rotulo="Crédito das semanas não usadas">{dinheiro(c.credito_centavos)}</Linha>}
        {c.devolver_centavos > 0 && <Linha rotulo="A devolver ao cliente">{dinheiro(c.devolver_centavos)}</Linha>}
        {c.cobrar_centavos > 0 && <Linha rotulo="A cobrar do cliente">{dinheiro(c.cobrar_centavos)}</Linha>}
      </dl>
      {!c.antes_da_retirada && <p className="mt-3 text-caption text-ink-muted">{c.data ? `Estimativa para ${dataCurta(c.data)}. O valor final sai na devolução.` : "Estimativa. O valor final sai na devolução."}</p>}
    </Panel>
  );
}

/** A troca pendente (LOC-09): os dois veículos, o motivo e o andamento das duas vistorias. Sem valores para o vistoriador. */
function Troca({ l }: { l: LocacaoCompleta }) {
  const t = l.troca;
  if (!t) return null;
  return (
    <Panel titulo="Troca de veículo" subtitulo="Pendente: a locação segue no veículo atual até as duas vistorias terminarem">
      <dl>
        <Linha rotulo="Veículo atual">
          {t.veiculo_antigo.modelo} · <span className="wl-mono">{placa(t.veiculo_antigo.placa)}</span>
        </Linha>
        <Linha rotulo="Veículo novo">
          {t.veiculo_novo.modelo} · <span className="wl-mono">{placa(t.veiculo_novo.placa)}</span>
        </Linha>
        <Linha rotulo="Motivo">{t.motivo}</Linha>
        {t.pedida_em && <Linha rotulo="Pedida em">{dataHoraCurta(t.pedida_em)}</Linha>}
        {t.devolucao_vistoria && <Linha rotulo="Chegada do veículo atual">{rotuloDaVistoriaDaTroca(t.devolucao_vistoria.status)}</Linha>}
        {t.saida_vistoria && <Linha rotulo="Saída do veículo novo">{rotuloDaVistoriaDaTroca(t.saida_vistoria.status)}</Linha>}
        {t.preco && <Linha rotulo="Preço do veículo novo">{dinheiro(t.preco.valor_periodo_centavos)}</Linha>}
        {t.caucao && (
          <Linha rotulo="Diferença de caução">
            {dinheiro(t.caucao.valor_centavos)} · {ROTULO_CONTA[t.caucao.status] ?? t.caucao.status}
          </Linha>
        )}
      </dl>
    </Panel>
  );
}

function Historico({ l, historico }: { l: LocacaoCompleta; historico: HistoricoDaLocacao | undefined }) {
  const itens = historico?.resultados ?? [];
  const prevista = l.devolucao.prevista_para;
  const mostraPrevista = prevista && (l.status === "ativa" || l.status === "devolucao_atrasada");
  const previstaTexto = prevista ? (diaDe(prevista) === diaDe(new Date().toISOString()) ? `hoje, ${horaCurta(prevista)}` : dataHoraCurta(prevista)) : "";
  return (
    <Panel titulo="Histórico">
      <ol className="relative flex flex-col pl-[26px] before:absolute before:bottom-2 before:left-[6px] before:top-2 before:w-[2px] before:bg-line">
        {itens.map((i, n) => (
          <li key={`${i.em}-${n}`} className="relative py-2 before:absolute before:-left-[25px] before:top-[13px] before:h-3 before:w-3 before:rounded-pill before:bg-solid">
            <div className="text-body">{i.rotulo}</div>
            <div className="text-caption text-ink-muted">{[i.em ? dataHoraCurta(i.em) : null, i.detalhe].filter(Boolean).join(" · ")}</div>
          </li>
        ))}
        {mostraPrevista && (
          <li className="relative py-2 before:absolute before:-left-[25px] before:top-[13px] before:h-3 before:w-3 before:rounded-pill before:bg-surface before:shadow-[inset_0_0_0_2px_var(--ink)]">
            <div className="text-body">Devolução prevista</div>
            <div className="text-caption text-ink-muted">{previstaTexto}</div>
          </li>
        )}
      </ol>
    </Panel>
  );
}

/** Detalhe da locação: veículo, cliente, pagamentos, contrato, prazo, resumo e histórico. */
export function DetalheDaLocacao({ id }: { id: number }) {
  const [aviso, setAviso] = useState<string | null>(null);
  const locacao = useQuery({ queryKey: ["locacao", id], queryFn: () => locacoes.obter(id), retry: (n, e) => !(e instanceof ErroApi) && n < 2 });
  const historico = useQuery({ queryKey: ["locacao", id, "historico"], queryFn: () => locacoes.historico(id), enabled: locacao.isSuccess });
  const clienteId = locacao.data?.cliente.id;
  const cliente = useQuery({ queryKey: ["cliente", clienteId], queryFn: () => clientes.obter(clienteId ?? 0), enabled: clienteId !== undefined, retry: false });

  if (locacao.isPending) {
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Carregando a locação…
      </p>
    );
  }
  if (locacao.isError) return <TelaDeErro erro={locacao.error} voltar={{ href: "/locacoes", rotulo: "Voltar para Locações" }} />;

  const l = locacao.data;
  const contato = contatoDoCliente(cliente.data);
  const ehCarro = veiculoEhCarro(l.veiculo.modelo);
  const pagas = l.parcelas?.filter((p) => p.tipo === "parcela" && p.status === "paga").length ?? 0;
  const totalParcelas = l.parcelas?.filter((p) => p.tipo === "parcela").length ?? 0;

  const avisoNaTela = aviso && (
    <p role="status" className="rounded-lg bg-brand-soft px-4 py-3 text-body">
      {aviso}
    </p>
  );

  const cabecalhoVeiculo = (
    <>
      <div className="flex items-center gap-3">
        <Miniatura icone={ehCarro ? Car : Bike} />
        <div>
          <div className="text-body font-medium">{l.veiculo.modelo}</div>
          <div className="wl-mono text-caption text-ink-muted">
            {placa(l.veiculo.placa)}
            {l.km_saida !== null ? ` · saiu com ${km(l.km_saida)}` : ""}
          </div>
        </div>
      </div>
      <Link href={`/clientes/${l.cliente.id}`} className="flex items-center gap-3 text-ink no-underline">
        <Miniatura icone={User} />
        <div>
          <div className="text-body font-medium">{l.cliente.nome}</div>
          {contato && <div className="text-caption text-ink-muted">{contato}</div>}
        </div>
      </Link>
    </>
  );

  return (
    <>
      {/* Desktop */}
      <div className="hidden flex-col gap-6 md:flex">
        <nav aria-label="Caminho" className="text-caption text-ink-muted">
          <Link href="/locacoes" className="text-ink-muted">
            Locações
          </Link>{" "}
          / <span className="wl-mono text-ink">{l.codigo}</span>
        </nav>
        <header className="flex flex-wrap items-center gap-4">
          <div>
            <h1 className="text-display">{l.cliente.nome}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <StatusBadge tom={tomDoStatus(l.situacao.tom)} compacto>
                {l.situacao.rotulo}
              </StatusBadge>
              <span className="wl-mono text-caption text-ink-muted">{l.codigo}</span>
              <span className="text-caption text-ink-muted">
                · {ROTULO_PERIODICIDADE[l.periodicidade]} · {textoDoPeriodoEmDatas(l)}
              </span>
            </div>
          </div>
          <div className="ml-auto">
            <AcoesDaLocacao l={l} variante="desktop" aoConcluir={setAviso} />
          </div>
        </header>
        {avisoNaTela}
        <div className="grid grid-cols-[minmax(0,1fr)_380px] items-start gap-6">
          <div className="flex min-w-0 flex-col gap-6">
            <section className="wl-panel">
              <div className="grid grid-cols-2 gap-6">{cabecalhoVeiculo}</div>
            </section>
            <Pagamentos l={l} />
            <Contrato l={l} aoConcluir={setAviso} />
          </div>
          <div className="flex min-w-0 flex-col gap-6">
            <section className="wl-panel">
              <Prazo l={l} />
            </section>
            <Troca l={l} />
            <Cancelamento l={l} />
            <Resumo l={l} />
            <Historico l={l} historico={historico.data} />
          </div>
        </div>
      </div>

      {/* Celular */}
      <div className="flex flex-col gap-4 md:hidden">
        <header className="flex items-center gap-3">
          <Link href="/locacoes" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm">
            <Icone de={ChevronLeft} />
          </Link>
          <div className="min-w-0">
            <h1 className="truncate text-title">{l.cliente.nome}</h1>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tom={tomDoStatus(l.situacao.tom)} compacto>
                {l.situacao.rotulo}
              </StatusBadge>
              <span className="wl-mono text-caption text-ink-muted">{l.codigo}</span>
            </div>
          </div>
        </header>
        {avisoNaTela}
        <section className="rounded-lg bg-solid p-4 text-on-solid">
          <Prazo l={l} sobreSolido />
          <div className="mt-3 text-caption">
            {l.veiculo.modelo} · {placa(l.veiculo.placa)}
          </div>
        </section>
        <Troca l={l} />
        <Cancelamento l={l} />
        {l.precos && (
          <section className="wl-panel">
            <h2 className="wl-panel__title mb-2">Resumo</h2>
            <dl>
              <Linha rotulo="Plano">
                {dinheiro(l.precos.valor_periodo_centavos)}/{ABREV[l.periodicidade]}
              </Linha>
              {l.parcelas && (
                <Linha rotulo="Pagamentos">
                  {pagas} de {totalParcelas} pagos
                </Linha>
              )}
              <Linha rotulo="Caução">{dinheiro(l.precos.caucao_centavos)}</Linha>
              {cliente.data && <Linha rotulo="Telefone">{celular(cliente.data.celular)}</Linha>}
            </dl>
          </section>
        )}
        <Contrato l={l} aoConcluir={setAviso} />
        <Historico l={l} historico={historico.data} />
        <AcoesDaLocacao l={l} variante="celular" aoConcluir={setAviso} />
      </div>
    </>
  );
}


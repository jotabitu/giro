"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Icone, ProgressBar, StatusBadge } from "@/design-system";
import { assinatura as api, type Assinatura } from "@/lib/api";
import { avisoDeUso, ITENS_DO_USO, percentualDeUso, precoDoPlano, situacaoDaAssinatura } from "@/lib/assinatura";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, dinheiro } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { DadosFiscaisDaAssinatura } from "./DadosFiscaisDaAssinatura";
import { DialogoPausarAssinatura } from "./DialogoPausarAssinatura";
import { FaturasDaAssinatura } from "./FaturasDaAssinatura";
import { FormaDePagamentoDaAssinatura } from "./FormaDePagamentoDaAssinatura";
import { PlanosDaAssinatura } from "./PlanosDaAssinatura";

// Referência: docs/telas/html/Admin-Assinatura-Desktop.dc.html e Admin-Assinatura-Mobile.dc.html.
// Tudo o que cada bloco mostra e permite vem da API (`GET /api/assinatura/`, `acoes`); a tela não calcula valor, data nem permissão.

/** Barra de uso de um item do plano (PLT-03): o número, o limite e, se for o caso, o aviso por escrito. */
function Medidor({ item, uso }: { item: (typeof ITENS_DO_USO)[number]; uso: { usado: number; limite: number | null; aviso: boolean; bloqueado: boolean } }) {
  const aviso = avisoDeUso(uso);
  return (
    <div className="flex flex-col gap-1.5 md:gap-2 md:rounded-lg md:bg-surface-sunken md:p-[18px_20px]" role="group" aria-label={item.rotulo}>
      <div className="flex items-baseline justify-between text-caption md:hidden">
        <strong className="font-medium">{item.rotulo}</strong>
        <span className="text-ink-muted">{uso.limite === null ? `${uso.usado}, sem limite` : `${uso.usado} de ${uso.limite}`}</span>
      </div>
      <div className="hidden items-baseline justify-between md:flex">
        <b className="text-[28px] leading-8 font-semibold tracking-tight">{uso.usado}</b>
        <span className="text-caption text-ink-muted">{uso.limite === null ? `${item.plural}, sem limite` : `de ${uso.limite} ${item.plural}`}</span>
      </div>
      {uso.limite !== null && <ProgressBar valor={percentualDeUso(uso)} rotulo={`Uso de ${item.plural}`} />}
      {aviso && (
        <span role={uso.bloqueado ? "alert" : "note"} className={`text-caption ${uso.bloqueado ? "text-critical-ink" : "text-warning-ink"}`}>
          {aviso}
        </span>
      )}
    </div>
  );
}

/** Card principal do plano contratado, mudança/pausa/cancelamento agendados e ações que a API liberou. */
function CartaoDoSeuPlano({
  a,
  aoMudarPlano,
  aoPausar,
  aoConcluir,
}: {
  a: Assinatura;
  aoMudarPlano: () => void;
  aoPausar: () => void;
  aoConcluir: (mensagem: string) => void;
}) {
  const cliente = useQueryClient();
  const situacao = situacaoDaAssinatura(a);
  const atualizar = async (res: Assinatura | undefined, msg: string) => {
    if (res) cliente.setQueryData(["assinatura"], res);
    await Promise.all([cliente.invalidateQueries({ queryKey: ["assinatura"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
    aoConcluir(msg);
  };
  const desfazerMudanca = useMutation({
    mutationFn: () => api.desfazerMudanca(),
    onSuccess: () => atualizar(undefined, "Mudança de plano desfeita. Você continua no plano de hoje."),
  });
  const desfazerCancelamento = useMutation({
    mutationFn: () => api.desfazerCancelamento(),
    onSuccess: (res) => atualizar(res, "Cancelamento desfeito. Sua assinatura continua ativa."),
  });
  const encerrarPausa = useMutation({
    mutationFn: () => api.encerrarPausa(),
    onSuccess: (res) => atualizar(res, a.acoes?.voltar_pausa ? "Assinatura reativada." : "Pausa agendada desfeita."),
  });
  const erro = desfazerMudanca.error ?? desfazerCancelamento.error ?? encerrarPausa.error;
  const temAcao = Boolean(
    a.acoes?.mudar_plano ||
      a.acoes?.desfazer_mudanca_plano ||
      a.acoes?.pausar ||
      a.acoes?.voltar_pausa ||
      a.acoes?.desistir_pausa ||
      a.acoes?.desfazer_cancelamento ||
      (a.acoes?.escolher_forma_pagamento && a.forma_pagamento?.forma === null),
  );

  return (
    <section className="flex flex-col gap-3 rounded-[28px] bg-solid p-5 text-on-solid md:rounded-[32px] md:p-7" aria-label="Seu plano">
      <div className="flex flex-wrap items-center gap-2">
        <span className="hidden text-caption text-on-solid-muted md:inline">Seu plano</span>
        <StatusBadge tom={situacao.tom} compacto>
          {situacao.rotulo}
        </StatusBadge>
      </div>
      <div className="text-[30px] leading-[34px] font-semibold tracking-tight md:text-[36px] md:leading-10">{a.plano.nome}</div>
      <div className="text-caption text-on-solid-muted md:text-body">{precoDoPlano(a)}</div>
      {a.teste && a.status === "em_teste" && (
        <div className="text-caption text-on-solid-muted">{a.teste.dias_restantes === 1 ? "Falta 1 dia" : `Faltam ${a.teste.dias_restantes} dias`} de teste grátis.</div>
      )}
      {a.plano_proximo && (
        <div className="text-caption text-on-solid-muted md:text-body">
          Muda para {a.plano_proximo.nome}
          {a.plano_proximo.vale_em ? ` em ${dataCurta(a.plano_proximo.vale_em)}` : ""}
          {a.proxima_fatura ? `, a ${dinheiro(a.proxima_fatura.valor_centavos)}` : ""}.
        </div>
      )}
      {a.pausa && <div className="text-caption text-on-solid-muted md:text-body">{a.pausa.rotulo}</div>}
      {a.cancelamento && (
        <div className="text-caption text-on-solid-muted md:text-body">
          {a.cancelamento.rotulo} Depois disso, a empresa fica sem acesso e nada mais é cobrado.
        </div>
      )}
      {temAcao && (
        <div className="mt-2 flex flex-wrap gap-2">
          {a.acoes?.mudar_plano && (
            <Button variante="quieto" onClick={aoMudarPlano}>
              Mudar de plano
            </Button>
          )}
          {a.acoes?.desfazer_mudanca_plano && (
            <Button variante="quieto" disabled={desfazerMudanca.isPending} onClick={() => desfazerMudanca.mutate()}>
              {desfazerMudanca.isPending ? "Desfazendo…" : "Desfazer mudança"}
            </Button>
          )}
          {a.acoes?.pausar && (
            <Button variante="quieto" onClick={aoPausar}>
              Pausar assinatura
            </Button>
          )}
          {a.acoes?.voltar_pausa && (
            <Button variante="marca" disabled={encerrarPausa.isPending} onClick={() => encerrarPausa.mutate()}>
              {encerrarPausa.isPending ? "Reativando…" : "Voltar da pausa"}
            </Button>
          )}
          {a.acoes?.desistir_pausa && (
            <Button variante="quieto" disabled={encerrarPausa.isPending} onClick={() => encerrarPausa.mutate()}>
              {encerrarPausa.isPending ? "Desfazendo…" : "Desistir da pausa"}
            </Button>
          )}
          {a.acoes?.desfazer_cancelamento && (
            <Button variante="marca" disabled={desfazerCancelamento.isPending} onClick={() => desfazerCancelamento.mutate()}>
              {desfazerCancelamento.isPending ? "Desfazendo…" : "Desfazer cancelamento"}
            </Button>
          )}
          {a.acoes?.escolher_forma_pagamento && a.forma_pagamento?.forma === null && (
            <a href="#forma-de-pagamento" className="wl-btn wl-btn--quiet">
              Escolher forma de pagamento
            </a>
          )}
        </div>
      )}
      {erro && (
        <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
          {mensagemDoErro(erro)}
        </p>
      )}
    </section>
  );
}

/** Administração › Assinatura: plano, uso, forma de pagamento, faturas, dados da nota fiscal, pausa e cancelamento. */
export function AssinaturaDaEmpresa() {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["assinatura"], queryFn: () => api.obter(), enabled: podeVer });
  const a = podeVer ? consulta.data : undefined;
  const [planos, setPlanos] = useState<"mudar" | "comparar" | null>(null);
  const [pausaAberta, setPausaAberta] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa a Assinatura.
      </p>
    );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-4">
        <Link href="/mais" aria-label="Voltar" className="wl-icon-btn size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Assinatura</h1>
        </div>
      </header>

      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando a assinatura…
        </p>
      )}

      {a?.faixa_aviso && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {a.faixa_aviso}
        </p>
      )}
      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}
      {a?.somente_leitura && (
        <p role="note" className="rounded-lg bg-surface-sunken p-4 text-body text-ink-muted">
          Sua empresa está só para consulta no momento. Dá para ver tudo, mas não para cadastrar ou alterar.
        </p>
      )}

      {a && (
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <div className="flex min-w-0 flex-col gap-6 md:flex-[999_1_560px]">
            <CartaoDoSeuPlano a={a} aoMudarPlano={() => setPlanos("mudar")} aoPausar={() => setPausaAberta(true)} aoConcluir={setAviso} />

            <section className="wl-panel" aria-label="Uso do plano">
              <h2 className="mb-4 text-heading">Uso do plano</h2>
              <div className="grid gap-4 md:grid-cols-[repeat(auto-fit,minmax(200px,1fr))] md:gap-3">
                {ITENS_DO_USO.map((item) => (
                  <Medidor key={item.chave} item={item} uso={a.uso[item.chave]} />
                ))}
              </div>
              <p className="mt-3.5 mb-0 text-caption text-ink-muted">Avisamos quando chegar a 90% de qualquer limite.</p>
            </section>

            {a.forma_pagamento && (
              <div id="forma-de-pagamento">
                <FormaDePagamentoDaAssinatura forma={a.forma_pagamento} pode={a.acoes?.escolher_forma_pagamento === true} />
              </div>
            )}
            {a.forma_pagamento && <FaturasDaAssinatura forma={a.forma_pagamento.forma ?? null} />}
            {a.dados_fiscais && <DadosFiscaisDaAssinatura dados={a.dados_fiscais} pode={a.acoes?.editar_dados_fiscais === true} aoConcluir={setAviso} />}
          </div>

          <aside className="flex min-w-0 flex-col gap-4 md:flex-[1_1_300px]" aria-label="Oferta e cancelamento">
            {a.oferta && (
              <section className="wl-panel flex flex-col gap-3" aria-label="Plano acima">
                <h2 className="text-heading">{a.oferta.titulo}</h2>
                <p className="m-0 text-body">O plano {a.oferta.plano.nome} inclui:</p>
                <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-body">
                  {a.oferta.itens.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ul>
                <p className="m-0 text-caption text-ink-muted">{dinheiro(a.oferta.plano.preco_mensal_centavos)} por mês</p>
                <div>
                  <Button variante="quieto" onClick={() => setPlanos("comparar")}>
                    Comparar planos
                  </Button>
                </div>
              </section>
            )}
            <section className="flex flex-col gap-2 px-2">
              {a.acoes?.cancelar && (
                <div>
                  <Link href="/admin/assinatura/cancelar" className="text-caption text-ink-muted underline">
                    Cancelar assinatura
                  </Link>
                </div>
              )}
              <p className="m-0 text-caption text-ink-muted">
                <Link href="/admin/exportar" className="underline">
                  Exportar dados antes
                </Link>
                . Exportar baixa a auditoria em CSV. O resto dos seus dados você pede à equipe Giro.
              </p>
            </section>
          </aside>
        </div>
      )}
      {planos && <PlanosDaAssinatura podeMudar={planos === "mudar" && a?.acoes?.mudar_plano === true} aoFechar={() => setPlanos(null)} aoConcluir={setAviso} />}
      {pausaAberta && (
        <DialogoPausarAssinatura
          aberto
          inicio={a?.proxima_fatura?.vencimento}
          aoFechar={() => setPausaAberta(false)}
          aoConcluir={(res) => {
            setPausaAberta(false);
            setAviso(res.pausa ? `${res.pausa.rotulo}.` : "Pausa agendada.");
          }}
        />
      )}
    </div>
  );
}

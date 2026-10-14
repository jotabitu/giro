"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button, Icone, ProgressBar, StatusBadge } from "@/design-system";
import { assinatura as api } from "@/lib/api";
import { avisoDeUso, ITENS_DO_USO, percentualDeUso, precoDoPlano, situacaoDaAssinatura } from "@/lib/assinatura";
import { mensagemDoErro } from "@/lib/erros";
import { useSessao } from "@/lib/sessao";

// Referência: docs/telas/html/Admin-Assinatura-Desktop.dc.html e Admin-Assinatura-Mobile.dc.html.
// Na fase 1 o contrato só entrega plano, estado, teste, faixa de aviso e uso (`GET /api/assinatura/`). Mudar de plano, forma de
// pagamento, faturas, dados da nota fiscal e comparar planos não têm rota; cancelar e pausar são da fase 2 (ver `[decisão]` no quadro).

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

/** Administração › Assinatura: o plano, o estado da assinatura e o uso dos limites. Só leitura nesta fase. */
export function AssinaturaDaEmpresa() {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["assinatura"], queryFn: () => api.obter(), enabled: podeVer });
  const a = podeVer ? consulta.data : undefined;

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa a Assinatura.
      </p>
    );

  const situacao = a ? situacaoDaAssinatura(a) : null;

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
      {a?.somente_leitura && (
        <p role="note" className="rounded-lg bg-surface-sunken p-4 text-body text-ink-muted">
          Sua empresa está só para consulta no momento. Dá para ver tudo, mas não para cadastrar ou alterar.
        </p>
      )}

      {a && situacao && (
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <div className="flex min-w-0 flex-col gap-6 md:flex-[999_1_560px]">
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
            </section>

            <section className="wl-panel" aria-label="Uso do plano">
              <h2 className="mb-4 text-heading">Uso do plano</h2>
              <div className="grid gap-4 md:grid-cols-[repeat(auto-fit,minmax(200px,1fr))] md:gap-3">
                {ITENS_DO_USO.map((item) => (
                  <Medidor key={item.chave} item={item} uso={a.uso[item.chave]} />
                ))}
              </div>
              <p className="mt-3.5 mb-0 text-caption text-ink-muted">Avisamos quando chegar a 90% de qualquer limite.</p>
            </section>
          </div>

          <aside className="flex min-w-0 flex-col gap-4 md:flex-[1_1_300px]" aria-label="Cancelamento">
            <section className="flex flex-col gap-2 px-2">
              <div>
                <Button compacto disabled aria-describedby="cancelar-ajuda">
                  Cancelar assinatura
                </Button>
              </div>
              <p id="cancelar-ajuda" className="m-0 text-caption text-ink-muted">
                O cancelamento por aqui chega em uma próxima versão. Você pode <Link href="/admin/exportar" className="underline">exportar os dados</Link> da auditoria a qualquer momento.
              </p>
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}

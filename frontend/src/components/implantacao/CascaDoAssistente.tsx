"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import type { ReactNode } from "react";
import { implantacao, type AndamentoDoAssistente } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { passoDe, passoTemTela, rotaDoPasso, vizinhos } from "@/lib/implantacao";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";
import { useSessao } from "@/lib/sessao";

// Referência: docs/telas/html/Onboarding-*-Desktop.dc.html e Onboarding-*-Mobile.dc.html (moldura comum dos passos 5 a 12).
// Quais passos existem, a ordem, o número e o que está feito vêm de GET /api/implantacao/ (docs/api/plataforma.md); a tela não conta nada.

/** Moldura do assistente: marca da empresa, "Salvar e sair", lista de passos (desktop) e barra de progresso (celular). Só o administrador. */
export function CascaDoAssistente({ passo, semPermissao = "Só o administrador faz a configuração inicial.", children }: { passo: string; semPermissao?: string; children: (andamento: AndamentoDoAssistente) => ReactNode }) {
  const { eu } = useSessao();
  const marca = useMarcaDaEmpresa();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["implantacao"], queryFn: () => implantacao.obter(), enabled: podeVer });

  if (!podeVer)
    return (
      <p role="alert" className="m-4 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        {semPermissao}
      </p>
    );

  const andamento = consulta.data;
  const atual = andamento ? passoDe(andamento, passo) : null;

  return (
    <div className="mx-auto flex min-h-screen max-w-[1200px] flex-col gap-6 bg-canvas p-4 md:p-6">
      <header className="flex items-center gap-3">
        <div className="wl-logo-slot" aria-hidden="true">
          {marca.logo ? (
            // eslint-disable-next-line @next/next/no-img-element -- logo servido pela API (S-12): sempre <img>, nunca inline
            <img src={marca.logo.url} alt="" width={40} height={40} style={{ borderRadius: "inherit", objectFit: "contain" }} />
          ) : (
            marca.iniciais
          )}
        </div>
        <span className="text-heading">{marca.nome}</span>
        <span className="hidden text-body text-ink-muted md:inline">Configuração inicial</span>
        <Link href="/inicio" className="wl-btn wl-btn--sm ml-auto md:h-12 md:px-5 md:text-[length:inherit]">
          <span className="hidden md:inline">Salvar e sair</span>
          <span className="md:hidden">Sair</span>
        </Link>
      </header>

      {consulta.isError && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando os passos…
        </p>
      )}
      {andamento && !atual && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          Este passo não faz parte da configuração inicial do seu plano.{" "}
          <Link href={andamento.proximo ? rotaDoPasso(andamento.proximo) : "/inicio"} className="underline">
            {andamento.proximo ? "Ir para o próximo passo" : "Voltar ao início"}
          </Link>
        </p>
      )}

      {andamento && atual && (
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <aside className="wl-panel hidden shrink-0 flex-col gap-4 md:flex md:w-[280px]" aria-label="Passos da configuração">
            <div>
              <div className="mb-2 text-caption text-ink-muted">
                Passo {atual.numero} de {andamento.total}
              </div>
              <div className="wl-progressbar" role="progressbar" aria-label="Passos da configuração" aria-valuemin={0} aria-valuemax={andamento.total} aria-valuenow={atual.numero}>
                <div className="wl-progressbar__fill" style={{ width: `${(atual.numero / andamento.total) * 100}%` }} />
              </div>
            </div>
            <ol className="m-0 flex list-none flex-col gap-0.5 p-0">
              {andamento.passos.map((p) => {
                const agora = p.passo === atual.passo;
                const classes = `flex min-h-[44px] items-center gap-3 rounded-pill px-3 text-body ${agora ? "bg-solid text-on-solid" : p.feito ? "text-ink" : "text-ink-muted"}`;
                const miolo = (
                  <>
                    <span className={`grid size-[26px] shrink-0 place-items-center rounded-full text-caption font-medium ${agora ? "bg-brand text-on-brand" : "bg-surface-sunken text-ink"}`}>{p.numero}</span>
                    {p.rotulo}
                    {p.feito && !agora && <span className="sr-only"> (feito)</span>}
                  </>
                );
                return (
                  <li key={p.passo} aria-current={agora ? "step" : undefined}>
                    {passoTemTela(p.passo) && !agora ? (
                      <Link href={rotaDoPasso(p.passo)} className={classes}>
                        {miolo}
                      </Link>
                    ) : (
                      <div className={classes}>{miolo}</div>
                    )}
                  </li>
                );
              })}
            </ol>
          </aside>

          <div className="flex min-w-0 flex-1 flex-col gap-6">
            <div className="md:hidden">
              <div className="mb-2 flex justify-between text-caption text-ink-muted">
                <span>
                  Passo {atual.numero} de {andamento.total}
                </span>
                {vizinhos(andamento, passo).seguinte && <span>{vizinhos(andamento, passo).seguinte?.rotulo} a seguir</span>}
              </div>
              <div className="flex gap-1" aria-hidden="true">
                {andamento.passos.map((p) => (
                  <span key={p.passo} className={`h-1.5 flex-1 rounded-pill ${p.numero <= atual.numero ? "bg-solid" : "bg-surface-sunken"}`} />
                ))}
              </div>
            </div>
            {children(andamento)}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight, Lock } from "lucide-react";
import Link from "next/link";
import { Icone } from "@/design-system";
import { configuracoes } from "@/lib/api";
import { CARTOES, destinoDaAcao } from "@/lib/configuracoes";
import { mensagemDoErro } from "@/lib/erros";
import { useSessao } from "@/lib/sessao";

// Referência: docs/telas/html/Config-Desktop.dc.html e Config-Mobile.dc.html.
// Título, resumo, ordem e quais cartões existem vêm da API (USR-05); a tela só liga a chave à rota e ao ícone. A faixa da implantação é só do desktop.

/** Administração › Configurações: um cartão por área, cada um leva à tela dela. Não edita nada. */
export function Configuracoes() {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["configuracoes"], queryFn: () => configuracoes.resumo(), enabled: podeVer });

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa Configurações.
      </p>
    );

  const d = consulta.data;
  const implantacao = d?.implantacao ?? null;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-3 md:items-end md:gap-4">
        <Link href="/mais" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 shrink-0 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1 text-caption text-ink-muted md:text-body">
            <Icone de={Lock} />
            Administração
          </div>
          <h1 className="text-title md:mt-1.5 md:text-display">Configurações</h1>
          <p className="mt-1.5 hidden text-body text-ink-muted md:block">Tudo o que muda como o sistema funciona para a sua empresa</p>
        </div>
      </header>

      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando as configurações…
        </p>
      )}

      {d && (
        <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-[repeat(auto-fill,minmax(300px,1fr))]">
          {d.cartoes.map((c) => {
            const destino = CARTOES[c.chave];
            if (!destino) return null;
            return (
              <li key={c.chave}>
                <Link href={destino.href} className="flex min-h-11 items-start gap-3.5 rounded-[22px] bg-surface p-4 text-ink no-underline md:rounded-[24px] md:p-5">
                  <span className="grid size-11 shrink-0 place-items-center rounded-[14px] bg-surface-sunken" aria-hidden="true">
                    <Icone de={destino.icone} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[16px] font-semibold">{c.titulo}</span>
                    <span className="mt-0.5 block text-[14px] text-ink-muted">{c.resumo}</span>
                  </span>
                  <span className="shrink-0 text-ink-muted" aria-hidden="true">
                    <Icone de={ChevronRight} />
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      {implantacao && (
        <section className="wl-panel hidden flex-wrap items-center gap-4 md:flex" aria-label="Implantação">
          <div className="min-w-[300px] flex-1">
            <div className="font-semibold">{implantacao.titulo}</div>
            <div className="text-[14px] text-ink-muted">{implantacao.faltam}</div>
          </div>
          {implantacao.acao && (
            <Link href={destinoDaAcao(implantacao.acao)} className="wl-btn wl-btn--solid">
              {implantacao.acao.rotulo}
            </Link>
          )}
        </section>
      )}
    </div>
  );
}

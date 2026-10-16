"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Aviso } from "@/components/acesso/Aviso";
import { ErroApi } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";

/** Erro da API em português. Sem caixa aberto (`FIN-07`), leva a pessoa direto ao caixa. */
export function ErroDoFinanceiro({ erro }: { erro: unknown }) {
  const semCaixa = erro instanceof ErroApi && erro.codigo === "FIN-07" && erro.status === 422;
  return (
    <Aviso tipo="erro">
      {mensagemDoErro(erro)}
      {semCaixa && (
        <>
          {" "}
          <Link href="/financeiro/caixa" className="underline">
            Abrir o caixa
          </Link>
        </>
      )}
    </Aviso>
  );
}

/** Confirmação de uma ação concluída, no topo da tela. */
export function Confirmacao({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="rounded-lg bg-brand-soft px-4 py-3 text-body">
      {children}
    </p>
  );
}

/** Linhas "rótulo ... valor" de um resumo (gaveta, valor do dia). */
export function LinhasDeValor({ linhas }: { linhas: { rotulo: string; valor: ReactNode; forte?: boolean }[] }) {
  return (
    <dl>
      {linhas.map((l) => (
        <div key={l.rotulo} className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
          <dt className={l.forte ? "font-medium" : "text-ink-muted"}>{l.rotulo}</dt>
          <dd className={`text-right ${l.forte ? "font-semibold" : "font-medium"}`}>{l.valor}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Escolha de uma opção entre poucas (forma de pagamento), em botões de 44px com foco visível. */
export function EscolhaDeOpcao<V extends string>({ rotulo, opcoes, valor, aoMudar, colunas = 3 }: { rotulo: string; opcoes: { valor: V; rotulo: string }[]; valor: V; aoMudar: (v: V) => void; colunas?: 2 | 3 }) {
  return (
    <fieldset className="flex flex-col">
      <legend className="wl-field__label mb-2">{rotulo}</legend>
      <div className={`grid gap-2 ${colunas === 3 ? "md:grid-cols-3" : "md:grid-cols-2"}`}>
        {opcoes.map((o) => (
          <label
            key={o.valor}
            className={`flex min-h-[44px] cursor-pointer items-center justify-center rounded-md px-4 text-body has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 ${valor === o.valor ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
          >
            <input type="radio" name={rotulo} value={o.valor} checked={valor === o.valor} onChange={() => aoMudar(o.valor)} className="sr-only" />
            {o.rotulo}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, DataTable, Dialogo, StatusBadge, type ColunaTabela } from "@/design-system";
import { assinatura as api, type CobrancaDaFatura, type FaturaDaAssinatura, type FormaDaAssinatura, type MeioDePagarFatura, type TomApi } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCompleta, dataCurta, dinheiro } from "@/lib/formatos";
import { tomDoStatus } from "@/lib/tom";
import { CodigoDePagamento } from "./ComunsDaAssinatura";

// Referência: "Faturas" das telas Admin-Assinatura. Situação, descrição, valor e as ações (Pagar, Recibo) vêm da API (PLT-14).

const MEIOS: { valor: MeioDePagarFatura; rotulo: string }[] = [
  { valor: "pix", rotulo: "Pagar por Pix" },
  { valor: "boleto", rotulo: "Pagar por boleto" },
  { valor: "cartao", rotulo: "Pagar com cartão" },
];

function Situacao({ f }: { f: FaturaDaAssinatura }) {
  return (
    <StatusBadge tom={tomDoStatus(f.situacao.tom as TomApi)} compacto>
      {f.situacao.rotulo}
    </StatusBadge>
  );
}

/** Pagar uma fatura: pela forma cadastrada ou por outro meio, sem trocar a forma. A API devolve a cobrança já emitida. */
function PagarFatura({ fatura, forma, aoFechar }: { fatura: FaturaDaAssinatura; forma: FormaDaAssinatura | null; aoFechar: () => void }) {
  const cliente = useQueryClient();
  const [cobranca, setCobranca] = useState<CobrancaDaFatura | null>(null);
  const codigo = fatura.codigo ?? "";
  const pagar = useMutation({
    mutationFn: (meio?: MeioDePagarFatura) => api.pagarFatura(codigo, meio),
    onSuccess: async (c) => {
      setCobranca(c);
      await cliente.invalidateQueries({ queryKey: ["assinatura"] });
    },
  });

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={`Pagar ${codigo}`}
      descricao={`${fatura.descricao} · ${dinheiro(fatura.valor_centavos)} · vence ${dataCompleta(fatura.vencimento)}`}
      acoes={
        <Button variante="quieto" onClick={aoFechar}>
          Fechar
        </Button>
      }
    >
      <div className="flex flex-col gap-3">
        {pagar.isError && (
          <p role="alert" className="rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(pagar.error)}
          </p>
        )}
        {!cobranca && (
          <div className="flex flex-col gap-2">
            {forma && (
              <Button variante="solido" disabled={pagar.isPending} onClick={() => pagar.mutate(undefined)}>
                {pagar.isPending ? "Gerando…" : "Pagar pela forma cadastrada"}
              </Button>
            )}
            <p className="text-caption text-ink-muted">{forma ? "Ou pague por outro meio, sem mudar a forma cadastrada:" : "Escolha como pagar:"}</p>
            <div className="flex flex-wrap gap-2">
              {MEIOS.map((m) => (
                <Button key={m.valor} variante="quieto" disabled={pagar.isPending} onClick={() => pagar.mutate(m.valor)}>
                  {m.rotulo}
                </Button>
              ))}
            </div>
          </div>
        )}
        {cobranca?.pix_copia_e_cola && <CodigoDePagamento rotulo={`Pix copia e cola · vence ${dataCompleta(cobranca.vencimento)}`} codigo={cobranca.pix_copia_e_cola} comQr={cobranca.forma !== "boleto"} />}
        {cobranca?.linha_digitavel && <CodigoDePagamento rotulo="Linha digitável do boleto" codigo={cobranca.linha_digitavel} />}
        {cobranca?.url_boleto && (
          <a href={cobranca.url_boleto} target="_blank" rel="noreferrer" className="wl-btn wl-btn--sm self-start">
            Abrir boleto
          </a>
        )}
        {cobranca?.url_pagina && (
          <div className="flex flex-col gap-2">
            <p className="text-body">Você digita o cartão na página do parceiro de pagamento. Ao terminar, volte para esta tela.</p>
            <Button variante="solido" onClick={() => window.location.assign(cobranca.url_pagina ?? "/admin/assinatura")}>
              Ir para a página do cartão
            </Button>
          </div>
        )}
      </div>
    </Dialogo>
  );
}

/** Tabela de faturas e a linha do teste, como a API manda. */
export function FaturasDaAssinatura({ forma }: { forma: FormaDaAssinatura | null }) {
  const [pagando, setPagando] = useState<FaturaDaAssinatura | null>(null);
  const [erroDoRecibo, setErroDoRecibo] = useState<string | null>(null);
  const lista = useQuery({ queryKey: ["assinatura", "faturas"], queryFn: () => api.faturas() });
  const recibo = useMutation({
    mutationFn: async (codigo: string) => (await api.fatura(codigo)).recibo_url,
    onSuccess: (url) => {
      setErroDoRecibo(url ? null : "O recibo ainda não está disponível.");
      if (url) window.open(url, "_blank", "noopener,noreferrer");
    },
    onError: (e) => setErroDoRecibo(mensagemDoErro(e)),
  });

  const acoes = (f: FaturaDaAssinatura) => (
    <span className="flex flex-wrap gap-2">
      {f.acoes.pagar && (
        <Button compacto variante="solido" onClick={() => setPagando(f)}>
          Pagar
        </Button>
      )}
      {f.acoes.recibo && f.codigo && (
        <Button compacto variante="quieto" disabled={recibo.isPending} onClick={() => recibo.mutate(f.codigo ?? "")}>
          Recibo
        </Button>
      )}
    </span>
  );

  const colunas: ColunaTabela<FaturaDaAssinatura>[] = [
    { chave: "vencimento", titulo: "Vencimento", mono: true, celula: (f) => dataCurta(f.vencimento) },
    { chave: "descricao", titulo: "Descrição", celula: (f) => f.descricao },
    { chave: "valor", titulo: "Valor", mono: true, celula: (f) => dinheiro(f.valor_centavos) },
    { chave: "situacao", titulo: "Situação", celula: (f) => <Situacao f={f} /> },
    { chave: "acoes", titulo: "", celula: acoes },
  ];
  const linhas = lista.data?.resultados ?? [];

  return (
    <section className="wl-panel" aria-label="Faturas">
      <h2 className="mb-4 text-heading">Faturas</h2>
      {lista.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando as faturas…
        </p>
      )}
      {lista.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(lista.error)}
        </p>
      )}
      {erroDoRecibo && (
        <p role="alert" className="mb-3 text-caption text-critical-ink">
          {erroDoRecibo}
        </p>
      )}
      {lista.data && linhas.length === 0 && <p className="text-body text-ink-muted">Nenhuma fatura ainda.</p>}
      {linhas.length > 0 && (
        <>
          <div className="hidden overflow-x-auto md:block">
            <DataTable colunas={colunas} linhas={linhas} chaveDaLinha={(f) => f.codigo ?? `${f.tipo}-${f.vencimento}`} legenda="Faturas da assinatura" />
          </div>
          <ul className="m-0 flex list-none flex-col gap-3 p-0 md:hidden" aria-label="Faturas da assinatura">
            {linhas.map((f) => (
              <li key={f.codigo ?? `${f.tipo}-${f.vencimento}`} className="flex flex-col gap-1.5 border-b border-line pb-3 last:border-b-0">
                <span className="wl-mono text-caption text-ink-muted">{dataCurta(f.vencimento)}</span>
                <span className="text-body">
                  {f.descricao} · {dinheiro(f.valor_centavos)}
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  <Situacao f={f} />
                  {acoes(f)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      {pagando && <PagarFatura fatura={pagando} forma={forma} aoFechar={() => setPagando(null)} />}
    </section>
  );
}

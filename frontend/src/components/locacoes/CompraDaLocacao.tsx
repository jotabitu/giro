"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Button, Panel, StatusBadge, TextField } from "@/design-system";
import { locacoes, type LocacaoCompleta } from "@/lib/api";
import { agoraDaTela } from "@/lib/ambiente";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCompleta, dataCurta, diaDe, dinheiro } from "@/lib/formatos";
import { textoDaTransferencia } from "@/lib/locacao-compra";
import { ROTULO_PERIODICIDADE } from "@/lib/clientes";

// Locação com intenção de compra (LOC-16, VEN-11, T-420).
// Referência: docs/telas/html/Locacao-Detalhe-Compra-*.dc.html e Locacao-Detalhe-Compra-Quitada-*.dc.html.
// A API monta o andamento e decide as ações; aqui só se mostra o que veio (parcelas, saldo e situação nunca são calculados na tela).

function Linha({ rotulo, children }: { rotulo: ReactNode; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

/** "Andamento da compra": o texto pronto da API, as parcelas pagas e o que ainda falta para quitar (`falta_para_quitar`). */
export function AndamentoDaCompra({ l }: { l: LocacaoCompleta }) {
  const c = l.compra;
  if (!c || !c.andamento) return null;
  const atrasada = l.sinais.pagamento_atrasado;
  return (
    <Panel
      titulo="Andamento da compra"
      acao={
        c.quitada_em ? (
          <StatusBadge tom="sucesso" compacto>
            {c.parcelas_pagas} de {c.parcelas_total} parcelas pagas
          </StatusBadge>
        ) : undefined
      }
    >
      <p className="m-0 text-body font-medium">{c.andamento}</p>
      {atrasada && <p className="m-0 mt-2 text-body text-ink-muted">{l.situacao.rotulo}</p>}
      {c.falta_para_quitar.length > 0 && (
        <ul className="m-0 mt-3 flex list-none flex-col p-0" aria-label="Falta para quitar">
          {c.falta_para_quitar.map((f, i) => (
            <li key={`${f.conta_id ?? "s"}-${i}`} className="flex justify-between gap-3 border-b border-line py-2.5 text-body last:border-b-0">
              <span>{f.rotulo}</span>
              {f.valor_centavos !== undefined && <span className="font-medium">{dinheiro(f.valor_centavos)}</span>}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** "Transferência no Detran" da locação quitada (VEN-11): pendente com a data e "Transferência feita", ou feita. */
export function TransferenciaDaCompra({ l, aoConcluir }: { l: LocacaoCompleta; aoConcluir: (m: string) => void }) {
  const cliente = useQueryClient();
  const venda = l.compra?.venda;
  const hoje = diaDe(agoraDaTela().toISOString());
  const [data, setData] = useState(hoje);
  const registrar = useMutation({
    mutationFn: () => locacoes.registrarTransferencia(l.id, { feita_em: data }),
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["locacao", l.id] }), cliente.invalidateQueries({ queryKey: ["vendas"] })]);
      aoConcluir("Transferência registrada.");
    },
  });
  if (!l.compra || !venda) return null;
  const t = venda.transferencia;
  return (
    <Panel
      titulo="Transferência no Detran"
      acao={
        <StatusBadge tom={t.pendente ? "alerta" : "sucesso"} compacto>
          {t.pendente ? "Pendente" : "Feita"}
        </StatusBadge>
      }
    >
      {t.pendente ? (
        <>
          <p className="m-0 text-body">{textoDaTransferencia(l)}</p>
          {venda.acoes.registrar_transferencia && (
            <form
              className="mt-4 flex flex-wrap items-end gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!registrar.isPending && data) registrar.mutate();
              }}
            >
              <div className="min-w-[200px] flex-1">
                <TextField cheio mono rotulo="Data da transferência" type="date" max={hoje} min={l.compra.quitada_em ? diaDe(l.compra.quitada_em) : undefined} value={data} onChange={(e) => setData(e.target.value)} erro={campoDoErro(registrar.error, "feita_em")} />
              </div>
              <Button variante="solido" type="submit" disabled={registrar.isPending || !data}>
                {registrar.isPending ? "Registrando…" : "Transferência feita"}
              </Button>
            </form>
          )}
          {registrar.isError && !campoDoErro(registrar.error, "feita_em") && (
            <p role="alert" className="m-0 mt-3 text-caption text-critical">
              {mensagemDoErro(registrar.error)}
            </p>
          )}
        </>
      ) : (
        <p className="m-0 text-body">
          Transferência feita em {t.feita_em ? dataCompleta(t.feita_em) : "—"}
          {t.registrada_por ? ` · ${t.registrada_por.nome}` : ""}
        </p>
      )}
      <p className="m-0 mt-3 text-caption text-ink-muted">
        Venda{" "}
        <Link href="/vendas" className="wl-mono text-ink">
          {venda.codigo}
        </Link>{" "}
        · Quitação de locação
      </p>
    </Panel>
  );
}

/** Resumo da locação com intenção de compra: o plano congelado, a parcela, a última com a caução abatida e a quitação. */
export function ResumoDaCompra({ l }: { l: LocacaoCompleta }) {
  const c = l.compra;
  if (!c) return null;
  const quitada = c.quitada_em;
  return (
    <Panel titulo="Resumo">
      <dl>
        <Linha rotulo="Plano">{c.plano?.nome ?? "—"}</Linha>
        {c.valor_parcela_centavos !== undefined && (
          <Linha rotulo="Parcela">
            {dinheiro(c.valor_parcela_centavos)} · {ROTULO_PERIODICIDADE[l.periodicidade].toLowerCase()}
          </Linha>
        )}
        {c.ultima_parcela_centavos !== undefined && <Linha rotulo="Última parcela">{dinheiro(c.ultima_parcela_centavos)}</Linha>}
        {quitada ? <Linha rotulo="Quitada em">{dataCompleta(quitada)}</Linha> : l.fim_previsto && <Linha rotulo="Fim previsto">{dataCurta(l.fim_previsto)}</Linha>}
        {l.precos && (
          <Linha rotulo="Caução">
            {dinheiro(l.precos.caucao_centavos)}
            {quitada ? " · abatida" : ""}
          </Linha>
        )}
      </dl>
    </Panel>
  );
}

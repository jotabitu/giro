"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo } from "@/design-system";
import { financeiro, type ContaReceber, type FormaDeRecebimento } from "@/lib/api";
import { dinheiro } from "@/lib/formatos";
import { useFilial } from "@/lib/filial-escolhida";
import { linhaDaConta, rotuloDaForma } from "@/lib/financeiro";
import { EscolhaDeOpcao, ErroDoFinanceiro, LinhasDeValor } from "./Comuns";

const FORMAS: FormaDeRecebimento[] = ["dinheiro", "cartao_debito", "cartao_credito"];

/** Baixa no caixa (FIN-04). O valor é o `valor_hoje.total_centavos` que a API calculou; a tela não soma multa nem juros. */
export function BaixaDaConta({ conta, aoFechar, aoConcluir }: { conta: ContaReceber; aoFechar: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const [forma, setForma] = useState<FormaDeRecebimento>("dinheiro");
  const todas = useFilial()?.todas ?? false;
  const v = conta.valor_hoje;
  const receber = useMutation({
    mutationFn: () => financeiro.receber(conta.id, { forma, valor_centavos: v.total_centavos }),
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["contas-receber"] }), cliente.invalidateQueries({ queryKey: ["caixa"] })]);
      aoConcluir(`${dinheiro(v.total_centavos)} recebidos de ${conta.cliente.nome}.`);
      aoFechar();
    },
    // O valor do dia pode ter mudado desde que a lista abriu: a API recusa e a lista se atualiza.
    onError: () => void cliente.invalidateQueries({ queryKey: ["contas-receber"] }),
  });

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={`Dar baixa em ${conta.cliente.nome}`}
      descricao={`${linhaDaConta(conta)}. O dinheiro entra no caixa de hoje.`}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={receber.isPending || todas} onClick={() => receber.mutate()}>
            {receber.isPending ? "Recebendo…" : `Receber ${dinheiro(v.total_centavos)}`}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="rounded-md bg-surface-sunken px-4 py-1">
          <LinhasDeValor
            linhas={[
              { rotulo: "Valor da parcela", valor: dinheiro(v.principal_centavos) },
              ...(v.multa_centavos > 0 ? [{ rotulo: "Multa", valor: dinheiro(v.multa_centavos) }] : []),
              ...(v.juros_centavos > 0 ? [{ rotulo: "Juros", valor: dinheiro(v.juros_centavos) }] : []),
              { rotulo: "Total hoje", valor: dinheiro(v.total_centavos), forte: true },
            ]}
          />
        </div>
        <EscolhaDeOpcao rotulo="Forma" opcoes={FORMAS.map((f) => ({ valor: f, rotulo: rotuloDaForma(f) }))} valor={forma} aoMudar={setForma} />
        {todas && <p className="text-caption text-ink-muted">O dinheiro entra no caixa de uma filial. Escolha a filial no menu para dar baixa.</p>}
        {receber.isError && <ErroDoFinanceiro erro={receber.error} />}
      </div>
    </Dialogo>
  );
}

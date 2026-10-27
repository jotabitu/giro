"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { financeiro, type MovimentoDoCaixa } from "@/lib/api";
import { campoDoErro } from "@/lib/erros";
import { dinheiro, horaCurta } from "@/lib/formatos";
import { ErroDoFinanceiro } from "./Comuns";

/**
 * Estorno de um movimento do caixa aberto (`POST caixas/{id}/movimentos/{mid}/estornar/`, CA-017-17).
 * Não se desfaz: nasce um movimento de estorno e o original continua na lista. Pede o motivo e confirma na própria tela.
 */
export function DialogoEstornarMovimento({ caixaId, movimento, aoFechar, aoConcluir }: { caixaId: number; movimento: MovimentoDoCaixa; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cliente = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const estornar = useMutation({
    mutationFn: () => financeiro.estornarMovimento(caixaId, movimento.id, motivo.trim()),
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["caixa"] }), cliente.invalidateQueries({ queryKey: ["contas-receber"] })]);
      aoConcluir("Movimento estornado. O estorno entrou no caixa de hoje e o original continua na lista.");
    },
  });

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Estornar movimento"
      descricao={`${horaCurta(movimento.hora)} · ${movimento.descricao} · ${dinheiro(movimento.valor_centavos)}. O estorno não se desfaz.`}
      tamanho="pequeno"
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={estornar.isPending || !motivo.trim()} onClick={() => estornar.mutate()}>
            {estornar.isPending ? "Estornando…" : "Estornar movimento"}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (motivo.trim() && !estornar.isPending) estornar.mutate();
        }}
      >
        <TextField cheio data-autofocus rotulo="Motivo do estorno" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(estornar.error, "motivo")} />
        <p className="m-0 text-caption text-ink-muted">Para devolver dinheiro a um cliente ou desfazer o recebimento de uma conta, use o estorno da conta em Contas a receber.</p>
        {estornar.isError && !campoDoErro(estornar.error, "motivo") && <ErroDoFinanceiro erro={estornar.error} />}
      </form>
    </Dialogo>
  );
}

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo } from "@/design-system";
import { assinatura as api, type Assinatura } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta } from "@/lib/formatos";

const OPCOES_PADRAO = [1, 2, 3];
const rotuloMeses = (m: number) => (m === 1 ? "1 mês" : `${m} meses`);

export type DialogoPausarProps = {
  aberto: boolean;
  mesesDisponiveis?: number[];
  inicio?: string;
  texto?: string;
  aoFechar: () => void;
  aoConcluir: (assinatura: Assinatura) => void;
};

/** Escolha de 1 a 3 meses para pausar a assinatura ativa (PLT-07, CA-ASS-37, CA-ASS-54). */
export function DialogoPausarAssinatura({ aberto, mesesDisponiveis = OPCOES_PADRAO, inicio, texto, aoFechar, aoConcluir }: DialogoPausarProps) {
  const cliente = useQueryClient();
  const [meses, setMeses] = useState<number>(mesesDisponiveis[0] ?? 1);
  const pausar = useMutation({
    mutationFn: () => api.pausar({ meses }),
    onSuccess: async (res) => {
      cliente.setQueryData(["assinatura"], res);
      await Promise.all([cliente.invalidateQueries({ queryKey: ["assinatura"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
      aoConcluir(res);
    },
  });

  const descricao = [
    texto ?? "Sem cobrança durante a pausa; seus dados ficam guardados para consulta.",
    inicio ? `Começa em ${dataCurta(inicio)}.` : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Dialogo
      aberto={aberto}
      aoFechar={aoFechar}
      titulo="Pausar assinatura"
      descricao={descricao}
      tamanho="pequeno"
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={pausar.isPending} onClick={() => pausar.mutate()}>
            {pausar.isPending ? "Pausando…" : "Confirmar pausa"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <div role="radiogroup" aria-label="Duração da pausa" className="grid grid-cols-3 gap-2">
          {mesesDisponiveis.map((m) => {
            const ativo = meses === m;
            return (
              <button
                key={m}
                type="button"
                role="radio"
                aria-checked={ativo}
                onClick={() => setMeses(m)}
                className={`rounded-md px-3 py-2.5 text-body font-medium ${ativo ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
              >
                {rotuloMeses(m)}
              </button>
            );
          })}
        </div>
        {pausar.isError && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(pausar.error)}
          </p>
        )}
      </div>
    </Dialogo>
  );
}

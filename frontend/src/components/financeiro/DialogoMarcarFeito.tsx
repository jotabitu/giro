"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Button, Dialogo } from "@/design-system";
import { financeiro, type Reembolso } from "@/lib/api";
import { TAMANHO_MAXIMO_DA_NOTA } from "@/lib/despesas";
import { campoDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { ErroDoFinanceiro } from "./Comuns";

/**
 * Marca o reembolso como feito (`POST reembolsos/{id}/feito/`, DEV-02), com o comprovante opcional.
 * A transferência acontece fora do sistema, pelo banco da locadora; aqui só se registra que foi feita.
 */
export function DialogoMarcarFeito({ reembolso, aoFechar, aoConcluir }: { reembolso: Reembolso; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cliente = useQueryClient();
  const arquivo = useRef<HTMLInputElement>(null);
  const [comprovante, setComprovante] = useState<File | null>(null);
  const [erroDoArquivo, setErroDoArquivo] = useState<string | null>(null);
  const marcar = useMutation({
    mutationFn: () => financeiro.marcarReembolsoFeito(reembolso.id, comprovante),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["reembolsos"] });
      await cliente.invalidateQueries({ queryKey: ["inicio"] });
      aoConcluir(`Reembolso de ${dinheiro(reembolso.valor_centavos)} para ${reembolso.cliente.nome} marcado como feito.`);
    },
  });

  function escolher(f: File | null) {
    if (f && f.size > TAMANHO_MAXIMO_DA_NOTA) {
      setErroDoArquivo("O comprovante pode ter até 10 MB. Escolha um arquivo menor.");
      setComprovante(null);
      if (arquivo.current) arquivo.current.value = "";
      return;
    }
    setErroDoArquivo(null);
    setComprovante(f);
  }

  const erroNoCampo = erroDoArquivo ?? campoDoErro(marcar.error, "comprovante");
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Marcar como feito"
      descricao={`${reembolso.cliente.nome} · ${dinheiro(reembolso.valor_centavos)} · ${reembolso.forma_rotulo}. Faça a transferência pelo banco da locadora antes de marcar.`}
      tamanho="pequeno"
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={marcar.isPending} onClick={() => marcar.mutate()}>
            {marcar.isPending ? "Marcando…" : "Marcar como feito"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <span className="wl-field__label">Comprovante (opcional)</span>
          <input ref={arquivo} type="file" accept="image/*,application/pdf" aria-label="Comprovante" onChange={(e) => escolher(e.target.files?.[0] ?? null)} className="min-h-[44px] text-body" />
          {erroNoCampo && (
            <span role="alert" className="text-caption text-critical-ink">
              {erroNoCampo}
            </span>
          )}
        </div>
        {marcar.isError && !campoDoErro(marcar.error, "comprovante") && <ErroDoFinanceiro erro={marcar.error} />}
      </div>
    </Dialogo>
  );
}

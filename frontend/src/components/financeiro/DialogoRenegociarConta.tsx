"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { financeiro, type ContaReceberDetalhe } from "@/lib/api";
import { campoDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";
import { ErroDoFinanceiro } from "./Comuns";

type Linha = { vencimento: string; valor: string };

const emReais = (centavos: number) => (centavos / 100).toFixed(2).replace(".", ",");

/**
 * Renegocia uma conta em aberto (`POST contas-receber/renegociar/`, FIN-01): a original vai para `renegociada`
 * e nascem as contas novas, nos vencimentos e valores daqui. A API confere a soma e o status; a tela só monta o pedido.
 * Não se desfaz, então pede o motivo e confirma na própria tela.
 */
export function DialogoRenegociarConta({ conta, aoFechar, aoConcluir }: { conta: ContaReceberDetalhe; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cliente = useQueryClient();
  const total = conta.valor_hoje.total_centavos;
  const [linhas, setLinhas] = useState<Linha[]>([{ vencimento: "", valor: emReais(total) }]);
  const [motivo, setMotivo] = useState("");
  const [erroLocal, setErroLocal] = useState<string | null>(null);

  const renegociar = useMutation({
    mutationFn: () => {
      const novas = linhas.map((l) => ({ vencimento: l.vencimento, valor_centavos: centavosDoTexto(l.valor) }));
      if (novas.some((n) => !n.vencimento || n.valor_centavos === null)) {
        setErroLocal("Informe o vencimento e o valor de cada conta nova.");
        throw new Error("linhas");
      }
      setErroLocal(null);
      return financeiro.renegociar({ contas: [conta.id], novas: novas.map((n) => ({ vencimento: n.vencimento, valor_centavos: n.valor_centavos! })), motivo: motivo.trim() });
    },
    onSuccess: async (novas) => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["contas-receber"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
      aoConcluir(novas.length === 1 ? "Conta renegociada. Nasceu 1 conta em aberto no lugar." : `Conta renegociada. Nasceram ${novas.length} contas em aberto no lugar.`);
    },
  });

  const mudar = (i: number, campo: keyof Linha, valor: string) => setLinhas((ls) => ls.map((l, j) => (j === i ? { ...l, [campo]: valor } : l)));

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Renegociar conta"
      descricao={`Valor devido hoje: ${dinheiro(total)}. A conta atual sai do em aberto e as contas novas ocupam o lugar dela. Isso não se desfaz.`}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={renegociar.isPending || !motivo.trim()} onClick={() => renegociar.mutate()}>
            {renegociar.isPending ? "Renegociando…" : "Renegociar conta"}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
        }}
      >
        <fieldset className="m-0 flex flex-col gap-3 border-0 p-0">
          <legend className="mb-1 text-body font-semibold">Contas novas</legend>
          {linhas.map((l, i) => (
            <div key={i} className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
              <label className="wl-field wl-field--cheio">
                <span className="wl-field__label">Vencimento {i + 1}</span>
                <input className="wl-input" type="date" value={l.vencimento} onChange={(e) => mudar(i, "vencimento", e.target.value)} />
              </label>
              <TextField cheio rotulo={`Valor ${i + 1} (R$)`} mono inputMode="decimal" autoComplete="off" value={l.valor} onChange={(e) => mudar(i, "valor", e.target.value)} />
              {linhas.length > 1 ? (
                <Button compacto variante="quieto" aria-label={`Tirar a conta nova ${i + 1}`} onClick={() => setLinhas((ls) => ls.filter((_, j) => j !== i))}>
                  Tirar
                </Button>
              ) : (
                <span />
              )}
            </div>
          ))}
          <div>
            <Button compacto variante="quieto" onClick={() => setLinhas((ls) => [...ls, { vencimento: "", valor: "" }])}>
              Adicionar conta nova
            </Button>
          </div>
        </fieldset>
        <TextField cheio rotulo="Motivo da renegociação" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(renegociar.error, "motivo")} />
        {erroLocal && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {erroLocal}
          </p>
        )}
        {renegociar.isError && !erroLocal && !campoDoErro(renegociar.error, "motivo") && <ErroDoFinanceiro erro={renegociar.error} />}
      </form>
    </Dialogo>
  );
}

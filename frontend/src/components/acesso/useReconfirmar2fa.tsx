"use client";

import { useCallback, useState, type ReactNode } from "react";
import { contas } from "@/lib/api";
import { comReconfirmacao, confirmarCodigo, ReconfirmacaoCancelada, type CorpoDoCodigo } from "@/lib/reconfirmar-2fa";
import { DialogoReconfirmar2fa } from "./DialogoReconfirmar2fa";

type Pedido = { mensagem: string; resolver: () => void; rejeitar: (erro: unknown) => void };

/**
 * Ponto único das ações que pedem 2 etapas recentes (403 `2fa_recente`; hoje o cancelamento da assinatura,
 * depois o backup completo da fase 2). `executar(acao)` roda a ação e, se a API pedir, abre o diálogo,
 * reconfirma e repete a ação uma vez. Renderize `dialogo` na tela; nada recarrega, então o que a pessoa já
 * preencheu continua lá. Cancelar o diálogo rejeita com `ReconfirmacaoCancelada`.
 */
export function useReconfirmar2fa(): { executar: <T>(acao: () => Promise<T>) => Promise<T>; dialogo: ReactNode } {
  const [pedido, setPedido] = useState<Pedido | null>(null);

  const executar = useCallback(
    <T,>(acao: () => Promise<T>) =>
      comReconfirmacao(
        acao,
        (mensagem) =>
          new Promise<void>((resolver, rejeitar) => {
            setPedido({ mensagem, resolver, rejeitar });
          }),
      ),
    [],
  );

  async function confirmar(p: Pedido, corpo: CorpoDoCodigo): Promise<string | null> {
    const r = await confirmarCodigo((c) => contas.reconfirmar2fa(c), corpo);
    if (r.tipo === "campo") return r.mensagem;
    setPedido(null);
    if (r.tipo === "ok") p.resolver();
    else p.rejeitar(r.erro);
    return null;
  }

  const dialogo = pedido ? (
    <DialogoReconfirmar2fa
      mensagem={pedido.mensagem}
      aoConfirmar={(corpo) => confirmar(pedido, corpo)}
      aoCancelar={() => {
        setPedido(null);
        pedido.rejeitar(new ReconfirmacaoCancelada());
      }}
    />
  ) : null;

  return { executar, dialogo };
}

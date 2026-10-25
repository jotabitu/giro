"use client";

import { useState } from "react";
import { Button, CodigoVerificacao, Dialogo, TextField } from "@/design-system";
import type { CorpoDoCodigo } from "@/lib/reconfirmar-2fa";

export type DialogoReconfirmar2faProps = {
  /** A `mensagem` do 403 `2fa_recente` ("Confirme o código do autenticador para cancelar a assinatura."). */
  mensagem: string;
  /** Envia o código; devolve o erro do campo (400) ou `null` se deu certo ou se o diálogo já foi fechado por outro motivo. */
  aoConfirmar: (corpo: CorpoDoCodigo) => Promise<string | null>;
  aoCancelar: () => void;
};

/** Pede de novo o código das 2 etapas sem sair da tela (USR-02). Mesmas palavras da etapa do código no Login. */
export function DialogoReconfirmar2fa({ mensagem, aoConfirmar, aoCancelar }: DialogoReconfirmar2faProps) {
  const [codigo, setCodigo] = useState("");
  const [recuperacao, setRecuperacao] = useState(false);
  const [codigoRec, setCodigoRec] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const pronto = recuperacao ? codigoRec.trim().length > 0 : codigo.length === 6;

  async function enviar() {
    if (!pronto || enviando) return;
    const corpo: CorpoDoCodigo = recuperacao ? { codigo_recuperacao: codigoRec.trim() } : { codigo };
    // O código não fica no estado depois do envio: só a variável local o leva até a chamada.
    setCodigo("");
    setCodigoRec("");
    setErro(null);
    setEnviando(true);
    const campo = await aoConfirmar(corpo);
    setEnviando(false);
    if (campo) setErro(campo);
  }

  return (
    <Dialogo
      aberto
      aoFechar={aoCancelar}
      titulo="Código de verificação"
      descricao={mensagem}
      tamanho="pequeno"
      fecharAoClicarFora={false}
      acoes={
        <>
          <Button variante="quieto" onClick={aoCancelar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={!pronto || enviando} onClick={() => void enviar()}>
            {enviando ? "Verificando…" : "Confirmar"}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <p className="m-0 text-body text-ink-muted">
          {recuperacao ? "Digite um dos códigos de recuperação. Cada um vale uma vez." : "Digite os 6 números que aparecem no aplicativo autenticador."}
        </p>
        {recuperacao ? (
          <TextField
            cheio
            rotulo="Código de recuperação"
            mono
            value={codigoRec}
            onChange={(e) => setCodigoRec(e.target.value)}
            autoComplete="off"
            erro={erro ?? undefined}
            autoFocus
          />
        ) : (
          <CodigoVerificacao rotulo="Código do aplicativo" valor={codigo} aoMudar={setCodigo} erro={erro ?? undefined} disabled={enviando} autoFocus />
        )}
        <button
          type="button"
          className="self-start text-caption underline"
          onClick={() => {
            setRecuperacao((v) => !v);
            setErro(null);
          }}
        >
          {recuperacao ? "Usar o código do aplicativo" : "Usar um código de recuperação"}
        </button>
      </form>
    </Dialogo>
  );
}

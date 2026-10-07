"use client";

import { useState } from "react";
import { Button, CodigoVerificacao, TextField } from "@/design-system";
import { contas, type Eu } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { Aviso } from "./Aviso";

/** Segunda etapa do login (`etapa: verificar_2fa`): código do aplicativo ou, se perdeu o celular, um código de recuperação. */
export function VerificarCodigo({ tokenPre, aoConcluir, aoVoltar }: { tokenPre: string; aoConcluir: (usuario: Eu) => void; aoVoltar: () => void }) {
  const [codigo, setCodigo] = useState("");
  const [recuperacao, setRecuperacao] = useState(false);
  const [codigoRec, setCodigoRec] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      const r = await contas.verificar2fa(tokenPre, recuperacao ? { codigo_recuperacao: codigoRec.trim() } : { codigo });
      if (r.etapa !== "pronto") throw new Error("etapa inesperada");
      aoConcluir(r.usuario);
    } catch (e) {
      setErro(mensagemDoErro(e));
      setCodigo("");
    } finally {
      setEnviando(false);
    }
  }

  const pronto = recuperacao ? codigoRec.trim().length > 0 : codigo.length === 6;

  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        if (pronto && !enviando) void enviar();
      }}
    >
      <div>
        <h1 className="text-title md:text-display">Código de verificação</h1>
        <p className="mt-2 text-body text-ink-muted">
          {recuperacao ? "Digite um dos códigos de recuperação. Cada um vale uma vez." : "Digite os 6 números que aparecem no aplicativo autenticador."}
        </p>
      </div>
      {recuperacao ? (
        <TextField cheio rotulo="Código de recuperação" mono value={codigoRec} onChange={(e) => setCodigoRec(e.target.value)} autoComplete="off" />
      ) : (
        <CodigoVerificacao rotulo="Código do aplicativo" valor={codigo} aoMudar={setCodigo} erro={erro ?? undefined} autoFocus />
      )}
      {erro && recuperacao && <Aviso tipo="erro">{erro}</Aviso>}
      <div className="grid">
        <Button type="submit" variante="solido" disabled={!pronto || enviando}>
          {enviando ? "Verificando…" : "Entrar"}
        </Button>
      </div>
      <div className="flex flex-wrap justify-between gap-2 text-caption">
        <button
          type="button"
          className="underline"
          onClick={() => {
            setRecuperacao((v) => !v);
            setErro(null);
          }}
        >
          {recuperacao ? "Usar o código do aplicativo" : "Perdi o celular"}
        </button>
        <button type="button" className="underline" onClick={aoVoltar}>
          Voltar para entrar
        </button>
      </div>
    </form>
  );
}

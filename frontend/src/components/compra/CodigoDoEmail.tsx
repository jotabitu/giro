"use client";

import { useState } from "react";
import { Button, CodigoVerificacao } from "@/design-system/components";
import { compraApi } from "@/lib/api/compra";
import { ErroApi } from "@/lib/api/tipos";
import type { AndamentoDoPedido, PedidoCriado } from "@/lib/api/tipos-compra";
import { mensagemDoErro } from "@/lib/erros";

/** Passo do código de 6 dígitos (D-430-01): sem ele, nenhum sistema é criado. */
export function CodigoDoEmail({
  pedido,
  aoConfirmar,
  aoRecomecar,
}: {
  pedido: PedidoCriado;
  aoConfirmar: (andamento: AndamentoDoPedido) => void;
  aoRecomecar: () => void;
}) {
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState<string | undefined>();
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [perdido, setPerdido] = useState(false);

  async function confirmar(valor: string) {
    setEnviando(true);
    setErro(undefined);
    setAviso(null);
    try {
      aoConfirmar(await compraApi.confirmar(pedido.chave, valor));
    } catch (e) {
      setCodigo("");
      if (e instanceof ErroApi && e.codigo === "pedido_nao_encontrado") setPerdido(true);
      setErro(e instanceof ErroApi ? e.message : mensagemDoErro(e));
    } finally {
      setEnviando(false);
    }
  }

  async function reenviar() {
    setErro(undefined);
    try {
      const r = await compraApi.reenviarCodigo(pedido.chave);
      setAviso(r.mensagem);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : mensagemDoErro(e));
    }
  }

  return (
    <main className="wl-panel" style={{ maxWidth: 520, width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 28, lineHeight: "34px", fontWeight: 600 }}>Confirme seu e-mail</h1>
        <p style={{ margin: "8px 0 0", color: "var(--ink-muted)" }}>{pedido.mensagem}</p>
      </div>
      <CodigoVerificacao
        rotulo={`Digite o código que enviamos para ${pedido.email}`}
        valor={codigo}
        aoMudar={setCodigo}
        aoCompletar={confirmar}
        erro={erro}
        disabled={enviando || perdido}
        autoFocus
      />
      {aviso && (
        <p role="status" style={{ margin: 0, color: "var(--success-ink)" }}>
          {aviso}
        </p>
      )}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {perdido ? (
          <Button variante="solido" onClick={aoRecomecar}>
            Escolher o plano de novo
          </Button>
        ) : (
          <>
            <Button variante="solido" disabled={enviando || codigo.length !== 6} onClick={() => confirmar(codigo)}>
              {enviando ? "Criando..." : "Criar meu sistema"}
            </Button>
            <Button variante="quieto" onClick={reenviar}>
              Reenviar código
            </Button>
          </>
        )}
      </div>
    </main>
  );
}

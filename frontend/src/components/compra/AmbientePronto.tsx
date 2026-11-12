"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, LoaderCircle } from "lucide-react";
import { Button } from "@/design-system/components";
import { Icone } from "@/design-system/Icone";
import { compraApi } from "@/lib/api/compra";
import type { AndamentoDoPedido } from "@/lib/api/tipos-compra";
import { horaEmSaoPaulo } from "@/lib/compra";
import { mensagemDoErro } from "@/lib/erros";

const CONSULTA_A_CADA_MS = 2000;

/** Tela 3 · Ambiente pronto (`Compra-Pronto`): acompanha a criação a cada 2 s e, no fim, leva ao convite (USR-01). */
export function AmbientePronto({ chave, inicial, aoRecomecar }: { chave: string; inicial: AndamentoDoPedido; aoRecomecar: () => void }) {
  const consulta = useQuery({
    queryKey: ["compra", "pedido", chave],
    queryFn: () => compraApi.andamento(chave),
    initialData: inicial,
    // `initialData` já é a resposta da confirmação: só consulta de novo enquanto cria.
    staleTime: Infinity,
    refetchInterval: (q) => (q.state.data?.status === "criando" ? CONSULTA_A_CADA_MS : false),
    retry: false,
  });
  const andamento = consulta.data;

  if (consulta.isError) {
    return (
      <main className="wl-panel" style={{ maxWidth: 560, margin: "0 auto" }}>
        <p role="alert" style={{ margin: 0 }}>
          {mensagemDoErro(consulta.error)}
        </p>
        <div style={{ marginTop: 16 }}>
          <Button variante="solido" onClick={aoRecomecar}>
            Escolher o plano de novo
          </Button>
        </div>
      </main>
    );
  }

  if (andamento.status === "falhou") {
    return (
      <main className="wl-panel" style={{ maxWidth: 560, margin: "0 auto" }}>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600 }}>Não deu certo</h1>
        <p role="alert" style={{ margin: "8px 0 0" }}>
          {andamento.mensagem}
        </p>
      </main>
    );
  }

  const pronto = andamento.status === "pronto";
  const nome = andamento.administrador?.nome;
  const email = andamento.administrador?.email;

  return (
    <main style={{ maxWidth: 640, width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 40, lineHeight: "44px", fontWeight: 600, letterSpacing: "-0.02em" }}>
          {pronto ? `Tudo pronto, ${nome}` : "Criando o seu sistema"}
        </h1>
        <p style={{ margin: "8px 0 0", color: "var(--ink-muted)" }}>
          {andamento.status === "confirmado"
            ? andamento.mensagem
            : pronto
              ? `O sistema da ${andamento.empresa?.nome_exibicao} já existe. Enviamos o link de acesso para ${email}.`
              : "Isso leva alguns segundos."}
        </p>
      </div>
      {andamento.empresa && (
        <section className="wl-panel">
          <p className="wl-mono" style={{ margin: 0, fontSize: 20 }}>
            {andamento.empresa.endereco}
          </p>
          <p style={{ margin: "4px 0 0", color: "var(--ink-muted)", fontSize: 14 }}>seu endereço</p>
        </section>
      )}
      {andamento.passos && (
        <section className="wl-panel" aria-live="polite">
          {andamento.passos.map((passo) => (
            <div key={passo.passo} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0" }}>
              <Icone de={passo.feito_em ? Check : LoaderCircle} />
              <span style={{ flex: 1 }}>{passo.texto}</span>
              {passo.feito_em && (
                <small className="wl-mono" style={{ color: "var(--ink-muted)" }}>
                  {horaEmSaoPaulo(passo.feito_em)}
                </small>
              )}
            </div>
          ))}
        </section>
      )}
      {pronto && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-start" }}>
          {andamento.acessar ? (
            <>
              <a className="wl-btn wl-btn--solid" href={andamento.acessar.url}>
                Acessar meu sistema
              </a>
              <span style={{ color: "var(--ink-muted)", fontSize: 14 }}>ou use o link do e-mail em qualquer aparelho</span>
            </>
          ) : (
            <p style={{ margin: 0 }}>Abra o link que enviamos para {email}.</p>
          )}
        </div>
      )}
    </main>
  );
}

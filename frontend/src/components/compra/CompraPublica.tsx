"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button } from "@/design-system/components";
import { compraApi } from "@/lib/api/compra";
import type { AndamentoDoPedido, PedidoCriado, PlanoAVenda } from "@/lib/api/tipos-compra";
import { guardarPedido, pedidoGuardado } from "@/lib/compra";
import { mensagemDoErro } from "@/lib/erros";
import { AmbientePronto } from "./AmbientePronto";
import { CabecalhoDaCompra } from "./Cabecalho";
import { Checkout } from "./Checkout";
import { CodigoDoEmail } from "./CodigoDoEmail";
import { EscolhaDoPlano, type Ciclo } from "./EscolhaDoPlano";

type Passo =
  | { tela: "planos" }
  | { tela: "checkout"; plano: PlanoAVenda }
  | { tela: "codigo"; pedido: PedidoCriado }
  | { tela: "pronto"; chave: string; andamento: AndamentoDoPedido };

/**
 * Compra pública (`docs/api/compra.md`): escolha do plano, criar conta, código no e-mail e ambiente pronto, numa
 * rota só. A chave do pedido fica em memória e no sessionStorage da aba, nunca na URL. Marca Giro (tela de compra).
 */
export function CompraPublica() {
  const [passo, setPasso] = useState<Passo>({ tela: "planos" });
  const [ciclo, setCiclo] = useState<Ciclo>("mensal");
  const catalogo = useQuery({ queryKey: ["compra", "planos"], queryFn: () => compraApi.planos(), staleTime: 5 * 60_000, retry: 1 });

  // Volta à criação em andamento depois de recarregar a aba (o pedido ainda sem código recomeça do plano).
  useEffect(() => {
    const chave = pedidoGuardado();
    if (!chave) return;
    compraApi
      .andamento(chave)
      .then((andamento) => {
        if (andamento.status !== "aguardando_confirmacao") setPasso({ tela: "pronto", chave, andamento });
        else guardarPedido(null);
      })
      .catch(() => guardarPedido(null));
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [passo.tela]);

  function recomecar() {
    guardarPedido(null);
    setPasso({ tela: "planos" });
  }

  let conteudo;
  if (passo.tela === "pronto") {
    conteudo = <AmbientePronto chave={passo.chave} inicial={passo.andamento} aoRecomecar={recomecar} />;
  } else if (passo.tela === "codigo") {
    conteudo = (
      <CodigoDoEmail
        pedido={passo.pedido}
        aoRecomecar={recomecar}
        aoConfirmar={(andamento) => setPasso({ tela: "pronto", chave: passo.pedido.chave, andamento })}
      />
    );
  } else if (catalogo.isPending) {
    conteudo = <p style={{ textAlign: "center", color: "var(--ink-muted)" }}>Carregando os planos...</p>;
  } else if (catalogo.isError) {
    conteudo = (
      <div style={{ textAlign: "center" }}>
        <p role="alert">{mensagemDoErro(catalogo.error)}</p>
        <Button onClick={() => catalogo.refetch()}>Tentar de novo</Button>
      </div>
    );
  } else if (passo.tela === "checkout") {
    conteudo = (
      <Checkout
        catalogo={catalogo.data}
        plano={passo.plano}
        ciclo={ciclo}
        aoTrocarPlano={() => setPasso({ tela: "planos" })}
        aoCriar={(pedido) => {
          guardarPedido(pedido.chave);
          setPasso({ tela: "codigo", pedido });
        }}
      />
    );
  } else {
    conteudo = <EscolhaDoPlano catalogo={catalogo.data} ciclo={ciclo} aoMudarCiclo={setCiclo} aoEscolher={(plano) => setPasso({ tela: "checkout", plano })} />;
  }

  return (
    <div style={{ minHeight: "100vh", boxSizing: "border-box", padding: 24, display: "flex", flexDirection: "column", gap: 32, background: "var(--canvas)", color: "var(--ink)" }}>
      <CabecalhoDaCompra />
      {conteudo}
    </div>
  );
}

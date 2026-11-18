"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, Clock, CreditCard, X } from "lucide-react";
import { limites } from "@/components/compra/EscolhaDoPlano";
import { Icone } from "@/design-system/Icone";
import { compraApi } from "@/lib/api/compra";
import type { CatalogoDaCompra } from "@/lib/api/tipos-compra";
import { reaisInteiros } from "@/lib/compra";
import { ID_TITULO_PLANOS } from "./IrParaPlanos";
import { LINK_TESTE_GRATIS, linkDoPlano } from "./links";

/**
 * Cartões dos planos (T-490): os planos à venda, os preços e o que cada um inclui vêm do mesmo catálogo público
 * que a /compra usa (`GET /api/publico/compra/planos/`, PLT-11). A tela não escreve texto nem preço de plano. O
 * plano em destaque leva o mesmo selo da /compra ("Mais escolhido"); o Completo só aparece se a API o vender.
 */
export function CartoesDaLanding({ catalogo }: { catalogo: CatalogoDaCompra }) {
  return (
    <div className="plans">
      {catalogo.planos.map((p) => (
        <article key={p.codigo} className={p.destaque ? "wl-panel plan pro" : "wl-panel plan"}>
          <h3>{p.nome}{p.destaque && <> <span className="wl-badge wl-badge--sm wl-badge--brand">Mais escolhido</span></>}</h3>
          <div className="price"><b>{reaisInteiros(p.mensal_centavos)}</b><span className="wl-muted">/mês</span></div>
          <p className="wl-muted">{p.descricao}</p>
          <ul>
            {[...limites(p), ...p.inclui].map((item) => <li key={item}><Icone de={Check} />{item}</li>)}
          </ul>
          <a className={p.destaque ? "wl-btn wl-btn--brand" : "wl-btn wl-btn--quiet"} href={linkDoPlano(p.codigo)}>Começar teste grátis</a>
        </article>
      ))}
    </div>
  );
}

export function Planos() {
  const catalogo = useQuery({ queryKey: ["compra", "planos"], queryFn: () => compraApi.planos(), staleTime: 5 * 60_000, retry: 1 });
  return (
    <section id="planos" style={{ background: "var(--surface-sunken)" }}>
      <div className="wrap">
        <div className="head">
          <p className="over">Planos</p>
          <h2 className="h2" id={ID_TITULO_PLANOS} tabIndex={-1}>Comece grátis e escolha o plano depois.</h2>
        </div>
        {catalogo.data ? (
          <CartoesDaLanding catalogo={catalogo.data} />
        ) : catalogo.isError ? (
          <p className="wl-muted">
            Não conseguimos mostrar os planos agora. <a href={LINK_TESTE_GRATIS}>Veja os planos e comece o teste</a>.
          </p>
        ) : (
          <p className="wl-muted" role="status">Carregando os planos...</p>
        )}
        <div className="terms">
          <span className="wl-badge wl-badge--surface"><Icone de={Clock} />14 dias grátis</span>
          <span className="wl-badge wl-badge--surface"><Icone de={CreditCard} />Sem cartão</span>
          <span className="wl-badge wl-badge--surface"><Icone de={X} />Cancele quando quiser</span>
        </div>
      </div>
    </section>
  );
}

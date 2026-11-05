"use client";

import { Check } from "lucide-react";
import { Button, SegmentedControl } from "@/design-system/components";
import { Icone } from "@/design-system/Icone";
import type { CatalogoDaCompra, PlanoAVenda } from "@/lib/api/tipos-compra";
import { reaisInteiros } from "@/lib/compra";

export type Ciclo = "mensal" | "anual";

const CICLOS = [
  { valor: "mensal", rotulo: "Mensal" },
  { valor: "anual", rotulo: "Anual · 2 meses grátis" },
] as const;

function limites(plano: PlanoAVenda): string[] {
  const { veiculos, filiais, usuarios } = plano.limites;
  const linhas: string[] = [];
  linhas.push(veiculos === null ? "Sem limite de veículos" : `Até ${veiculos} veículos`);
  if (filiais !== null && usuarios !== null) {
    linhas.push(`${filiais} ${filiais === 1 ? "filial" : "filiais"} e ${usuarios} usuários`);
  }
  return linhas;
}

/** Tela 1 · Escolha do plano (`Compra-Planos`): só os planos à venda, com os textos da API (PLT-11). */
export function EscolhaDoPlano({
  catalogo,
  ciclo,
  aoMudarCiclo,
  aoEscolher,
}: {
  catalogo: CatalogoDaCompra;
  ciclo: Ciclo;
  aoMudarCiclo: (ciclo: Ciclo) => void;
  aoEscolher: (plano: PlanoAVenda) => void;
}) {
  return (
    <main style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24, textAlign: "center" }}>
      <span className="wl-badge">{catalogo.teste.dias} dias grátis · sem cartão</span>
      <div>
        <h1 style={{ margin: 0, fontSize: 40, lineHeight: "44px", fontWeight: 600, letterSpacing: "-0.02em" }}>
          Escolha o plano da sua locadora
        </h1>
        <p style={{ margin: "8px 0 0", color: "var(--ink-muted)" }}>
          Frota, contratos, vistorias e cobranças com a sua marca. Troque de plano quando quiser.
        </p>
      </div>
      <SegmentedControl rotulo="Ciclo de cobrança" opcoes={CICLOS} valor={ciclo} aoMudar={aoMudarCiclo} />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 20,
          width: "100%",
          maxWidth: 860,
          textAlign: "left",
        }}
      >
        {catalogo.planos.map((plano) => {
          const centavos = ciclo === "anual" ? plano.anual_centavos : plano.mensal_centavos;
          return (
            <section key={plano.codigo} className="wl-panel" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <h2 style={{ margin: 0, fontSize: 22, fontWeight: 600 }}>{plano.nome}</h2>
                {plano.destaque && <span className="wl-badge">Mais escolhido</span>}
              </div>
              <p style={{ margin: 0, color: "var(--ink-muted)" }}>{plano.descricao}</p>
              <p style={{ margin: 0, fontSize: 34, fontWeight: 600 }}>
                {reaisInteiros(centavos)}
                <small style={{ fontSize: 15, fontWeight: 400, color: "var(--ink-muted)" }}>{ciclo === "anual" ? " /ano" : " /mês"}</small>
              </p>
              <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
                {[...limites(plano), ...plano.inclui].map((linha) => (
                  <li key={linha} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <Icone de={Check} />
                    {linha}
                  </li>
                ))}
              </ul>
              <div style={{ marginTop: "auto" }}>
                <Button variante={plano.destaque ? "solido" : "padrao"} onClick={() => aoEscolher(plano)}>
                  {plano.destaque ? "Começar teste grátis" : "Começar teste"}
                </Button>
              </div>
            </section>
          );
        })}
      </div>
      <p style={{ margin: 0, color: "var(--ink-muted)", fontSize: 14 }}>Sem fidelidade · cancele quando quiser</p>
    </main>
  );
}

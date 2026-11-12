import { Lock } from "lucide-react";
import { Icone } from "@/design-system/Icone";

/** Topo das telas de compra: marca Giro (SVG do kit, com o próprio fundo grafite) e "Conexão segura". */
export function CabecalhoDaCompra() {
  return (
    <header style={{ display: "flex", alignItems: "center", gap: 12 }}>
      {/* eslint-disable-next-line @next/next/no-img-element -- logo do kit de marca (docs/marca/kit), sempre por SVG */}
      <img src="/marca/giro-horizontal-fundo.svg" alt="Giro" width={97} height={36} style={{ borderRadius: 10 }} />
      <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "var(--ink-muted)" }}>
        <Icone de={Lock} />
        Conexão segura
      </span>
    </header>
  );
}

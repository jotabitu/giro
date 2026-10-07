"use client";

import Link from "next/link";
import { useState } from "react";
import { aplicarMarca, aplicarTema, hexValido, MARCA_PADRAO, type Tema } from "@/design-system/marca";
import { SegmentedControl } from "@/design-system/components";

const TEMAS = [
  { valor: "light", rotulo: "Claro" },
  { valor: "dark", rotulo: "Escuro" },
] as const;

/** Barra do preview: troca de tema e da cor da empresa em execução. */
export function Controles() {
  const [tema, setTema] = useState<Tema>("light");
  const [marca, setMarca] = useState(MARCA_PADRAO);

  return (
    <div className="wl-panel flex flex-wrap items-center gap-4">
      <Link href="/design-system" className="text-heading">
        Design system
      </Link>
      <SegmentedControl
        rotulo="Tema"
        opcoes={TEMAS}
        valor={tema}
        aoMudar={(t) => {
          setTema(t);
          aplicarTema(t);
        }}
      />
      <label className="flex items-center gap-2 text-caption text-ink-muted">
        Cor da empresa
        <input
          type="color"
          value={marca}
          aria-label="Cor da empresa"
          onChange={(e) => {
            if (hexValido(e.target.value)) {
              setMarca(e.target.value);
              aplicarMarca(e.target.value);
            }
          }}
        />
        <span className="wl-mono">{marca}</span>
      </label>
    </div>
  );
}

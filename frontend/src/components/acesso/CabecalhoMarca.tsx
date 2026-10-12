"use client";

import { useMarcaDaEmpresa } from "@/lib/marca-empresa";

/** Logo e nome da locadora (white label). A marca Giro só aparece no rodapé "Tecnologia Giro". */
export function CabecalhoMarca() {
  const marca = useMarcaDaEmpresa();
  return (
    <div className="flex items-center gap-3">
      <div className="wl-logo-slot" aria-hidden="true">
        {marca.logo ? (
          // eslint-disable-next-line @next/next/no-img-element -- logo servido pela API (S-12): sempre <img>, nunca inline
          <img src={marca.logo.url} alt="" width={40} height={40} style={{ borderRadius: "inherit", objectFit: "contain" }} />
        ) : (
          marca.iniciais
        )}
      </div>
      <span className="text-heading">{marca.nome}</span>
    </div>
  );
}

export function RodapeGiro() {
  return (
    <div className="flex flex-wrap justify-between gap-2 text-caption text-ink-muted">
      <span>Tecnologia Giro</span>
      <span>Termos de uso · Privacidade</span>
    </div>
  );
}

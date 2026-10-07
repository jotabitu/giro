"use client";

import { useMarcaDaEmpresa } from "@/lib/marca-empresa";

function iniciais(nome: string) {
  return nome.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

/** Logo e nome da locadora (white label). A marca Giro só aparece no rodapé "Tecnologia Giro". */
export function CabecalhoMarca() {
  const marca = useMarcaDaEmpresa();
  return (
    <div className="flex items-center gap-3">
      <div className="wl-logo-slot" aria-hidden="true">
        {marca.logoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- logo da empresa vem de URL externa (S3)
          <img src={marca.logoUrl} alt="" width={40} height={40} style={{ borderRadius: "inherit", objectFit: "cover" }} />
        ) : (
          iniciais(marca.nome)
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

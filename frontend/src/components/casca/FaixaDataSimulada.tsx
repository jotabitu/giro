"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { TriangleAlert } from "lucide-react";
import { Icone } from "@/design-system";
import { ambiente as ambienteApi, type Ambiente } from "@/lib/api";
import { definirAmbiente, escopoDaRota, useAmbiente } from "@/lib/ambiente";
import { dataCompleta } from "@/lib/formatos";

/** Faixa fixa no topo, sem fechar, enquanto a API diz que a data é simulada (ADR 0021). */
export function FaixaDataSimulada({ ambiente }: { ambiente: Ambiente | null }) {
  if (!ambiente?.data_simulada) return null;
  return (
    <div role="status" className="sticky top-0 z-50 flex items-center justify-center gap-2 bg-warning-soft px-4 py-2 text-caption text-warning-ink">
      <Icone de={TriangleAlert} />
      <span>Data simulada: {dataCompleta(`${ambiente.hoje}T12:00:00-03:00`)}. Ambiente de desenvolvimento.</span>
    </div>
  );
}

const RENOVAR_EM = 5 * 60_000;

/** Lê o ambiente da API (uma vez por escopo e a cada 5 min), publica o "hoje" para as telas e mostra a faixa. */
export function AmbienteDaTela() {
  const escopo = escopoDaRota(usePathname() ?? "/");
  const ambiente = useAmbiente();
  useEffect(() => {
    let vivo = true;
    const ler = () => void ambienteApi.obter(escopo).then((a) => vivo && definirAmbiente(a));
    ler();
    const id = setInterval(ler, RENOVAR_EM);
    return () => {
      vivo = false;
      clearInterval(id);
    };
  }, [escopo]);
  return <FaixaDataSimulada ambiente={ambiente} />;
}

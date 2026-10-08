"use client";

import { useEffect } from "react";
import { aplicarMarca } from "@/design-system";
import { marcaDaEmpresa } from "@/lib/api";

/** Marca da locadora (logo, cor, nome): aplica --brand, --on-brand e --brand-soft em execução. */
export function useMarcaDaEmpresa() {
  const marca = marcaDaEmpresa;
  useEffect(() => {
    aplicarMarca(marca.corHex);
  }, [marca.corHex]);
  return marca;
}

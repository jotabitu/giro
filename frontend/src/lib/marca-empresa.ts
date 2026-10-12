"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { ID_ESTILO_MARCA } from "@/design-system";
import { marca as marcaApi } from "@/lib/api";
import { cssDaMarcaDaApi, MARCA_NEUTRA, marcaDaTela, type MarcaDaTela } from "@/lib/marca";

/**
 * Marca da locadora (GET /api/marca/, a mesma com ou sem sessão): aplica --brand, --on-brand e --brand-soft
 * com as cores que a API calculou e devolve nome, iniciais e logo. Uma leitura por carga, renovada a cada 5 min.
 * Sem empresa no host (404) ou com falha, vale a marca neutra.
 */
export function useMarcaDaEmpresa(): MarcaDaTela {
  const { data } = useQuery({ queryKey: ["marca"], queryFn: () => marcaApi.obter(), staleTime: 5 * 60_000 });
  const css = data ? cssDaMarcaDaApi(data) : null;
  useEffect(() => {
    const el = document.getElementById(ID_ESTILO_MARCA);
    if (css && el) el.textContent = css;
  }, [css]);
  return data === undefined ? MARCA_NEUTRA : marcaDaTela(data);
}

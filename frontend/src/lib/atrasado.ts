"use client";

import { useEffect, useState } from "react";

/** O valor de `valor` só depois de `ms` sem mudar: a simulação de preços chama a API com isso, não a cada tecla. */
export function useAtrasado<T>(valor: T, ms = 400): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return atrasado;
}

/** `true` no celular (até 720px, o mesmo ponto de quebra dos estilos). No servidor e no primeiro render é `false`. */
export function useCelular(): boolean {
  const [celular, setCelular] = useState(false);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const m = window.matchMedia("(max-width: 720px)");
    const atualizar = () => setCelular(m.matches);
    atualizar();
    m.addEventListener("change", atualizar);
    return () => m.removeEventListener("change", atualizar);
  }, []);
  return celular;
}

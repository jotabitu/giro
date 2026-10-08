"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

/** Filtros da lista na própria URL: o link da lista filtrada se compartilha e o voltar do navegador funciona. */
export function useFiltrosNaUrl() {
  const params = useSearchParams();
  const rota = usePathname();
  const router = useRouter();

  const definir = useCallback(
    (mudancas: Record<string, string | null>) => {
      const novo = new URLSearchParams(params.toString());
      for (const [chave, valor] of Object.entries(mudancas)) {
        if (valor === null || valor === "") novo.delete(chave);
        else novo.set(chave, valor);
      }
      // Qualquer mudança de filtro volta para a primeira página.
      if (!("cursor" in mudancas)) novo.delete("cursor");
      const texto = novo.toString();
      router.replace(texto ? `${rota}?${texto}` : rota, { scroll: false });
    },
    [params, rota, router],
  );

  return { valor: (chave: string) => params.get(chave), definir };
}

/** Campo de busca com atraso de 300 ms antes de ir para a URL (e para a API). Devolve o texto digitado e o já aplicado. */
export function useBuscaNaUrl(definir: (m: Record<string, string | null>) => void, naUrl: string) {
  const [texto, setTexto] = useState(naUrl);
  useEffect(() => {
    if (texto === naUrl) return;
    const t = setTimeout(() => definir({ busca: texto }), 300);
    return () => clearTimeout(t);
  }, [texto, naUrl, definir]);
  return [texto, setTexto] as const;
}

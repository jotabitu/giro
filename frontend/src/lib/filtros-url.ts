"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

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

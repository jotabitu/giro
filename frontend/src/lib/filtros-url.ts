"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { paginaDoCursor, type AoIrPagina } from "@/lib/paginacao";

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
      // Qualquer mudança de filtro volta para a primeira página (cursor e número saem juntos).
      if (!("cursor" in mudancas)) {
        novo.delete("cursor");
        novo.delete("pagina");
      }
      const texto = novo.toString();
      router.replace(texto ? `${rota}?${texto}` : rota, { scroll: false });
    },
    [params, rota, router],
  );

  // Número da página na URL ao lado do cursor: estado de navegação, a API pagina só por cursor.
  const pagina = paginaDoCursor(params.get("cursor"), params.get("pagina"));
  const aoIr = useCallback<AoIrPagina>((cursor, p) => definir({ cursor, pagina: cursor && p > 1 ? String(p) : null }), [definir]);

  return { valor: (chave: string) => params.get(chave), definir, paginacao: { pagina, aoIr } };
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

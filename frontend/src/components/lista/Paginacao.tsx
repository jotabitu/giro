"use client";

import type { ReactNode } from "react";
import { Button } from "@/design-system";

/** Paginação por cursor da API (`proximo` e `anterior`). O texto de contagem vem pronto de quem chama. */
export function Paginacao({ texto, anterior, proximo, aoIr, extra }: { texto: string; anterior: string | null; proximo: string | null; aoIr: (cursor: string | null) => void; extra?: ReactNode }) {
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-caption text-ink-muted">
      <span>{texto}</span>
      <div className="flex flex-wrap gap-2">
        {extra}
        <Button variante="quieto" compacto disabled={anterior === null} onClick={() => aoIr(anterior === "0" ? null : anterior)}>
          Anterior
        </Button>
        <Button variante="quieto" compacto disabled={proximo === null} onClick={() => aoIr(proximo)}>
          Próxima
        </Button>
      </div>
    </div>
  );
}

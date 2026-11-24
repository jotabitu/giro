"use client";

import { useCallback, useState, type ReactNode } from "react";
import { Button } from "@/design-system";
import { paginaDoCursor, type AoIrPagina } from "@/lib/paginacao";

/**
 * Paginação por cursor da API (`proximo` e `anterior`). O texto de contagem vem pronto de quem chama.
 * A API não devolve o número da página: ele é estado de navegação (soma 1 no Próxima, tira 1 no Anterior).
 */
export function Paginacao({ texto, anterior, proximo, pagina, aoIr, extra }: { texto: string; anterior: string | null; proximo: string | null; pagina: number; aoIr: AoIrPagina; extra?: ReactNode }) {
  const voltar = () => {
    const cursor = anterior === "0" ? null : anterior;
    aoIr(cursor, cursor === null ? 1 : Math.max(1, pagina - 1));
  };
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-caption text-ink-muted">
      <span>{texto}</span>
      <div className="flex flex-wrap items-center gap-2">
        {extra}
        {/* Anterior, número e Próxima ficam juntos numa linha; se faltar espaço, quem quebra é o extra. */}
        <div className="flex items-center gap-2">
          <Button variante="quieto" compacto disabled={anterior === null} onClick={voltar}>
            Anterior
          </Button>
          <span aria-current="page" className="min-w-6 text-center tabular-nums text-ink">
            <span className="sr-only">Página </span>
            {pagina}
          </span>
          <Button variante="quieto" compacto disabled={proximo === null} onClick={() => aoIr(proximo, pagina + 1)}>
            Próxima
          </Button>
        </div>
      </div>
    </div>
  );
}

/** Cursor e página guardados no estado do componente, para as listas que não levam o cursor à URL. */
export function usePaginaLocal() {
  const [estado, setEstado] = useState<{ cursor: string | null; pagina: number }>({ cursor: null, pagina: 1 });
  const aoIr = useCallback<AoIrPagina>((cursor, pagina) => setEstado({ cursor, pagina: paginaDoCursor(cursor, pagina) }), []);
  const voltarAoInicio = useCallback(() => setEstado({ cursor: null, pagina: 1 }), []);
  return { cursor: estado.cursor, pagina: estado.pagina, aoIr, voltarAoInicio };
}

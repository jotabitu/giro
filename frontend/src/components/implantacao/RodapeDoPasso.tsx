"use client";

import Link from "next/link";
import { Button } from "@/design-system";

/**
 * Botões de todo passo do assistente (docs/api/plataforma.md, "Rotas de cada passo"): "Voltar" e "Pular por agora" só navegam
 * (não marcam passo, IMP-05); "Continuar" é do passo e só vale depois que a API marcou o passo como feito.
 */
export function RodapeDoPasso({
  voltarPara,
  pularPara,
  rotuloDePular = "Pular por agora",
  rotuloDeContinuar = "Continuar",
  podeContinuar,
  continuando = false,
  aoContinuar,
}: {
  voltarPara: string;
  pularPara: string;
  rotuloDePular?: string;
  rotuloDeContinuar?: string;
  /** `true` quando a API já marcou o passo (relida depois de gravar). */
  podeContinuar: boolean;
  continuando?: boolean;
  aoContinuar: () => void;
}) {
  return (
    <div className="mt-auto flex flex-wrap items-center gap-3 border-t border-line pt-4">
      <Link href={voltarPara} className="wl-btn wl-btn--quiet">
        Voltar
      </Link>
      <Link href={pularPara} className="wl-btn wl-btn--quiet">
        {rotuloDePular}
      </Link>
      <span className="ml-auto">
        <Button variante="solido" disabled={!podeContinuar || continuando} onClick={aoContinuar}>
          {continuando ? "Salvando…" : rotuloDeContinuar}
        </Button>
      </span>
    </div>
  );
}

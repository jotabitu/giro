"use client";

import { TextField } from "@/design-system";

/** Valor em reais digitado como "54,90"; a conversão para centavos e a validação final são de `lib/precos` e da API. */
export function CampoDeDinheiro({ rotulo, valor, aoMudar, erro, disabled }: { rotulo: string; valor: string; aoMudar: (v: string) => void; erro?: string; disabled?: boolean }) {
  return <TextField cheio rotulo={rotulo} mono inputMode="decimal" autoComplete="off" value={valor} onChange={(e) => aoMudar(e.target.value)} erro={erro} disabled={disabled} />;
}

"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Icone, IconButton } from "@/design-system";

// A seta que recolhe e abre um bloco de Planos e preços (T-507 no aluguel, T-508 na locação com compra).
// O bloco começa aberto; com a oferta desligada, começa recolhido. Erro dentro do bloco o mantém aberto.

/** Transição pura: o bloco está aberto se não foi recolhido ou se há erro nele; a seta inverte o que se vê. */
export function estadoDoBloco(recolhido: boolean, comErro: boolean): { aberto: boolean; recolhidoDepoisDoToque: boolean } {
  const aberto = !recolhido || comErro;
  return { aberto, recolhidoDepoisDoToque: aberto };
}

export function useBlocoRecolhivel(comecaRecolhido: boolean, comErro: boolean): { aberto: boolean; alternar: () => void } {
  const [recolhido, setRecolhido] = useState(comecaRecolhido);
  const { aberto, recolhidoDepoisDoToque } = estadoDoBloco(recolhido, comErro);
  return { aberto, alternar: () => setRecolhido(recolhidoDepoisDoToque) };
}

/** `oQue` completa o rótulo: "Recolher os planos de aluguel" / "Abrir os planos de aluguel". */
export function SetaDoBloco({ aberto, oQue, controla, aoAlternar }: { aberto: boolean; oQue: string; controla: string; aoAlternar: () => void }) {
  return (
    <IconButton
      quieto
      compacto
      aria-label={`${aberto ? "Recolher" : "Abrir"} ${oQue}`}
      aria-expanded={aberto}
      aria-controls={controla}
      onClick={aoAlternar}
      icone={<Icone de={aberto ? ChevronUp : ChevronDown} />}
    />
  );
}

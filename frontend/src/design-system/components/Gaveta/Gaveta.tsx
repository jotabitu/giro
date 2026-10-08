"use client";

import type { ReactNode } from "react";
import { CaixaModal } from "../Dialogo/modal";

export type LadoDaGaveta = "esquerda" | "direita" | "baixo";

export type GavetaProps = {
  aberto: boolean;
  /** Chamado por Escape, pelo botão Fechar e pelo clique fora. Feche a gaveta aqui. */
  aoFechar: () => void;
  /** Nome da gaveta ("Menu", "Filtros"). */
  titulo: string;
  descricao?: string;
  children?: ReactNode;
  /** Rodapé fixo, normalmente os botões de um filtro ("Limpar", "Ver 12 veículos"). */
  acoes?: ReactNode;
  /** esquerda: menu no celular. baixo: filtros e escolhas no celular. direita: detalhe lateral. */
  lado?: LadoDaGaveta;
  fecharAoClicarFora?: boolean;
};

/** Painel que desliza da borda da tela. É um diálogo modal: foco preso e Escape fecham como no Dialogo. */
export function Gaveta({ lado = "esquerda", ...resto }: GavetaProps) {
  return <CaixaModal classe={`wl-gaveta wl-gaveta--${lado}`} rotuloFechar="Fechar" {...resto} />;
}

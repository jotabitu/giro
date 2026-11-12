"use client";

import type { ReactNode } from "react";
import { CaixaModal } from "./modal";

export type DialogoProps = {
  aberto: boolean;
  /** Chamado por Escape, pelo botão Fechar e pelo clique fora. Feche o diálogo aqui. */
  aoFechar: () => void;
  /** Diz o que a pessoa vai fazer ("Cancelar contrato LOC-2841"). */
  titulo: string;
  /** Uma frase com a consequência. Lida pelo leitor de tela junto com o título. */
  descricao?: string;
  children?: ReactNode;
  /** Botões do rodapé: a ação principal por último e à direita (solido), a de saída ao lado (quieto). */
  acoes?: ReactNode;
  /** `amplo` (até 1100 × 820 px; tela cheia no celular) é para conteúdo que pede espaço, como o visualizador de fotos. */
  tamanho?: "pequeno" | "medio" | "amplo";
  /** Padrão: sim. Desligue em diálogos com formulário preenchido. */
  fecharAoClicarFora?: boolean;
};

/** Janela modal centralizada para confirmar ou preencher algo curto. */
export function Dialogo({ tamanho = "medio", ...resto }: DialogoProps) {
  return <CaixaModal classe={`wl-dialogo wl-dialogo--${tamanho}`} rotuloFechar="Fechar" {...resto} />;
}

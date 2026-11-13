import type { Metadata } from "next";
import { Suspense } from "react";
import { QuadroDeMovimentacoes } from "@/components/movimentacoes/QuadroDeMovimentacoes";

export const metadata: Metadata = { title: "Nova movimentação" };

// Rota antiga (links da ficha do veículo, com ?veiculo= e &transferir=1): abre o quadro com o diálogo já aberto (T-453).
export default function NovaMovimentacaoPagina() {
  return (
    <Suspense>
      <QuadroDeMovimentacoes comNovaAberta />
    </Suspense>
  );
}

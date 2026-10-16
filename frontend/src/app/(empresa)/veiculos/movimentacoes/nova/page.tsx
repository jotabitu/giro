import type { Metadata } from "next";
import { Suspense } from "react";
import { NovaMovimentacao } from "@/components/movimentacoes/NovaMovimentacao";

export const metadata: Metadata = { title: "Nova movimentação" };

export default function NovaMovimentacaoPagina() {
  return (
    <Suspense>
      <NovaMovimentacao />
    </Suspense>
  );
}

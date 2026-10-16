import type { Metadata } from "next";
import { Suspense } from "react";
import { QuadroDeMovimentacoes } from "@/components/movimentacoes/QuadroDeMovimentacoes";

export const metadata: Metadata = { title: "Movimentações" };

export default function Movimentacoes() {
  return (
    <Suspense>
      <QuadroDeMovimentacoes />
    </Suspense>
  );
}

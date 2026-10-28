import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaPendencias } from "@/components/financeiro/ListaPendencias";

export const metadata: Metadata = { title: "Pendências do pagamento" };

export default function PendenciasDoPagamento() {
  return (
    <Suspense>
      <ListaPendencias />
    </Suspense>
  );
}

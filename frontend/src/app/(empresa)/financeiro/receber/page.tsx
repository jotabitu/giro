import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaReceber } from "@/components/financeiro/ListaReceber";

export const metadata: Metadata = { title: "Contas a receber" };

export default function ContasAReceber() {
  return (
    <Suspense>
      <ListaReceber />
    </Suspense>
  );
}

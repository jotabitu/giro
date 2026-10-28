import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaReembolsos } from "@/components/financeiro/ListaReembolsos";

export const metadata: Metadata = { title: "Reembolsos" };

export default function Reembolsos() {
  return (
    <Suspense>
      <ListaReembolsos />
    </Suspense>
  );
}

import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaAprovacoes } from "@/components/aprovacoes/ListaAprovacoes";

export const metadata: Metadata = { title: "Aprovações" };

export default function Aprovacoes() {
  return (
    <Suspense>
      <ListaAprovacoes />
    </Suspense>
  );
}

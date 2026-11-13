import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaDeVendas } from "@/components/vendas/ListaDeVendas";

export const metadata: Metadata = { title: "Vendas" };

export default function Vendas() {
  return (
    <Suspense>
      <ListaDeVendas />
    </Suspense>
  );
}

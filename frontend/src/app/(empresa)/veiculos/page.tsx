import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaVeiculos } from "@/components/frota/ListaVeiculos";

export const metadata: Metadata = { title: "Veículos" };

export default function Veiculos() {
  return (
    <Suspense>
      <ListaVeiculos />
    </Suspense>
  );
}

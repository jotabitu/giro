import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaLocacoes } from "@/components/locacoes/ListaLocacoes";

export const metadata: Metadata = { title: "Locações" };

export default function Locacoes() {
  return (
    <Suspense>
      <ListaLocacoes />
    </Suspense>
  );
}

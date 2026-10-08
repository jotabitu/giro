import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaClientes } from "@/components/clientes/ListaClientes";

export const metadata: Metadata = { title: "Clientes" };

export default function Clientes() {
  return (
    <Suspense>
      <ListaClientes />
    </Suspense>
  );
}

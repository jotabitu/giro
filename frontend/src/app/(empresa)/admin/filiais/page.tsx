import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaFiliais } from "@/components/admin/ListaFiliais";

export const metadata: Metadata = { title: "Filiais" };

export default function Filiais() {
  return (
    <Suspense>
      <ListaFiliais />
    </Suspense>
  );
}

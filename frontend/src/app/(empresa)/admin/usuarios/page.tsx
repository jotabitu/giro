import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaUsuarios } from "@/components/admin/ListaUsuarios";

export const metadata: Metadata = { title: "Usuários" };

export default function Usuarios() {
  return (
    <Suspense>
      <ListaUsuarios />
    </Suspense>
  );
}

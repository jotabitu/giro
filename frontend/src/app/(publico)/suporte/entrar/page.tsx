import type { Metadata } from "next";
import { Suspense } from "react";
import { EntradaDoSuporte } from "@/components/acesso/EntradaDoSuporte";

export const metadata: Metadata = { title: "Modo suporte" };

export default function Pagina() {
  return (
    <Suspense>
      <EntradaDoSuporte />
    </Suspense>
  );
}

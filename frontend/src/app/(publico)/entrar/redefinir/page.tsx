import type { Metadata } from "next";
import { Suspense } from "react";
import { RedefinirSenha } from "@/components/acesso/RedefinirSenha";

export const metadata: Metadata = { title: "Nova senha" };

export default function Pagina() {
  return (
    <Suspense>
      <RedefinirSenha />
    </Suspense>
  );
}

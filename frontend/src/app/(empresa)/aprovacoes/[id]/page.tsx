import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ListaAprovacoes } from "@/components/aprovacoes/ListaAprovacoes";

export const metadata: Metadata = { title: "Aprovações" };

/** Link de um pedido (avisos e início do gerente): a lista com o pedido destacado. */
export default async function Pedido({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return (
    <Suspense>
      <ListaAprovacoes destaqueId={id} />
    </Suspense>
  );
}

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ListaDespesas } from "@/components/financeiro/ListaDespesas";

export const metadata: Metadata = { title: "Despesa" };

/** Link direto de uma despesa (avisos e "Para hoje"): a lista com o detalhe aberto. */
export default async function Despesa({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return (
    <Suspense>
      <ListaDespesas abrirId={id} />
    </Suspense>
  );
}

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { TelaDaVenda } from "@/components/vendas/TelaDaVenda";

export const metadata: Metadata = { title: "Venda" };

/** A venda (VEN-13 a VEN-19): a proposta, a negociação, a espera pelo gerente e a perda. Os avisos de desconto levam aqui. */
export default async function Venda({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return (
    <Suspense>
      <TelaDaVenda id={id} />
    </Suspense>
  );
}

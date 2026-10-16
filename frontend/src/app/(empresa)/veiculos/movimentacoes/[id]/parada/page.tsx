import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ParadaDaMovimentacao } from "@/components/movimentacoes/ParadaDaMovimentacao";

export const metadata: Metadata = { title: "Parada da movimentação" };

export default async function Parada({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <ParadaDaMovimentacao id={id} />;
}

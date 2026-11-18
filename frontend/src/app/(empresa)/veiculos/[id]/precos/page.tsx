import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PrecosDoVeiculo } from "@/components/precos-veiculo/PrecosDoVeiculo";

export const metadata: Metadata = { title: "Planos e preços" };

export default async function PrecosDoVeiculoPagina({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <PrecosDoVeiculo id={id} />;
}

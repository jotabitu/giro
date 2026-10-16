import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EditarVeiculo } from "@/components/frota/EditarVeiculo";

export const metadata: Metadata = { title: "Editar veículo" };

export default async function EditarVeiculoPagina({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <EditarVeiculo id={id} />;
}

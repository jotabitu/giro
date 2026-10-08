import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FichaVeiculo } from "@/components/frota/FichaVeiculo";

export const metadata: Metadata = { title: "Veículo" };

export default async function Veiculo({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <FichaVeiculo id={id} />;
}

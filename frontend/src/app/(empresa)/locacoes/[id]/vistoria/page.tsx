import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { VistoriaDeSaida } from "@/components/vistorias/VistoriaDeSaida";

export const metadata: Metadata = { title: "Vistoria de saída" };

export default async function VistoriaDaLocacao({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <VistoriaDeSaida locacaoId={id} />;
}

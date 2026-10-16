import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { RegistrarChegada } from "@/components/movimentacoes/RegistrarChegada";

export const metadata: Metadata = { title: "Registrar chegada" };

export default async function Chegada({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <RegistrarChegada id={id} />;
}

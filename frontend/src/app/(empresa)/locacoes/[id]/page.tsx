import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DetalheDaLocacao } from "@/components/locacoes/DetalheDaLocacao";

export const metadata: Metadata = { title: "Locação" };

export default async function Locacao({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <DetalheDaLocacao id={id} />;
}

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Devolucao } from "@/components/vistorias/Devolucao";

export const metadata: Metadata = { title: "Devolução" };

export default async function DevolucaoDaLocacao({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <Devolucao locacaoId={id} />;
}

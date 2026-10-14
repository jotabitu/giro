import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FormularioDaFilial } from "@/components/admin/FormularioDaFilial";

export const metadata: Metadata = { title: "Filial" };

export default async function Filial({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <FormularioDaFilial id={id} />;
}

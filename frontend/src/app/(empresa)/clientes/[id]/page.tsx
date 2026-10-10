import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DetalheDoCliente } from "@/components/clientes/DetalheDoCliente";

export const metadata: Metadata = { title: "Cliente" };

export default async function Cliente({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <DetalheDoCliente id={id} />;
}

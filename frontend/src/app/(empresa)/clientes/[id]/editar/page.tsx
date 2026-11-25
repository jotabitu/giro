import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EditarCliente } from "@/components/clientes/EditarCliente";

export const metadata: Metadata = { title: "Editar cliente" };

export default async function EditarClientePagina({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <EditarCliente id={id} />;
}

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CadastroDoCliente } from "@/components/clientes/CadastroDoCliente";

export const metadata: Metadata = { title: "Cadastro do cliente" };

export default async function Cliente({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return <CadastroDoCliente id={id} />;
}

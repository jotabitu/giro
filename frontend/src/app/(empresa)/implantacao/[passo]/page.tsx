import type { Metadata } from "next";
import { PassoDoAssistente } from "@/components/implantacao/PassoDoAssistente";

export const metadata: Metadata = { title: "Configuração inicial" };

export default async function Passo({ params }: { params: Promise<{ passo: string }> }) {
  const { passo } = await params;
  return <PassoDoAssistente passo={passo} />;
}

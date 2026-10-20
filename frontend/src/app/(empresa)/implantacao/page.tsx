import type { Metadata } from "next";
import { InicioDoAssistente } from "@/components/implantacao/InicioDoAssistente";

export const metadata: Metadata = { title: "Configuração inicial" };

export default function Implantacao() {
  return <InicioDoAssistente />;
}

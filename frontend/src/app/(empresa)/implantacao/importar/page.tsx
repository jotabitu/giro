import type { Metadata } from "next";
import { ImportarDados } from "@/components/implantacao/ImportarDados";

export const metadata: Metadata = { title: "Importar dados" };

export default function Importar() {
  return <ImportarDados />;
}

import type { Metadata } from "next";
import { CompraPublica } from "@/components/compra/CompraPublica";

export const metadata: Metadata = { title: "Assine o Giro", referrer: "no-referrer" };

export default function Pagina() {
  return <CompraPublica />;
}

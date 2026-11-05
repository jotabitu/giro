import type { Metadata } from "next";
import { ReciboDevolucao } from "@/components/recibo/ReciboDevolucao";

export const metadata: Metadata = { title: "Recibo da devolução", referrer: "no-referrer", robots: { index: false, follow: false } };

export default function Pagina() {
  return <ReciboDevolucao />;
}

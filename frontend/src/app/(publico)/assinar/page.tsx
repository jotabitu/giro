import type { Metadata } from "next";
import { AssinarContrato } from "@/components/assinar/AssinarContrato";

export const metadata: Metadata = { title: "Assinar contrato", referrer: "no-referrer", robots: { index: false, follow: false } };

export default function Pagina() {
  return <AssinarContrato />;
}

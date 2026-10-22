import type { Metadata } from "next";
import { CancelarAssinatura } from "@/components/admin/CancelarAssinatura";

export const metadata: Metadata = { title: "Cancelar assinatura" };

export default function PaginaCancelarAssinatura() {
  return <CancelarAssinatura />;
}

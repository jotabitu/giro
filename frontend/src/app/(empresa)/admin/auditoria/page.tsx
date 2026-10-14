import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaAuditoria } from "@/components/admin/ListaAuditoria";

export const metadata: Metadata = { title: "Auditoria" };

export default function Auditoria() {
  return (
    <Suspense>
      <ListaAuditoria />
    </Suspense>
  );
}

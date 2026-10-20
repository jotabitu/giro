import type { Metadata } from "next";
import { AdminMarca } from "@/components/admin/AdminMarca";

export const metadata: Metadata = { title: "Empresa e marca" };

export default function PaginaMarca() {
  return <AdminMarca />;
}

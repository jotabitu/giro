import type { Metadata } from "next";
import { AdminRamo } from "@/components/admin/AdminRamo";

export const metadata: Metadata = { title: "O que a empresa faz" };

export default function PaginaRamo() {
  return <AdminRamo />;
}

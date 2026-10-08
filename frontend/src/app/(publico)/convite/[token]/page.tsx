import type { Metadata } from "next";
import { AceitarConvite } from "@/components/acesso/AceitarConvite";

export const metadata: Metadata = { title: "Convite" };

export default function Pagina() {
  return <AceitarConvite />;
}

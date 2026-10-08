import type { Metadata } from "next";
import { MenuMais } from "@/components/casca/MenuMais";

export const metadata: Metadata = { title: "Mais" };

export default function Mais() {
  return <MenuMais />;
}

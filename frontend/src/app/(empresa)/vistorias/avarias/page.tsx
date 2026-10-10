import type { Metadata } from "next";
import { AvariasAbertas } from "@/components/vistorias/AvariasAbertas";

export const metadata: Metadata = { title: "Avarias abertas" };

export default function Avarias() {
  return <AvariasAbertas />;
}

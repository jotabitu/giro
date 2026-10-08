import type { Metadata } from "next";
import { EsqueciSenha } from "@/components/acesso/EsqueciSenha";

export const metadata: Metadata = { title: "Esqueci a senha" };

export default function Pagina() {
  return <EsqueciSenha />;
}

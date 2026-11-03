"use client";

import type { ReactNode } from "react";
import { CascaDoApp } from "@/components/casca/CascaDoApp";
import { FaixaDaAssinatura } from "@/components/casca/FaixaDaAssinatura";
import { FaixaDoSuporte } from "@/components/casca/FaixaDoSuporte";
import { FilialProvider } from "@/lib/filial-escolhida";
import { SessaoProvider } from "@/lib/sessao";

export default function LayoutEmpresa({ children }: { children: ReactNode }) {
  return (
    <SessaoProvider>
      <div className="sticky top-0 z-50">
        <FaixaDoSuporte />
        <FaixaDaAssinatura />
      </div>
      <FilialProvider>
        <CascaDoApp>{children}</CascaDoApp>
      </FilialProvider>
    </SessaoProvider>
  );
}

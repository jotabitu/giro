"use client";

import type { ReactNode } from "react";
import { CascaDoApp } from "@/components/casca/CascaDoApp";
import { FaixaDoSuporte } from "@/components/casca/FaixaDoSuporte";
import { FilialProvider } from "@/lib/filial-escolhida";
import { SessaoProvider } from "@/lib/sessao";

export default function LayoutEmpresa({ children }: { children: ReactNode }) {
  return (
    <SessaoProvider>
      <FaixaDoSuporte />
      <FilialProvider>
        <CascaDoApp>{children}</CascaDoApp>
      </FilialProvider>
    </SessaoProvider>
  );
}

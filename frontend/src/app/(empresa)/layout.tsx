"use client";

import type { ReactNode } from "react";
import { CascaDoApp } from "@/components/casca/CascaDoApp";
import { FilialProvider } from "@/lib/filial-escolhida";
import { SessaoProvider } from "@/lib/sessao";

export default function LayoutEmpresa({ children }: { children: ReactNode }) {
  return (
    <SessaoProvider>
      <FilialProvider>
        <CascaDoApp>{children}</CascaDoApp>
      </FilialProvider>
    </SessaoProvider>
  );
}

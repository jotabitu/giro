"use client";

import type { ReactNode } from "react";
import { CascaDoApp } from "@/components/casca/CascaDoApp";
import { SessaoProvider } from "@/lib/sessao";

export default function LayoutEmpresa({ children }: { children: ReactNode }) {
  return (
    <SessaoProvider>
      <CascaDoApp>{children}</CascaDoApp>
    </SessaoProvider>
  );
}

import type { ReactNode } from "react";
import { Controles } from "./controles";

export const metadata = { title: "Design system" };

export default function LayoutDoDesignSystem({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-6 p-6">
      <Controles />
      {children}
    </div>
  );
}

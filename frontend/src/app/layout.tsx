import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { cssDosTemas } from "@/design-system/tokens";
import "./globals.css";

export const metadata: Metadata = { title: "Giro" };
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" data-theme="light">
      <head>
        {/* CSS gerado só de tokens.ts (conteúdo próprio, sem entrada de usuário). */}
        <style dangerouslySetInnerHTML={{ __html: cssDosTemas() }} />
      </head>
      <body>{children}</body>
    </html>
  );
}

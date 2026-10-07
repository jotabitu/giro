import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { cssDaMarca, ID_ESTILO_MARCA, MARCA_PADRAO } from "@/design-system/marca";
import { cssDosTemas } from "@/design-system/tokens";
import "./globals.css";
import "@/design-system/componentes.css";

export const metadata: Metadata = { title: "Giro" };
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" data-theme="light" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <head>
        {/* CSS gerado só de tokens.ts e marca.ts (conteúdo próprio, cor validada como #rrggbb). */}
        <style dangerouslySetInnerHTML={{ __html: cssDosTemas() }} />
        {/* Marca da empresa: troca em execução por aplicarMarca(). A cor da empresa entra aqui quando a API existir. */}
        <style id={ID_ESTILO_MARCA} dangerouslySetInnerHTML={{ __html: cssDaMarca(MARCA_PADRAO) }} />
      </head>
      <body>{children}</body>
    </html>
  );
}

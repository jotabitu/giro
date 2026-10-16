import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AmbienteDaTela } from "@/components/casca/FaixaDataSimulada";
import { cssDaMarca, ID_ESTILO_MARCA, MARCA_PADRAO } from "@/design-system/marca";
import { cssDosTemas } from "@/design-system/tokens";
import { Provedores } from "@/lib/provedores";
import "./globals.css";

// Renderização por requisição: a CSP usa um nonce novo a cada resposta (src/middleware.ts), e
// página pré-renderizada em build não o recebe nos scripts inline do Next.
export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Giro" };
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" data-theme="light" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <head>
        {/* CSS gerado só de tokens.ts e marca.ts (conteúdo próprio, cor validada como #rrggbb). */}
        <style dangerouslySetInnerHTML={{ __html: cssDosTemas() }} />
        {/* Marca da empresa: troca em execução por aplicarMarca(). As cores da empresa vêm de GET /api/marca/ (lib/marca-empresa.ts). */}
        <style id={ID_ESTILO_MARCA} dangerouslySetInnerHTML={{ __html: cssDaMarca(MARCA_PADRAO) }} />
      </head>
      <body>
        <AmbienteDaTela />
        <Provedores>{children}</Provedores>
      </body>
    </html>
  );
}

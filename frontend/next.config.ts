import type { NextConfig } from "next";

// Frontend e API na mesma origem (ADR 0013): o navegador chama /api/ no host do próprio
// frontend e o Next repassa ao Django. O Host original segue em X-Forwarded-Host, que o Django
// usa para achar a empresa (USE_X_FORWARDED_HOST). Em produção o proxy reverso faz o mesmo
// antes de chegar aqui; este rewrite vale para dev e como reserva.
// O destino é lido no build (output standalone): defina API_URL_INTERNA ao construir a imagem.
const apiInterna = process.env.API_URL_INTERNA ?? "http://backend:8000";

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // A API do Django termina em barra; sem isto o Next redireciona /api/x/ para /api/x em laço.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    // A versão com barra vem primeiro: o padrão :path* perde a barra final e o Django redirecionaria.
    return [
      { source: "/api/:path*/", destination: `${apiInterna}/api/:path*/` },
      { source: "/api/:path*", destination: `${apiInterna}/api/:path*` },
    ];
  },
};

export default config;

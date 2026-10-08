import type { NextConfig } from "next";

// Frontend e API na mesma origem (ADR 0013): o navegador chama /api/ no host do próprio
// frontend e o Next repassa ao Django. O Host original segue em X-Forwarded-Host, que o Django
// usa para achar a empresa (USE_X_FORWARDED_HOST). Só para desenvolvimento: em homologação e
// produção o proxy reverso manda /api/ direto ao Django, sem passar pelo Next (ADR 0018).
// O destino é lido no build (output standalone): defina API_URL_INTERNA ao construir a imagem.
const apiInterna = process.env.API_URL_INTERNA ?? "http://backend:8000";

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // A API do Django termina em barra; sem isto o Next redireciona /api/x/ para /api/x em laço.
  skipTrailingSlashRedirect: true,
  // Cabeçalhos fixos de segurança (S-18). A CSP, que depende de nonce, sai de src/middleware.ts.
  // HSTS só vale sobre HTTPS; o Django cobre /api/ e o proxy reverso pode repeti-lo.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
          },
        ],
      },
    ];
  },
  async rewrites() {
    // A versão com barra vem primeiro: o padrão :path* perde a barra final e o Django redirecionaria.
    return [
      { source: "/api/:path*/", destination: `${apiInterna}/api/:path*/` },
      { source: "/api/:path*", destination: `${apiInterna}/api/:path*` },
    ];
  },
};

export default config;

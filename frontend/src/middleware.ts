import { NextResponse, type NextRequest } from "next/server";
import { montarCsp, novoNonce } from "@/lib/csp";
import { mostraLanding } from "@/lib/host-landing";

const DEV = process.env.NODE_ENV !== "production";

export function middleware(req: NextRequest) {
  const headers = new Headers(req.headers);

  // /api/ (só em dev: em homologação e produção o proxy reverso manda /api/ direto ao Django).
  // Proxy de mesma origem (ADR 0013, 0018 item 4): o X-Forwarded-For que o cliente mandou não
  // pode chegar ao Django, que conta os proxies confiáveis da direita para achar o IP do ator.
  if (req.nextUrl.pathname.startsWith("/api/")) {
    headers.delete("x-forwarded-for");
    return NextResponse.next({ request: { headers } });
  }

  // "/" (T-489): landing pública só no domínio da plataforma; no subdomínio da empresa, /entrar.
  const host = req.headers.get("host");
  if (req.nextUrl.pathname === "/" && !mostraLanding(host)) {
    // Mesmo host que o navegador pediu (req.url pode trazer o endereço interno do Next). O proxy
    // sobrescreve Host e X-Forwarded-Proto (infra/proxy/snippets/giro-locais.conf.template).
    const protocolo = req.headers.get("x-forwarded-proto") ?? req.nextUrl.protocol.replace(":", "");
    return NextResponse.redirect(new URL("/entrar", `${protocolo}://${host ?? req.nextUrl.host}`));
  }

  // Páginas: CSP com nonce na requisição (o Next lê daqui para marcar os próprios scripts)
  // e na resposta (o navegador aplica).
  const csp = montarCsp(novoNonce(), DEV, process.env.GIRO_ARQUIVOS_ORIGEM);
  headers.set("content-security-policy", csp);
  const resposta = NextResponse.next({ request: { headers } });
  resposta.headers.set("content-security-policy", csp);
  return resposta;
}

export const config = {
  // Tudo, menos os estáticos do Next e prefetch.
  matcher: [
    {
      source: "/((?!_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};

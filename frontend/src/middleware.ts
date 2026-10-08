import { NextResponse, type NextRequest } from "next/server";
import { montarCsp, novoNonce } from "@/lib/csp";

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

  // Páginas: CSP com nonce na requisição (o Next lê daqui para marcar os próprios scripts)
  // e na resposta (o navegador aplica).
  const csp = montarCsp(novoNonce(), DEV);
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

import { NextResponse, type NextRequest } from "next/server";

// Proxy de mesma origem (ADR 0013, 0018 item 4): o X-Forwarded-For que o cliente mandou não
// pode chegar ao Django, que conta os proxies confiáveis da direita para achar o IP do ator.
// Só roda em dev: em homologação e produção /api/ não passa pelo Next, e este middleware
// apagaria o IP que o proxy reverso acrescentou.
export function middleware(req: NextRequest) {
  const headers = new Headers(req.headers);
  headers.delete("x-forwarded-for");
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: "/api/:path*" };

// Content-Security-Policy da aplicação (T-035, S-18). Montada por requisição com um nonce, que o
// Next aplica aos próprios scripts (strict-dynamic dispensa listar origens). Sem 'unsafe-inline'
// em script. Estilo inline continua permitido: o layout injeta o CSS dos temas e da marca, e o
// React usa style="". Em dev o React precisa de eval para a pilha de depuração.
export function montarCsp(nonce: string, dev: boolean): string {
  const diretivas = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ];
  if (!dev) diretivas.push("upgrade-insecure-requests");
  return diretivas.join("; ");
}

export function novoNonce(): string {
  return btoa(crypto.randomUUID());
}

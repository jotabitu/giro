// Content-Security-Policy da aplicação (T-035, S-18). Montada por requisição com um nonce, que o
// Next aplica aos próprios scripts (strict-dynamic dispensa listar origens). Sem 'unsafe-inline'
// em script. Estilo inline continua permitido: o layout injeta o CSS dos temas e da marca, e o
// React usa style="". Em dev o React precisa de eval para a pilha de depuração.
//
// `arquivosOrigem` (T-479): origens do armazenamento de arquivos (URLs assinadas do S3/R2), lidas em
// execução de GIRO_ARQUIVOS_ORIGEM, separadas por espaço. Entram só em img-src: nenhuma tela embute
// PDF em iframe/embed, então object-src continua 'none'. Valor inválido é ignorado.
const ORIGEM_HTTPS = /^https:\/\/[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+(:\d{1,5})?$/;

export function origensDeArquivos(valor: string | undefined): string[] {
  if (!valor) return [];
  return valor
    .split(/\s+/)
    .map((origem) => origem.trim().toLowerCase().replace(/\/$/, ""))
    .filter((origem) => ORIGEM_HTTPS.test(origem));
}

export function montarCsp(nonce: string, dev: boolean, arquivosOrigem?: string): string {
  const arquivos = origensDeArquivos(arquivosOrigem);
  const diretivas = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' data: blob:${arquivos.map((o) => ` ${o}`).join("")}`,
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

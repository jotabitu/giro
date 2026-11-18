// Destinos da landing (T-489). As pendências ficam marcadas com TODO(landing) e listadas no PR.

// TODO(landing): número do WhatsApp da equipe Giro (hoje https://wa.me/ sem número).
export const LINK_WHATSAPP = "https://wa.me/";

// TODO(landing): confirmar o destino de "Começar teste grátis". Hoje vai para a compra pública
// (/compra), a rota de assinatura que já existe em (publico).
export const LINK_TESTE_GRATIS = "/compra";

// TODO(landing): páginas de Termos de uso e Privacidade (hoje apontam para as perguntas).
export const LINK_TERMOS = "#perguntas";
export const LINK_PRIVACIDADE = "#perguntas";

/** Botão do cartão de um plano (T-490): vai direto à criação da conta com o plano escolhido. A compra confere o
 * código no catálogo da API e, se ele não estiver à venda, mostra a escolha dos planos. Sem código (o Completo,
 * que não está à venda), vai para a escolha. */
export function linkDoPlano(codigo: string | null): string {
  return codigo ? `${LINK_TESTE_GRATIS}?plano=${encodeURIComponent(codigo)}` : LINK_TESTE_GRATIS;
}

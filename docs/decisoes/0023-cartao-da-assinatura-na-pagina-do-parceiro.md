# Cartão da assinatura só na página do parceiro

**Status:** aceita · 14 out 2026 · detalha a 0007 para a cobrança da assinatura (T-183)

## Contexto

A tela `Admin-Assinatura` oferece cartão de crédito com "cobrança automática todo mês", e a `Compra-Checkout` desenha os campos do cartão (número, validade, código) dentro da página do Giro. O parceiro (Asaas, ADR 0007) aceita cartão de dois jeitos:

1. **Página do parceiro**: o Giro cria a cobrança e recebe um link; a pessoa digita o cartão na página do parceiro, e o parceiro guarda o cartão para as próximas cobranças (o Giro recebe só um token, a bandeira e os 4 últimos dígitos).
2. **Tokenização pela API**: o Giro recebe o número, a validade e o código e os repassa ao parceiro, que devolve o token.

No jeito 2 o número do cartão passa pelo nosso frontend, proxy, backend, logs e Sentry. Isso põe o Giro inteiro no escopo do PCI DSS (questionário completo, varredura trimestral, revisão de log), um custo que não cabe no MVP e que é caro de desfazer depois que o dado entra.

## Decisão

1. **O número do cartão nunca passa pelo Giro.** Nenhuma rota recebe número, validade ou código de segurança, e nenhum formulário do Giro os pede. O cartão é digitado só na página do parceiro, aberta pelo link que a API devolve (`url_pagina`, `docs/api/assinatura.md`).
2. O Giro guarda só o que o parceiro devolve depois do pagamento: token do cartão (cifrado, `CampoCifrado` com a chave dos segredos, ADR 0014, decifrado só em `integracoes/pagamentos/`), bandeira e 4 últimos dígitos. O token nunca sai na API, na auditoria nem no log.
3. As faturas seguintes são cobradas pelo backend com o token (`cobrar_cartao_salvo`, novo na interface de pagamentos). Trocar de forma ou de cartão apaga o token.
4. A interface de pagamentos (`financeiro.md`, "Interface de pagamentos") ganha, para a conta principal: `criar_ou_atualizar_pagador` (empresa como cliente da conta principal), `cobrar_cartao_salvo(conta, token, pedido)` e, em `SituacaoCobranca`, `cartao` (token, bandeira e final) quando o pagamento foi no cartão. O `tipo = cartao_link` de `PedidoCobranca` já existe e é o que abre a página. O backend confirma no sandbox como o parceiro devolve o token depois do pagamento na página; se ele não devolver, a cobrança automática do cartão passa a ser a assinatura recorrente do próprio parceiro, e esta ADR ganha uma nota.
5. Os campos de cartão da `Compra-Checkout` saem da tela (design-system): no checkout fica só a escolha da forma, como na `Admin-Assinatura`.

## Consequências

- O Giro fica no questionário mais simples do PCI (SAQ A), porque o cartão só existe na página do parceiro.
- A pessoa sai da tela do Giro para digitar o cartão e volta pelo link de retorno. A página do parceiro mostra a marca do parceiro; para a assinatura do Giro (cobrança do Giro à locadora) isso não fere o white label.
- Cadastrar o cartão sem cobrar nada, no teste, depende de o parceiro aceitar pré-autorização pela página; a regra de quando o cartão é pedido fica com o produto (`[D-6]` em `docs/api/assinatura.md`). Resolvido em 14 out 2026 (T-190, `PLT-13`): o cartão é digitado na página do parceiro ao pagar a 1ª fatura, sem pré-autorização.
- Vale também, no futuro, para o cartão do cliente final da locadora (subconta): mesmo princípio, mesma interface.

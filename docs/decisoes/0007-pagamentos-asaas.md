# Pagamentos pelo Asaas, com subconta por locadora

**Status:** aceita · 07 out 2026

## Contexto

O Giro cobra dois tipos de cliente: as locadoras (assinatura do Giro) e os clientes finais de cada locadora (parcelas de locação e venda, por Pix, boleto e cartão). As mensagens de cobrança precisam sair com a marca da locadora (white label), e o dinheiro precisa cair na conta de cada locadora, não na do Giro.

## Decisão

Usar o Asaas. Cada empresa ganha uma subconta white label criada pela API (`POST /v3/accounts`), com chave própria; cobranças, assinaturas recorrentes, Pix Automático e webhooks são feitos na subconta. A assinatura do Giro é cobrada pela conta principal. O backend fala com o parceiro só pela interface de `backend/integracoes/pagamentos/`, com uma implementação falsa para desenvolvimento e testes. Efí Bank é o plano B, atrás da mesma interface.

## Consequências

Cada locadora precisa passar pelo cadastro da subconta (dados da empresa e conta bancária) no passo "Recebimentos" da implantação. Taxas por cobrança recebida (Pix R$ 1,99 após os 3 primeiros meses) ficam com a locadora. Trocar de parceiro exige só uma nova implementação da interface.

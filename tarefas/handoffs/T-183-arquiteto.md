# T-183 · Contrato da Assinatura completa · arquiteto → orquestrador, produto, backend, frontend, design-system, seguranca

**O que foi feito:** o contrato do que faltava na tela `Admin-Assinatura`, que entra inteira no MVP (decisão do dono em 14 out 2026). Parte da `[decisão]` da T-170 (branch `t-170-assinatura`) e da T-029 (PR #194).
- `GET /api/assinatura/` ganha `teste.inicio`, `proxima_fatura` e `plano_proximo` para todos. Para o administrador, ganha também `forma_pagamento`, `dados_fiscais`, `oferta` (o cartão do plano Completo, montado com os recursos reais do plano acima) e `acoes`. Para os outros perfis, esses blocos vêm ausentes.
- A 1ª fatura vence no **dia seguinte** ao fim do teste (`PLT-01`): Moto Rápida em **22 out**, R$ 449,00. A referência diz 21 out e está errada; vale a regra.
- Comparar e mudar de plano (`PLT-04`): `GET planos/` com `cabe` e `excede`; `POST mudanca-plano/simular/`, `POST mudanca-plano/` (confirma com o valor simulado) e `DELETE mudanca-plano/` (desfaz o downgrade agendado). O downgrade que não cabe recebe 422 `PLT-04` (Moto Rápida → Essencial: 86 de 30 veículos, 5 de 3 usuários). Há um serviço só, `mudar_plano`, usado também pela ação da plataforma.
- Forma de pagamento: `PUT forma-pagamento/` com cartão, Pix automático ou boleto. O cartão é digitado só na página do parceiro (ADR 0023, nova). O Pix automático devolve o copia e cola da autorização.
- Faturas: lista com a linha do teste, `situacao` pronta, detalhe com a cobrança e o comprovante, e `pagar/`. A baixa vem sempre do webhook, que consulta o parceiro antes.
- Dados fiscais: `PATCH dados-fiscais/` muda a razão social e o `email_cobranca` (campo novo). O CNPJ não muda por aqui.
- Permissões e estado:
  - escrita só do administrador; o token de suporte recebe 403 `PLT-07`;
  - a empresa `suspensa` continua podendo pagar, escolher a forma e corrigir os dados fiscais. É uma exceção explícita ao `somente_leitura`, porque pagar faz a empresa voltar a `ativa` na hora.
- Sem rota (seção "Faturas, cobrança e régua"): a conta principal no parceiro, a geração das faturas, a emissão antes do vencimento, a régua `AUT-13` e as transições da empresa.

**Onde:**
- `docs/api/assinatura.md` (novo);
- `docs/decisoes/0023-cartao-da-assinatura-na-pagina-do-parceiro.md` (nova) e `docs/decisoes/README.md`;
- `docs/decisoes/modelo-de-dados.md`:
  - `Empresa.email_cobranca`;
  - em `FaturaAssinatura`: `tipo`, `periodo_inicio`, `periodo_fim`, `plano`, `cobranca_emitida_em` e `cartao_recusado_em`, e a restrição única só para `mensalidade`;
  - `FormaPagamentoAssinatura` no apoio do `public`;
- `docs/api/plataforma.md` (aponta para o contrato novo, com o serviço único `mudar_plano`);
- `docs/api/financeiro.md` (a interface de pagamentos para a conta principal);
- `tarefas/backlog.md` (seção T-183 e `[decisão]`) e `tarefas/feito.md`.

**Contrato:** `docs/api/assinatura.md`. O OpenAPI não muda nesta tarefa.

**Regras cobertas:** PLT-01, PLT-02, PLT-03, PLT-04, PLT-05, AUT-13 e a tabela de estados da empresa. A `PLT-06` (cancelar e pausar) ficou de fora, com o produto.

**O que ficou de fora:**
- **10 pontos sem regra**, marcados `[D-1]` a `[D-10]` no contrato, cada um com recomendação. O contrato segue a recomendação, e a resposta muda só o trecho marcado. Os principais:
  - quando o teste vira `ativa` e a suspensão no fim do teste;
  - o dia e o período das faturas;
  - a conta da diferença proporcional;
  - o cartão sem cobrança no teste;
  - a antecedência do boleto (a tela diz 5 dias e a régua começa no D-3);
  - a NFS-e da assinatura e a troca de CNPJ;
  - o cartão do Completo, que cita NF-e (contra a `FIL-04`) e portal do cliente (que não existe).
- `Plat-Cobranca` (a tela da plataforma) continua na fase 2.

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar as 6 propostas da seção T-183 do backlog: 3 de backend (faturas e conta principal; rotas; régua e estados), 1 de frontend, 1 de design-system e 1 de segurança. Abrir o PR.
- **Produto:** analisar `[D-1]` a `[D-10]` com o dono, junto da análise das PLT que já está em andamento. As que mudarem regra entram em `docs/regras-de-negocio.md`. A `[D-1]` e a `[D-6]` travam a régua; as outras só ajustam trechos.
- **Backend:** pode começar pelas faturas e pela conta principal, que não dependem das decisões. No sandbox, confirmar como o parceiro devolve o token do cartão depois do pagamento na página dele (ADR 0023, item 4).
- **Design-system:** "a partir de 22 out" na `Admin-Assinatura`, e tirar os campos de cartão da `Compra-Checkout` (ADR 0023).
- **Segurança:** revisar a ADR 0023, a exceção da `suspensa` e o webhook da conta principal.

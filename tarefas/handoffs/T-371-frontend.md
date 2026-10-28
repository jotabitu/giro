# Handoff · T-371 · Reembolsos e pendências do pagamento (frontend)

- **Agente:** frontend
- **Branch:** `t-371-reembolsos-pendencias`, a partir da `origin/main` com o #438 (T-380) e o #436 (T-372).
- **Contrato:** `docs/api/financeiro.md` ("Tela `Reembolsos`" e "Tela `Pendências do pagamento`", T-358 e T-380)
- **Telas de referência:** `docs/telas/html/Reembolsos-Desktop|Mobile.dc.html` e `Pendencias-Pagamento-Desktop|Mobile.dc.html`
- **Regras:** DEV-02, AUT-05, FIN-03, PLT-07, PLT-12

## O que foi entregue

- **`/financeiro/reembolsos`** (`ListaReembolsos`): indicadores `a_fazer` e `feitos` com o texto da API, abas A fazer, Feitos e Todos com as `contagens`, período Hoje, Semana e Mês (só no desktop, como a referência), busca por cliente ou locação e paginação por cursor. Tabela no desktop e cartões no celular. A situação mostra `status_rotulo` mais a data do `feito_em`. "Marcar como feito" só com `acoes.marcar_feito`; "Ver acerto" leva a `/locacoes/{origem.id}`; "Comprovante" só com `comprovante` (a API manda `null` ao suporte).
- **`DialogoMarcarFeito`:** comprovante opcional (imagem ou PDF, até 10 MB, como nas despesas), multipart em `POST reembolsos/{id}/feito/`. Ao concluir, invalida `reembolsos` e `inicio` (o "Para hoje" perde o item).
- **`/financeiro/pendencias-pagamento`** (`ListaPendencias`): indicadores `abertas` e `resolvidas`, abas Abertas, Resolvidas e Todas, busca, tabela e cartões. `motivo_rotulo`, `detalhe` (valor do dia e diferença) e `resolucao.texto` vêm da API; a tela não faz conta. 403 `PLT-12` (plano Essencial) mostra a mensagem da API e esconde a lista.
- **`DialogoResolverPendencia`:** "Baixar a conta" só quando `acoes.baixar`; "Ignorar o aviso" sempre; motivo obrigatório, com o erro do campo vindo da API (400). Invalida `pendencias-pagamento` e `contas-receber`.
- **Menu (`lib/menu.ts`):** as chaves `reembolsos` e `pendencias_pagamento` entram em `DESTINOS`, então o menu da API (`eu.navegacao`) e `rotaPermitida` passam a conhecer as duas rotas. O Essencial não recebe o item e a rota fica bloqueada. `hrefDoDestino` ignora o `id` dos dois destinos (não há página de detalhe): o "Para hoje" com `{ chave: "reembolsos", id: 31 }` abre a lista, que já abre em "A fazer".
- **Cliente e tipos:** `listarReembolsos`, `marcarReembolsoFeito`, `listarPendencias` e `resolverPendencia` em `lib/api/financeiro.ts`; tipos a partir do OpenAPI em `tipos-financeiro.ts`. `npm run api:gerar` não mudou o contrato.
- **Fixtures:** `falso-reembolsos.ts` (seed de 07 out: Juliana R$ 183,00 a fazer; Carlos R$ 299,40 e Roberto R$ 329,00 abertas; `planoDoFalso.essencial` para o 403).

## Fora da tela, como o contrato manda

"Exportar", "Prazo médio de acerto", o "Total do período", a chave Pix do cliente e o selo "Integração Asaas · Online" não vêm no MVP (`financeiro.md`), então não aparecem.

## Pontos para o orquestrador

- Nenhuma dependência nova. Nenhuma pergunta de regra aberta.
- O mesmo `Resolvidas no mês` das pendências vem de `periodo=mes` fixo; a tela não tem seletor de período nelas, como a referência.
- A tela não foi vista no navegador a 1440px e 390px (ambiente sem a API de pé); vale uma passada visual do design-system e do QA.

## Verificação

- `npx tsc --noEmit` e `npm run lint`: limpos. `npx vitest run`: 89 arquivos, 813 testes passando.
- Testes novos em `ReembolsosEPendencias.test.tsx` (14): `dev_02_a_fazer`, `dev_02_todos`, `plt_07_suporte` (reembolso e pendência sem ações), vazio, marcar como feito com comprovante e 409 `transicao_reembolso`, diálogo, `aut_05_abertas`, `aut_05_resolvidas`, `aut_05_dialogo_baixar`, `aut_05_resolver` (400, 409 `transicao_pendencia` e `transicao_conta`), `plt_12_essencial` (403 e rota bloqueada) e o menu.
- Os testes rodam em `node`, sem DOM: o clique nos botões está coberto pelas chamadas do cliente e pelas fixtures, não por clique.

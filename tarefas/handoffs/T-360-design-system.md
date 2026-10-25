# T-360 · Telas de referência que faltam na fase 1 · design-system → frontend, arquiteto, orquestrador

**O que foi feito:**
Desenhei em `docs/telas/html/`, nas versões desktop e celular, as telas de referência que faltavam na fase 1 do MVP, utilizando os tokens e componentes do design system white label e dados do seed Moto Rápida em 07 out 2026:
1. **Reembolsos (`Reembolsos-Desktop.dc.html` e `Reembolsos-Mobile.dc.html`):**
   - Lista de cauções e devoluções a reembolsar ao cliente (`DEV-02`, `LOC-12`, `LOC-13`).
   - Destino direto do item `para_hoje` do painel do financeiro e do gerente de filial (`/financeiro/reembolsos`).
   - Filtros por situação (`A fazer`, `Feitos`, `Todos`), KPIs do período e busca.
   - Caso de teste do seed: Juliana Rocha (locação `LOC-2836`, devolução da Honda CG 160 Fan `QXA-4B21`, caução de R$ 600,00 abatendo diárias/acerto, com saldo líquido a devolver de R$ 183,00 via Pix celular `85998765432`).
   - Ação "Marcar como feito" que aciona `POST /api/financeiro/reembolsos/{id}/feito/` com upload opcional de comprovante.
2. **Pendências do pagamento (`Pendencias-Pagamento-Desktop.dc.html` e `Pendencias-Pagamento-Mobile.dc.html`):**
   - Avisos de webhooks do parceiro de pagamento Asaas com divergência de valor ou cobrança não encontrada/cancelada (`AUT-05`, `FIN-04`, `S-14`).
   - Indicadores de pendências e valor sob análise, filtros (`Abertas`, `Resolvidas`, `Todas`) e busca por ID do parceiro ou pagador.
   - Casos de teste: divergência de valor em Carlos Menezes (`LOC-2841`, pago R$ 299,40 via Pix com juros/multa do dia não calculados de R$ 306,09) e pagamento recebido após cancelamento de proposta.
   - Ação "Resolver" que aciona `POST /api/financeiro/pendencias-pagamento/{id}/resolver/` (`baixar` ou `ignorar`, com justificativa obrigatória).
3. **Controle do suporte (`Admin-Suporte-Desktop.dc.html` e `Admin-Suporte-Mobile.dc.html`) e cartão em Configurações:**
   - Tela da administração em que o administrador visualiza os acessos do suporte Giro nos últimos 90 dias, bloqueia ou libera o suporte e revoga acessos ativos imediatamente (`PLT-07`).
   - Cartão do interruptor principal com status de acesso e botão de bloqueio (`POST /api/suporte/bloquear/` e `POST /api/suporte/liberar/`).
   - Cartões com os pilares de segurança e privacidade do suporte (`AUD-09`: nunca recebe CPF/CNH completos; aviso imediato por e-mail; faixa amarela visível; expiração por tempo).
   - Tabela de acessos com o caso ativo do seed: técnico Diego Santos, Chamado #1042, permissão "Só ver", término às 15:30 e botão "Revogar acesso" (`POST /api/suporte/acessos/{id}/revogar/`).
   - Cartão "Controle do suporte" adicionado ao catálogo de cartões em `Config-Desktop.dc.html` e `Config-Mobile.dc.html`.
4. **Faixa do modo suporte (`Modo-Suporte-Desktop.dc.html` e `Modo-Suporte-Mobile.dc.html`):**
   - Especificação e visualização da faixa fixa amarela no topo de todas as páginas da empresa enquanto `eu.suporte !== null`.
   - Exibe crachá do modo suporte ativo, operador ("Diego Santos"), empresa ("Moto Rápida"), número do chamado ("#1042"), nível de permissão ("Só ver"), horário de expiração ("15:30") e o botão de ação "Sair do suporte" (`POST /api/auth/suporte/sair/`).
   - Painel explicativo com o comportamento no frontend para permissão de leitura (403 `PLT-07` em ações de escrita) e expiração de sessão (401 `PLT-07`).
5. **Atualização do índice `docs/telas/README.md`:**
   - Adicionadas as novas linhas em Contas a receber / Financeiro, Administração e nas tabelas de rotas do menu e cartões de Configurações.
   - Atualizadas as linhas de Movimentações de veículos: removidas as marcas "(fase 2)" e rotas "(proposta)", confirmando sua inclusão no MVP desde 16 out.
   - As telas de Veículos não foram alteradas, em estrito cumprimento às instruções.

**Onde:**
- `docs/telas/html/Reembolsos-Desktop.dc.html`
- `docs/telas/html/Reembolsos-Mobile.dc.html`
- `docs/telas/html/Pendencias-Pagamento-Desktop.dc.html`
- `docs/telas/html/Pendencias-Pagamento-Mobile.dc.html`
- `docs/telas/html/Admin-Suporte-Desktop.dc.html`
- `docs/telas/html/Admin-Suporte-Mobile.dc.html`
- `docs/telas/html/Modo-Suporte-Desktop.dc.html`
- `docs/telas/html/Modo-Suporte-Mobile.dc.html`
- `docs/telas/html/Config-Desktop.dc.html`
- `docs/telas/html/Config-Mobile.dc.html`
- `docs/telas/README.md`
- `tarefas/feito.md`

**Contratos:**
- `docs/api/financeiro.md` (seções "Devoluções ao cliente", "Webhooks" e "Pendências de pagamento")
- `docs/api/contas.md` (seções "Modo suporte", "Controle do administrador" e "Rotas dos cartões de Configurações")
- `tarefas/handoffs/T-354-arquiteto.md` (seção 2 e item 3.3)

**Regras cobertas:**
- `DEV-02` (devoluções de caução e acerto da devolução)
- `LOC-12`, `LOC-13` (reembolsos por cancelamento e créditos)
- `FIN-04`, `AUT-05`, `S-14` (baixas de pagamento, webhooks e retenção de pagamentos com divergência para proteção do caixa)
- `PLT-07`, `AUD-09` (modo suporte Giro, controle de bloqueio pelo administrador, revogação, auditoria e preservação de dados pessoais)

**O que ficou de fora:**
- Implementação dos componentes e páginas no código Next.js (`frontend/src/app`), a ser feita pelo time de frontend.
- Nenhum arquivo de Veículos foi alterado.

**Próximo passo para quem recebe:**
- Orquestrador: conferência da entrega e abertura do Pull Request.
- Frontend: implementação das rotas `/financeiro/reembolsos`, `/financeiro/pendencias-pagamento`, `/admin/suporte` e do componente fixo de faixa do modo suporte na casca da aplicação.

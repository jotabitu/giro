# T-381 · Ajustes das telas pelos contratos da T-358 · design-system → arquiteto, frontend, orquestrador

**O que foi feito:**
Ajustei todas as telas de referência que divergiam dos contratos da fase 1 apontados pelo Arquiteto em `tarefas/handoffs/T-358-arquiteto.md`:

1. **`Onboarding-Recebimentos` (`Onboarding-Recebimentos-Desktop.dc.html` e `Onboarding-Recebimentos-Mobile.dc.html`):**
   - **Removidos:** campos bancários (Banco, Agência, Conta corrente, Chave Pix - S-05); interruptores de forma de cobrança (Pix automático, boleto, cartão recorrente - definidos no plano/billing e não por empresa); checkboxes de lembretes de WhatsApp (`AUT-03` possui régua fixa).
   - **Adicionados:** campos completos do formulário de subconta para `POST /api/recebimentos/`:
     - Razão social / Nome (`nome`: "Moto Rápida Locadora LTDA")
     - CNPJ (`documento`: "12.345.678/0001-95")
     - Tipo de empresa (`tipo_empresa`: `LIMITED`, `MEI`, `INDIVIDUAL`, `ASSOCIATION`)
     - Faturamento mensal estimado (`faturamento_mensal_centavos`: R$ 50.000,00)
     - Contato para recebimentos: E-mail (`email`) e Celular com DDD (`celular`)
     - Endereço da sede / matriz: CEP (`cep`), Logradouro (`logradouro`), Número (`numero`), Complemento (`complemento`), Bairro (`bairro`)
   - **Aviso:** card explicativo informando que os dados são submetidos para o parceiro Asaas, ficando com status `pendente` ("Em análise pelo parceiro") e que o passo de implantação só é concluído quando a subconta for aprovada (`IMP-07`).

2. **`Reembolsos` (`Reembolsos-Desktop.dc.html` e `Reembolsos-Mobile.dc.html`):**
   - **Removidos:** botão "Exportar" (exportações no MVP são restritas à auditoria e despesas); KPIs "Total do período" e "Prazo médio de acerto / meta" (não previstos em regra de negócio); chave Pix do cliente na tabela e cards (o modelo `Reembolso` não armazena chave Pix do cliente).
   - **Indicadores ajustados:** apenas os 2 KPIs contratuais:
     - `A reembolsar`: `R$ 183,00` (1 cliente com devolução)
     - `Reembolsados no mês`: `R$ 1.100,00` (3 reembolsos feitos)
   - **Busca:** placeholder atualizado para "Buscar por cliente ou locação" (`?busca=` aceita nome do cliente ou código da origem).
   - **Rótulos:** formas de pagamento padronizadas como `Pix`, `Estorno no cartão` e `Dinheiro`.

3. **`Pendências do pagamento` (`Pendencias-Pagamento-Desktop.dc.html` e `Pendencias-Pagamento-Mobile.dc.html`):**
   - **Removidos:** botão "Exportar"; selo / KPI "Integração Asaas · Online" (a API não afere a saúde do parceiro em tempo real na tela).
   - **Navegação e menu:** corrigido o rótulo do menu e cabeçalhos para "Pendências do pagamento" (substituindo a abreviação "Pendências de pgto").
   - **Indicadores ajustados:**
     - `Pendências abertas`: `2` (R$ 628,40 em análise)
     - `Resolvidas no mês`: `3` (3 resolvidas no mês / R$ 1.847,00)
   - **Motivos e detalhes alinhados ao contrato:**
     - Carlos: motivo `Valor pago diferente`, detalhe `Pagou R$ 299,40; a conta estava em R$ 306,09 (falta R$ 6,69).`, status `Aberta`.
     - Roberto: motivo `A conta já não estava aberta`, detalhe `A conta já não estava aberta (proposta cancelada antes da retirada).`, status `Aberta`.
     - Rafael: motivo `Estornada no parceiro`, detalhe `Operação cancelada a pedido do titular no parceiro.`, status `Resolvida · 05 out`.

4. **`Admin-Suporte` (`Admin-Suporte-Desktop.dc.html` e `Admin-Suporte-Mobile.dc.html`):**
   - **Removidos:** e-mails dos operadores da equipe Giro (`diego.santos@giro.example`, `camila.rocha@giro.example`) da tabela e cards (o e-mail do técnico Giro não é dado da locadora e o nome basta).
   - **Texto da auditoria corrigido:** alterado "Cada clique, tela vista ou alteração" para "Cada alteração" (`AUD-01` audita alterações e ações, não visualizações de tela).
   - **Expiração:** alinhada com `fim_rotulo` ("Expira às 15:30"), sem contagem regressiva ("restam 42 min").

5. **`Modo-Suporte` (`Modo-Suporte-Desktop.dc.html` e `Modo-Suporte-Mobile.dc.html`):**
   - **Removido:** texto de contagem regressiva "(restam 42 min)" / "(42 min)". A faixa exibe exatamente `fim_rotulo`: "Expira às 15:30", delegando a finalização ao status 401 `PLT-07`.
   - **Rótulos padronizados:** "Modo suporte", operador Diego Santos, "Equipe Giro", motivo Chamado #1042, `permissao_rotulo` ("Só ver"), `fim_rotulo` ("Expira às 15:30") e botão "Sair do suporte".

6. **Índice `docs/telas/README.md`:**
   - Adicionadas as rotas do menu `reembolsos` (`/financeiro/reembolsos`) e `pendencias_pagamento` (`/financeiro/pendencias-pagamento`).
   - Telas de Veículos mantidas intocadas.

**Onde:**
- `docs/telas/html/Onboarding-Recebimentos-Desktop.dc.html`
- `docs/telas/html/Onboarding-Recebimentos-Mobile.dc.html`
- `docs/telas/html/Reembolsos-Desktop.dc.html`
- `docs/telas/html/Reembolsos-Mobile.dc.html`
- `docs/telas/html/Pendencias-Pagamento-Desktop.dc.html`
- `docs/telas/html/Pendencias-Pagamento-Mobile.dc.html`
- `docs/telas/html/Admin-Suporte-Desktop.dc.html`
- `docs/telas/html/Admin-Suporte-Mobile.dc.html`
- `docs/telas/html/Modo-Suporte-Desktop.dc.html`
- `docs/telas/html/Modo-Suporte-Mobile.dc.html`
- `docs/telas/README.md`
- `tarefas/feito.md`

**Regras cobertas:**
- `IMP-07` (conclusão do passo recebimentos mediante subconta aprovada)
- `FIN-04` (conexão de recebimentos e subcontas)
- `DEV-02` (reembolsos de caução e acerto)
- `AUT-05`, `S-14` (pendências do pagamento por divergência de valor ou ausência de cobrança aberta)
- `PLT-07`, `AUD-01`, `AUD-09` (modo suporte, auditoria de alterações e privacidade de dados)

**Próximo passo para quem recebe:**
- Orquestrador: conferência da entrega e abertura do PR a partir da branch `t-381-ajustes-telas-t358`.
- Frontend: uso das telas de referência atualizadas para implementação das páginas e fluxos.

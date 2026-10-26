# T-384 · Revisão dos contratos da T-358 · segurança → orquestrador, arquiteto, backend

**O que foi feito:** revisão do PR #398 (branch `t-358-contratos-fase-1`):
- o suporte aberto pelo Django Admin, a página `/suporte/entrar`, a faixa, o cliente HTTP e a tela `Admin-Suporte`;
- `GET` e `POST /api/recebimentos/`;
- as listas de reembolsos e de pendências do pagamento.

Relatório: `docs/seguranca/2026-10-25-t384-contratos-t358.md`. Li o código que os contratos reaproveitam: `conectar_recebimentos`, `atualizar_recebimentos`, `transicionar`, `abrir_acesso_suporte` e o log do `asaas.py`. Nenhum código nem contrato mudou, e não rodei teste: é revisão de contrato.
**Regras:** PLT-07, AUD-05, AUD-09, FIN-04, PLT-12, DEV-02. **ADRs:** 0007, 0013, 0029.
**Branch:** `t-384-revisao-contratos-t358`, a partir da `origin/t-358-contratos-fase-1`. Entra depois do PR #398.

**Resultado:** sem achado alto. O #398 pode seguir.

**Para o arquiteto (mudanças no contrato):**
- **M-01**, `plataforma.md`, `POST /api/recebimentos/`: "Trava a empresa antes de chamar o parceiro: dois envios ao mesmo tempo criam uma subconta só, e o outro recebe 409 `recebimentos_conectados`."
- **M-02**, `financeiro.md`, reembolsos, `comprovante`: "Com token de suporte, sempre `null` (`AUD-09`), como os documentos do cliente."
- **B-01**, `plataforma.md`, `GET /api/recebimentos/`: trocar "com cache no Redis" por "com trava atômica no Redis (`cache.add`) por empresa; quem não pega a trava responde a situação gravada".
- **B-02**, `plataforma.md`, `POST /api/recebimentos/`: "O corpo vai só ao parceiro: não é gravado no Giro, não entra no evento `conta_pagamento.criar` nem em log. Limite de 10 envios por hora por empresa (429)."
- **B-03**, `plataforma.md`, `sugestao`: "do administrador que está logado".

**Para o backend (critérios das tarefas):**
- **T-366 (recebimentos):**
  - M-01: `select_for_update` na `Empresa` antes de `criar_subconta`; se o `save` falhar depois, logar só o `conta_externa_id`. Teste `test_fin_04_conectar_em_paralelo_cria_uma_subconta`;
  - B-01: `cache.add` como trava da consulta, e a transição já feita não vira 409;
  - B-02: throttle no `POST` e teste de que o corpo não fica na auditoria nem no log;
  - B-03: `sugestao` do `request.user`.
- **Listas de reembolsos e pendências:** M-02, `comprovante: null` para o token de suporte, conferido no `test_plt_07_reembolso_suporte_sem_marcar_feito`.
- **Suporte pelo Admin:** B-04, a ação confere a função Dono, o "Abrir" usa `rel="noopener noreferrer"` e o teste confere o `Cache-Control: no-store`.

**Para o produto e o frontend (sem tarefa):** recarregar a aba do suporte encerra o modo suporte, porque o token fica só em memória. Para continuar, é preciso um acesso novo, com outro e-mail ao administrador. A tela deve dizer isso.

**Próximo passo:** o orquestrador leva as cinco frases ao arquiteto, no #398 ou numa tarefa curta, e põe os critérios nas tarefas do backend.

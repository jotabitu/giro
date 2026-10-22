# T-346 · Reconfirmar as 2 etapas nas ações sensíveis (contrato) · arquiteto → orquestrador, backend, frontend

**O que foi feito:**
1. **Rota nova** `POST /api/auth/2fa/reconfirmar/` em `docs/api/contas.md`, seção "Reconfirmar as 2 etapas":
   - **Corpo:** `{ codigo }` ou `{ codigo_recuperacao }`.
   - **200:** `{ "access" }` com `Cache-Control: no-store`. É só um access novo, com o mesmo `sid`, `schema`, `empresa_id` e `amr`, mais `auth_time` = agora. Não abre sessão, não emite refresh e não grava cookie.
   - **Bloqueio:** o mesmo do login, por `dois_fatores.verificar_codigo` (`USR-06`; `PLT-08` no `public`).
   - **Código errado:** 400 `validacao` no campo enviado, e não 401, para o cliente HTTP não tentar renovar.
   - **Quem não tem autenticador:** 409 `2fa_inativo`.
   - **Token de suporte:** 403 `PLT-07`.
   - **Eventos `seguranca`, sem o código:** `usuario.reconfirmar_2fa` e `usuario.reconfirmar_2fa_falhou`.
   - **Como a tela trata o 403 `2fa_recente`:** pede o código, reconfirma e repete o pedido uma vez.
2. **ADR 0032** (aceita). A decisão é de arquitetura porque muda onde nasce o `auth_time` (no login e na reconfirmação) e cria uma emissão de access sem refresh. A ADR registra as alternativas descartadas (sair e entrar, refresh novo, cabeçalho por ação, senha). Também está no `docs/decisoes/README.md`.
3. `cancelamento.md` (2 etapas recentes) e `auditoria.md` (backup completo) agora apontam para a rota.

**Achado:** o `renovar` já não leva o `auth_time` (T-345). Então a janela de "15 minutos" de hoje dura, na prática, só o primeiro access do login, que vive 5 minutos. Não mudei isso: a ADR mantém a rotação sem `auth_time`, porque a tela repete o pedido logo depois de reconfirmar. Se a Segurança preferir a janela inteira de 15 minutos, isso é uma ADR nova.

**Por que só um access, sem refresh:** o `2fa/ativar/` troca o refresh. Feito aqui, isso disputaria com um `renovar` de outra aba, que veria o refresh antigo e revogaria a sessão por reuso (P-07).

## Tarefa do backend (a numerar)

**Agente:** backend · **Depende de:** T-345 (feita) · **Regras:** USR-02, USR-06, PLT-06, PLT-07, S-15 · **Contrato:** `contas.md`, "Reconfirmar as 2 etapas"; ADR 0032.

**Pronto quando:**
- `POST /api/auth/2fa/reconfirmar/` existe como view `Logada`, com o serializer do `2fa/verificar/` (um dos dois campos).
- **Token:** uma função em `comum.autenticacao` emite o access a partir das claims do token atual (`sid`, `schema`, `empresa_id`, `amr`) com `auth_time` = agora. Não chama `emitir_tokens`: não cria `Sessao`, não vincula `jti` e não grava cookie. A docstring de `CLAIM_AUTH_TIME` cita o login e a reconfirmação.
- **Bloqueio e códigos:** o código passa por `dois_fatores.verificar_codigo`. Código errado: 400 `validacao` no campo enviado. Bloqueio: 429 `USR-06`, com `usuario.bloqueado` e o aviso aos administradores, como no login. Sem autenticador: 409 `2fa_inativo`, antes de contar tentativa.
- **Eventos e textos:** `usuario.reconfirmar_2fa` ("Confirmou o código do autenticador") e `usuario.reconfirmar_2fa_falhou` ("Errou o código do autenticador", motivo `código` ou `código de recuperação`), com os textos em `auditoria.textos`. Com código de recuperação, também `usuario.usar_codigo_recuperacao`.
- **Testes:**
  - `test_usr_02_reconfirmar_devolve_access_na_mesma_sessao`: mesmo `sid` e `amr`, `auth_time` presente, nenhuma `Sessao` nova, sem `Set-Cookie`.
  - `test_usr_02_reconfirmar_libera_o_cancelamento`: login, relógio 16 min à frente, `renovar`, 403 `2fa_recente`; depois de reconfirmar, o `POST cancelamento/` passa da conferência das 2 etapas.
  - `test_usr_06_reconfirmar_conta_tentativas_e_bloqueia`: soma com a senha; o bloqueio vale no `auth/entrar/`.
  - `test_usr_02_reconfirmar_com_codigo_de_recuperacao`: o código só vale uma vez.
  - `test_usr_02_reconfirmar_sem_autenticador`
  - `test_plt_07_reconfirmar_recusa_suporte`
  - `test_usr_02_reconfirmar_evento_sem_o_codigo`
  - um teste de que o `renovar` depois da reconfirmação continua sem `auth_time`.
- OpenAPI regenerado (`docs/api/openapi.yaml`).

## Tarefa do frontend (a numerar, depois da do backend)

**Agente:** frontend · **Depende de:** a tarefa do backend acima, T-198 (feita) · **Regras:** USR-02, USR-06, PLT-06 · **Telas:** `Admin-Cancelar` · **Contrato:** `contas.md`, "Como a tela trata o 403 `2fa_recente`".

**Pronto quando:**
- Um ponto só (um diálogo e um auxiliar em volta da chamada) trata o 403 `2fa_recente`, para o backup completo da fase 2 reaproveitar:
  - O texto do diálogo é a `mensagem` do 403.
  - O campo de 6 dígitos usa as palavras da etapa do código no `Login`, com o link "Usar um código de recuperação".
  - "Confirmar" chama `POST /api/auth/2fa/reconfirmar/`, troca o access em memória (`definirAccess`) e repete o mesmo pedido uma vez, com o mesmo corpo.
  - Se a repetição voltar 403 `2fa_recente` de novo, mostra a mensagem e não repete outra vez.
- **Erros da reconfirmação:**
  - 400: erro no campo, e o diálogo fica aberto;
  - 429: a `mensagem` com o horário de `tentar_de_novo_em`, e o diálogo fecha;
  - 409 `2fa_inativo`: a `mensagem`.
  - "Cancelar" não envia nada.
- **Na `Admin-Cancelar`:** o motivo e o nome digitado continuam preenchidos durante a reconfirmação, e nada recarrega. O cancelamento termina sem sair do sistema.
- O código não fica no estado depois do envio, nem no cache do TanStack Query.
- **Testes (vitest):** o caminho feliz (403, código, repete, cancela), o código errado, o "Cancelar" sem envio, o 429 e a segunda recusa sem laço.

**Onde:** `docs/api/contas.md`, `docs/decisoes/0032-reconfirmar-2-etapas.md`, `docs/decisoes/README.md`, `docs/api/cancelamento.md`, `docs/api/auditoria.md`, `tarefas/backlog.md` (estado da T-346) e `tarefas/feito.md`.
**Regras cobertas:** `USR-02`, `USR-06`, `PLT-06`, `PLT-07`, `S-15` (nenhuma regra muda).
**O que ficou de fora:**
- O painel da plataforma não tem ação com `2fa_recente`. Quando tiver, usa a mesma rota em `plataforma.md`, com a `PLT-08`.
- Não há tela de referência do diálogo. A tela usa as palavras da etapa do código no `Login`. Se o design-system quiser desenhar uma, não bloqueia nenhuma das duas tarefas.

**Próximo passo para quem recebe:** o orquestrador numera as duas tarefas e libera a do backend; a do frontend vem depois dela. Se quiser, a segurança confere a rota junto com a T-345. Branch `t-346-reconfirmar-2-etapas`, sem PR.

# T-345 · Cancelamento: 2 etapas recentes, empresa apagada e recusa do parceiro · backend → orquestrador, segurança, frontend (T-198), qa, devops

Branch `t-345-cancelamento-seguranca`, criada da `origin/main` (9db448e, com o #375, o #376 e o #378). Origem: achados M-01 a M-03 e B-01 a B-03 da T-199 (`docs/seguranca/2026-10-20-t199-cancelamento.md`).

**O que foi feito:**

- **M-01 · 2 etapas recentes para cancelar.** `POST /api/assinatura/cancelamento/` responde 403 `{ "codigo": "2fa_recente", "mensagem": "Confirme o código do autenticador para cancelar a assinatura." }` sem `otp` no `amr` e `auth_time` de no máximo 15 minutos.
  - A checagem vem antes de qualquer outra conferência (corpo, nome, estado). As de perfil e de suporte continuam nas permissões da view, antes dela.
  - `dois_fatores_recente` e `token_da_requisicao` saíram de `auditoria` para `comum.autenticacao`, como a segurança sugeriu. A auditoria importa de lá, com o mesmo comportamento para o backup completo.
  - `DELETE cancelamento/`, pausar e voltar não pedem a confirmação.
- **M-02 · Suporte na cancelada e empresa apagada.**
  - `abrir_acesso_suporte` recusa a `cancelada` com 409 `{ "codigo": "empresa_cancelada", "mensagem": "Esta empresa cancelou a assinatura. O suporte não entra." }`, antes do suporte bloqueado. Nada é criado e nenhum e-mail sai.
  - **Entrada única no schema:** `plataforma.services.no_schema_da_empresa(empresa, com_tenant=False)`. Ela levanta `EmpresaApagada` (subclasse de `comum.tarefas.EmpresaIndisponivel`) quando `apagada_em` está preenchido. Os 9 pontos do relatório passam por ela:
    - `criar_empresa`, `recalcular_uso` e `_auditar_na_empresa`;
    - `definir_bloqueio_do_suporte`, `_registrar_nos_dois` e `escolher_forma_pagamento`;
    - `transicionar_empresa`, `destinatarios_da_cobranca` e `_administradores_ativos`.
  - **Escolha:** a entrada confere o `apagada_em` em memória e não o `pg_namespace`. Conferir o `pg_namespace` somaria uma consulta em todo evento gravado nos dois schemas. Entre o `DROP` e a gravação de `apagada_em`, só o próprio `apagar_empresa` mexe na empresa, e ele grava só no `public`.
- **M-03 · Recusa do parceiro.**
  - **Apagamento:** a recusa do parceiro na anonimização não segura os itens 3 e 4 do passo (c). Ela fica no log de erro (só o id da empresa) e no evento `empresa.apagar`, que ganhou `pagador_anonimizado`: `true`, `false` com a recusa, ou `null` sem pagador. Com o parceiro fora do ar, segue como antes: tenta no dia seguinte.
  - **Fim da forma (`encerrar_forma_pagamento`):** o cartão sai sempre, mesmo com o parceiro recusando ou fora do ar.
    - Recusa: se a consulta mostrar a autorização `cancelada` (ou inexistente, que a interface já devolve como `cancelada`), conta como encerrada. Senão, devolve `parceiro_recusou`, guarda a autorização e registra o log de erro.
    - Fora do ar: grava o resto e levanta `ParceiroForaDoAr` depois do commit, para a tarefa tentar de novo.
  - **Falso de pagamentos:** `recusar_operacao(nome, mensagem)` faz o parceiro recusar `cancelar_autorizacao` e `anonimizar_pagador` até o `limpar()`.
- **B-01:** `apagar_empresas` registra um log de erro quando há empresa a apagar e falta a `DATABASE_URL_MIGRACAO`. A falta não impede o web de subir, como a segurança sugeriu.
- **B-03:** `SecurityMiddleware` e `XFrameOptionsMiddleware` passaram para logo depois do `TenantMainMiddleware`, antes do `EmpresaCanceladaMiddleware`. O 403 `empresa_cancelada` sai com `X-Content-Type-Options: nosniff` e `X-Frame-Options: DENY`.
- **Contrato:** `docs/api/cancelamento.md` traz:
  - a decisão das 2 etapas, com a mensagem, e a linha 403 `2fa_recente` na tabela de erros;
  - o suporte recusado na `cancelada` e a entrada única no schema;
  - a recusa do parceiro no fim da forma e no item 2 do apagamento;
  - o `pagador_anonimizado` no evento e o log da B-01.

**Onde:** `backend/comum/autenticacao.py`; `backend/apps/auditoria/services.py`; `backend/apps/plataforma/services.py` e `api/assinatura.py`; `backend/integracoes/pagamentos/falso.py`; `backend/config/settings/base.py`; `docs/api/cancelamento.md`.

**Regras cobertas:** PLT-06, PLT-07, AUD-08, USR-02. Testes novos em `backend/tests/aceitacao/test_t345_cancelamento_seguranca.py`:

- M-01: `test_plt_06_cancelar_pede_2_etapas_recentes`;
- M-02: `test_plt_07_suporte_nao_entra_na_cancelada` e `test_aud_08_empresa_apagada_nao_cai_no_publico`;
- M-03:
  - `test_aud_08_recusa_do_parceiro_nao_trava_o_apagamento` e `test_aud_08_pagador_anonimizado_no_evento`;
  - `test_plt_06_fim_da_forma_esquece_o_cartao_com_recusa`, `test_plt_06_autorizacao_ja_cancelada_conta_como_encerrada` e `test_plt_06_fim_da_forma_com_o_parceiro_fora_do_ar`;
- B-01: `test_aud_08_apagar_sem_database_url_migracao_avisa`;
- B-03: `test_aud_08_cancelada_responde_com_os_cabecalhos_de_seguranca`.

**Testes rodados** (num container avulso na rede `giro-backend-teste`, banco `giro`, uma rodada por vez): `ruff check`, `ruff format --check`, `mypy` (400 arquivos), `makemigrations --check` (sem mudança) e o OpenAPI com `--validate` (0 erros, sem diff). Pytest com `--create-db`:

- **Rodada completa:** `test_t345`, `t195`, `t185`, `t185b`, `t186`, `t186b`, `t184`, `t010`, `t011`, `t014`, `t018`, `t317`, `t315`, `t250`, `t262`, `t129`, `t153`, `t181`, `t202`, `apps/plataforma`, `comum`, `tests/test_permissoes_das_rotas.py` e `tests/test_autenticacao.py`. Resultado: 727 passaram, 1 xfail e 2 falharam:
  - `test_aud_08_apaga_no_90_dia` compara o evento inteiro e não tinha o `pagador_anonimizado` novo;
  - `test_plt_07_lista_de_rotas_que_o_suporte_le` (T-011) não tinha as rotas `cancelamento/` e `pausa/` da T-195, que herdaram `suporte_somente_leitura` da base da assinatura. Elas entraram na lista de propósito: o suporte só lê a tela de cancelar, e toda escrita dele recebe o 403 `PLT-07`.
- **Depois da correção:** as duas expectativas atualizadas, rodadas de novo com o `test_t345`: 12 passaram.

**O que ficou de fora:**

- **B-02, para a tarefa da reativação (quando entrar):** recusar a empresa com o apagamento começado. Uma forma é gravar `apagamento_iniciado_em` com a `Empresa` travada antes do passo (a). Hoje nada reativa uma `cancelada`.
- **B-01, para o devops:** a `DATABASE_URL_MIGRACAO` vai só para o worker da `aud_08_apagar_empresas`, nunca para o backend web. Na homologação, o worker ainda não a recebe.
- **Sugestão da T-199:** pedir 2 etapas recentes também para trocar a forma de pagamento. Não entrou porque estava fora do escopo da T-345.

**Próximo passo para quem recebe:**

- **Frontend (T-198):** na `Admin-Cancelar`, o 403 `2fa_recente` pede o código do autenticador e repete o envio (como o backup completo da auditoria).
- **Segurança:** conferir os 5 achados. O M-02 usa o `apagada_em`, e não o `pg_namespace`; o motivo está acima.
- **QA:** os testes acima. Nos critérios do cancelamento, o envio sem 2 etapas recentes recebe o 403.
- **Devops:** o item B-01 acima.

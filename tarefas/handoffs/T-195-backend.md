# T-195 · Cancelar, pausar e apagar a assinatura · backend → orquestrador, frontend (T-198), qa (T-204, T-215), segurança (T-199), produto, devops

Branch `t-195-cancelar-pausar`, criada da `origin/main`. Contrato `docs/api/cancelamento.md` (T-194, com as decisões da T-211, T-231 e T-236).

**O que foi feito:**

- **Modelo** (migração `plataforma.0012_cancelar_e_pausar`): `Empresa.pausa_inicio`, `cancelamento_pedido_em`, `aviso_apagamento_enviado_em`, `apagada_em` e `motivo_cancelamento` como enum (`MotivoCancelamento`: `preco_alto`, `faltou_funcao`, `outro_sistema`, `fechar_ou_pausar`, `outro`). As transições da tabela de estados ganharam `pausada` e `cancelada` (a `pausada` volta `ativa` ou `inadimplente`). Os campos de cancelamento da `FaturaAssinatura` (`motivo_cancelamento`, `cancelada_em`, `substituida_por`) já existiam desde a T-184.
- **Datas** (`calendario.py`, funções puras): `datas_do_cancelamento(hoje, status, teste_fim, fim_do_periodo_pago)` dá o último dia de acesso, o dia em que vira `cancelada` e o do apagamento (+90). Cobre os casos (a) a (d) dos dados de referência e o anual. `periodo_da_pausa(inicio, meses)` vai de 1 a 3 meses, com a regra do mês sem o dia.
- **Serviços** (`services.py`; todos travam a `Empresa` e gravam auditoria no `public` e na empresa):
  - `cancelar_assinatura`: na `em_teste` e na `ativa`, o cancelamento fica marcado com acesso até o fim do teste ou do período pago, e a mensalidade do período seguinte, se já gerada, vira `cancelada` (motivo `cancelamento_assinatura`, com a cobrança cancelada no parceiro). Na `inadimplente`, na `suspensa` e na `pausada`, a empresa vira `cancelada` na hora: as `atrasada` continuam devidas e a régua para. A pausa marcada acaba nos dois casos. O nome digitado é conferido no serviço: sem espaços nas pontas nem repetidos, sem diferença de maiúsculas, acentos contam.
  - `desfazer_cancelamento`: até `acesso_ate`. Cada fatura que esse cancelamento cancelou nasce de novo, igual e `aberta`, com o próximo código, e a cancelada aponta para ela por `substituida_por`. A cobrança sai como na emissão: na hora se vence em até 5 dias, senão pela `gerar_faturas`.
  - `pausar_assinatura`, `desistir_da_pausa` (até a véspera de `pausa_inicio`; a fatura que a pausa cancelou nasce de novo) e `voltar_da_pausa`. A volta deixa a empresa `ativa`, ou `inadimplente` se a diferença do upgrade ainda estiver atrasada. A fatura da volta vence hoje, o `dia_vencimento` passa a ser o de hoje e a cobrança sai na hora. Com downgrade agendado, ele é conferido e vale já na volta.
  - `encerrar_forma_pagamento` (tarefa `plataforma_encerrar_forma_pagamento`, depois do commit, com nova tentativa se o parceiro estiver fora): quando a empresa vira `cancelada`, cancela a autorização do Pix automático, esquece o token do cartão e deixa a `forma` nula (ADR 0023).
- **Virada do dia** (`virar_estados`, antes das transições da assinatura): `virar_cancelada` no dia seguinte a `acesso_ate`, `iniciar_pausa` em `pausa_inicio` e a volta automática no dia seguinte a `pausada_ate`. As três são idempotentes. A `gerar_faturas` também não gera fatura para período que começa na pausa (o filtro do cancelamento marcado já existia).
- **AUD-08 (ADR 0025):**
  - `aud_08_avisar_apagamento` (Beat 09:00): aviso 7 dias antes, uma vez só, aos administradores ativos.
  - `aud_08_apagar_empresas` (Beat 03:30), uma empresa por vez, pelo `apagar_empresa`, nesta ordem: (a) arquivos do prefixo `<schema>/` (`comum.arquivos.apagar_arquivos_da_empresa`, com `apagar_prefixo` no provedor falso e no S3, versões incluídas); (b) o schema, por `plataforma.banco.apagar_schema`, o único `DROP SCHEMA` do código; (c) o `public`, nas 4 partes do contrato; (d) `apagada_em` e o evento `empresa.apagar` (segurança, ator sistema, sem dado pessoal).
  - `apagar_schema` usa `psycopg.sql.Identifier`, confere de novo com a `Empresa` travada e recusa `public`, `pg_*`, `information_schema` e nome fora do padrão. Roda pela `DATABASE_URL_MIGRACAO` quando ela existe; sem ela, usa a conexão da aplicação (dev e testes).
  - A empresa que falha fica para o dia seguinte e vai ao Sentry pelo log de erro.
  - `anonimizar_pagador` entrou na interface de pagamentos, no fake (lista `anonimizados`) e no Asaas.
  - A baixa da fatura de empresa apagada só grava no `public` e limpa o `email_cobranca` da fatura.
  - O `TenantMixin.save()` do django-tenants recria o schema que falta de uma empresa já existente. O `Empresa.save()` desliga isso na `cancelada`, senão o primeiro `save` depois do DROP traria o schema de volta.
- **Empresa `cancelada`:** `comum.middleware.EmpresaCanceladaMiddleware`, logo depois do middleware do tenant, responde 403 `empresa_cancelada` a todo pedido, inclusive `entrar` e `renovar`.
- **Rotas:** `GET`, `POST` e `DELETE /api/assinatura/cancelamento/`; `POST` e `DELETE /api/assinatura/pausa/`. O `DELETE pausa/` volta da pausa na `pausada` e desiste da pausa agendada na `ativa`. O `GET /api/assinatura/` ganhou os blocos `cancelamento` e `pausa`, `proxima_fatura` nula com a pausa marcada, a faixa da `pausada` e as ações `cancelar`, `desfazer_cancelamento`, `pausar`, `voltar_pausa` e `desistir_pausa`.
- **Exceções do somente leitura**, na lista explícita com teste: `escreve_na_suspensa` ganhou `POST cancelamento/`; o atributo novo `escreve_na_pausada` cobre `POST cancelamento/` e `DELETE pausa/`. `recusa_na_suspensa` agora aceita um mapa por método: o `POST pausa/` da `suspensa` responde o 409 "Pague a fatura em atraso antes de pausar.".
- **Painel da plataforma:** a situação "cancelando" passou a seguir o contrato (`acesso_ate` preenchido e não `cancelada`), com o rótulo do dia em que vira `cancelada`. A apagada mostra "Dados apagados".

**Onde:**

- `backend/apps/plataforma/`: `models.py`, `migrations/0012_cancelar_e_pausar.py`, `calendario.py`, `banco.py` (novo), `services.py`, `selectors.py`, `tasks.py`, `api/assinatura.py`, `api/serializers.py`, `api/urls.py`, `README.md`.
- `backend/comum/`: `middleware.py`, `permissoes.py`, `empresa.py`, `arquivos.py`.
- `backend/integracoes/pagamentos/`: `base.py`, `falso.py`, `asaas.py`.
- `backend/config/settings/base.py`: middleware, Beat, `DATABASE_URL_MIGRACAO` e os nomes de enum do OpenAPI.
- Testes antigos ajustados ao contrato: `test_t185_assinatura.py`, `test_t185b_forma_faturas.py` e `test_t010_plataforma.py`. A `cancelada` agora recebe `empresa_cancelada` em tudo, a `pausada` tem só "Voltar da pausa" e mostra a faixa nova com a data, e a lista de exceções da suspensa inclui o `POST cancelamento/`.
- `frontend/`: só os falsos (`falso-assinatura.ts` e `Assinatura.test.tsx`) ganharam as ações e os campos novos, para o typecheck passar. Nenhuma tela mudou.

**Contrato:** as 5 rotas acima e os campos novos do `GET /api/assinatura/`, em `docs/api/openapi.yaml`. Só acréscimos: nenhum schema existente mudou de nome. Enums novos: `MotivoCancelamentoEnum` e `SituacaoDaPausaEnum`.

**Regras cobertas:** PLT-06, AUD-08 e as decisões T-211, T-229, T-231 e T-236. Testes em `backend/tests/aceitacao/test_t195_cancelar_pausar.py` e `backend/apps/plataforma/tests/test_calendario.py`:

- cancelar: `test_plt_06_cancelar_no_teste` (CA-ASS-30), `test_plt_06_nome_nao_confere` (CA-ASS-31), `test_plt_06_cancelar_ativa` e `_com_a_fatura_seguinte_emitida` (CA-ASS-32), `test_plt_06_cancelar_anual_sem_devolucao` (CA-ASS-33), `test_plt_06_cancelar_inadimplente_para_a_regua` (CA-ASS-34), `test_plt_06_cancelar_no_teste_com_a_1a_paga` (CA-ASS-54);
- pausar: `test_plt_06_pausar_por_ate_3_meses` e `test_plt_06_pausa_e_volta_automatica` (CA-ASS-35), `test_plt_06_volta_manual_da_pausa` (CA-ASS-36), `test_plt_06_quem_nao_pausa` (CA-ASS-37), `test_plt_06_pausa_comeca_no_fim_do_periodo_pago` (CA-ASS-42), `test_plt_06_desistir_da_pausa_agendada` (CA-ASS-55);
- desfazer: `test_plt_06_desfazer_cancelamento_no_teste` (CA-ASS-43), `test_plt_06_desfazer_cancelamento_na_ativa` e `_com_a_fatura_emitida` (CA-ASS-44), `test_plt_06_quem_nao_desfaz` (CA-ASS-45);
- mudanças com cancelamento ou pausa: `test_plt_06_mudar_de_plano_com_cancelamento_marcado` (CA-ASS-56), `test_plt_06_diferenca_em_aberto_na_pausa` (CA-ASS-57);
- virada e exceções: `test_plt_06_cancelada_no_dia_seguinte_ao_acesso`, `test_plt_06_excecoes_do_somente_leitura`, `test_plt_06_suspensa_e_pausada_cancelam_na_hora`, `test_plt_06_so_o_administrador_cancela`;
- AUD-08: `test_aud_08_cancelada_nao_entra`, `test_aud_08_aviso_7_dias_antes`, `test_aud_08_apaga_no_90_dia`, `test_aud_08_nao_apaga_outra_empresa` (isolamento entre empresas), `test_aud_08_nao_apaga_reativada`, `test_aud_08_linha_apagada_so_com_cnpj` (CA-ASS-58) e `test_aud_08_fatura_atrasada_guarda_email` (CA-ASS-60);
- datas: os `test_plt_06_*` e `test_aud_08_*` de `test_calendario.py`.

**Testes rodados:** (preencher)

**O que ficou de fora:**

- **`[decisão]` nova no backlog:** cancelar a `ativa` com o período pago já vencido, no dia do vencimento da fatura seguinte ainda sem pagar. Padrão no código: o acesso termina agora, como na `inadimplente`. O produto confirma ou troca.
- **CNPJ único só entre as não apagadas** (`modelo-de-dados.md`, B-02) e a compra de quem já foi cliente (`PLT-16`, `empresa_anterior`, `situacao_do_cnpj`): ficam com a tarefa da `PLT-16`. Hoje a linha apagada guarda o CNPJ e o `unique` continua; quem tentar comprar com o mesmo CNPJ recebe `cnpj_em_uso`.
- **Campos `apagada`, `nome_exibicao` nulo e `uso` nulo da empresa apagada no painel** (`plataforma.md`, T-236): por ora só o rótulo "Dados apagados".
- **E-mail da fatura atrasada com a nota ligada:** com `GIRO_NFSE_ASSINATURA_ATIVA`, o contrato manda limpar o e-mail depois de a nota ser pedida. A emissão é da T-197; hoje o e-mail só sai na baixa com a nota desligada.
- **2 etapas recentes para cancelar:** espera a decisão da T-199.
- **Reativação pela equipe** (`reativar_empresa`, `assinatura.md`): não existe no código. Quando entrar, precisa limpar `cancelada_em`, `apagar_em`, `aviso_apagamento_enviado_em` e o cancelamento.
- Textos provisórios (`pausa.rotulo`, a faixa da `pausada` e o e-mail do aviso do apagamento) esperam a T-214 ou a T-200.

**Próximo passo para quem recebe:**

- **Frontend (T-198):** a `Admin-Cancelar` lê o `GET cancelamento/` e manda o `POST` com `motivo` e `nome_confirmacao`. O 409 do `GET` significa cancelamento já marcado: volte à `Admin-Assinatura`. A `Admin-Assinatura` mostra `cancelamento.rotulo` com "Desfazer cancelamento" (`DELETE cancelamento/`) e a `pausa`, com "Voltar da pausa" ou "Desistir da pausa", as duas no `DELETE pausa/`. A empresa cancelada recebe 403 `empresa_cancelada` em qualquer rota.
- **QA (T-204, T-215):** CA-ASS-30 a 39, 42 a 45, 54 a 58 e 60 com o relógio de referência; os números dos dados de referência estão nos testes acima.
- **Segurança (T-199):** a revisão do `banco.apagar_schema` e do `apagar_empresa`: conferência dupla, `Identifier` e nada de outra empresa. Também as exceções novas do somente leitura e as 2 etapas recentes para cancelar.
- **Devops:** o worker que roda `aud_08_apagar_empresas` precisa da `DATABASE_URL_MIGRACAO` (papel `giro_migracao`). Sem ela, o `DROP` tenta pela conexão da aplicação, que em produção (`giro_app`) não tem permissão, e a empresa fica para o dia seguinte com erro no Sentry.

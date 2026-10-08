# T-034 · Auditoria e Celery endurecidos · backend → orquestrador, devops, seguranca, qa

**O que foi feito:**
- **S-10 e C-05 (ADR 0016), migração `auditoria.0003_truncate_e_expurgo`:** a variável `giro.expurgo_auditoria` saiu do desenho. O trigger de linha recusa `UPDATE` sempre e `DELETE` exceto do papel `giro_expurgo` em evento com mais de 5 anos. Um trigger de comando recusa `TRUNCATE` (para qualquer papel, inclusive o dono). `auditoria_expurgar(limite date)` é `SECURITY DEFINER`, com `search_path` fixo no schema, e recusa limite nulo ou mais recente que 5 anos (AUD-02). A antiga `auditoria_expurgar_vencidos()` foi removida.
- **Permissões por schema:** `apps/auditoria/banco.py` (`aplicar_permissoes`), chamado no `post_migrate` de cada schema (public e empresas, inclusive empresa nova). Se o papel existir: `giro_app` com `SELECT, INSERT, UPDATE, DELETE` em todas as tabelas e sequências (e default privileges), **só `SELECT, INSERT`** na auditoria (`REVOKE UPDATE, DELETE, TRUNCATE`) e `EXECUTE` na função de expurgo; a função passa a ser de `giro_expurgo`, com `SELECT, DELETE` na auditoria; `EXECUTE` revogado de `PUBLIC`. Papel que não existe é ignorado: em dev com um papel só nada muda.
- **S-11:** `comum/worker.py`, ligado no `ready()` do `comum`: `task_prerun` e `task_postrun` voltam a conexão ao public e o ator ao Sistema (`comum.auditoria.limpar_ator`). Cache com `KEY_FUNCTION = django_tenants.cache.make_key` (Redis em `REDIS_URL`; LocMem nos testes). `CELERY_TASK_IGNORE_RESULT = True`.
- **C-03 (ADR 0018, item 4):** `comum/rede.py`, `ip_do_cliente(request)`, usado pelo middleware da auditoria. `X-Forwarded-For` só vale com `REMOTE_ADDR` numa rede de `GIRO_REDES_PROXY`; o cliente é `xff[-GIRO_PROXIES_CONFIAVEIS]`; sem cabeçalho, vazio, curto ou com valor que não é IP, vale o `REMOTE_ADDR`. Settings: `GIRO_REDES_PROXY` (padrão vazio = nunca confia) e `GIRO_PROXIES_CONFIAVEIS` (padrão 1).

- **R-01 da T-050 (média):** `na_empresa` entra com `tenant_context(empresa)` (a empresa devolvida por `conferir_empresa_para_tarefa`), não mais `schema_context`: dentro de tarefa a conexão tem a empresa real e a cifra e o hash de busca funcionam com o id dela. `@tarefa_de_empresa` deixou de consultar a empresa duas vezes.
- **R-04 da T-050 (baixa):** ator `suporte` vindo da fila sem `acesso_suporte_id` é recusado. Conferir que o acesso existe, é desta empresa e está no prazo fica com o model do acesso de suporte (T-011/T-029).

**Onde:** `backend/apps/auditoria/{banco.py,apps.py,models.py,migrations/0003_truncate_e_expurgo.py}`, `backend/comum/{worker.py,rede.py,apps.py,auditoria.py,middleware.py}`, `backend/config/settings/{base,test}.py`, `backend/conftest.py`, `backend/README.md`.

**Regras e testes** (`ruff`, `ruff format --check`, `mypy` estrito e `pytest --create-db` verdes no container; 146 testes e 105 xfail da QA; a branch já traz a T-033 (merge de `origin/t-033-dados-sensiveis`), porque R-01 mexe no `na_empresa` dela: mesclar o PR #16 antes):
- AUD-01: `test_aud_01_truncate_falha`, `test_aud_01_variavel_de_sessao_nao_libera_mais_o_delete`, `test_aud_01_papel_da_aplicacao_so_le_e_insere_na_auditoria` (com `SET ROLE giro_app`: `UPDATE`, `DELETE`, `TRUNCATE` e `DISABLE TRIGGER` recusados; `SELECT` e `INSERT` passam), `test_aud_01_nem_o_papel_do_expurgo_apaga_evento_recente`, `test_aud_01_update_falha_mesmo_para_o_papel_do_expurgo`, `test_aud_01_auditoria_grava_o_ip_do_cliente_atras_do_proxy`.
- AUD-02: `test_aud_02_expurgo_so_apaga_eventos_com_mais_de_5_anos` (como `giro_app`), `test_aud_02_expurgo_recusa_limite_mais_recente_que_5_anos`.
- `test_triggers_existem_no_schema_da_empresa_e_no_public` (os dois triggers em public, empresa_a e empresa_b).
- S-11: `test_ator_nao_vaza_entre_tarefas`, `test_cache_tem_o_schema_da_empresa_na_chave`, `test_cache_de_producao_tambem_usa_o_schema_na_chave`, `test_resultado_das_tarefas_nao_e_guardado_por_padrao`.
- R-01 e R-04: `test_cli_01_cifra_e_hash_dentro_de_tarefa_de_empresa` (cifra e hash dentro de `@tarefa_de_empresa`, hash igual ao da requisição da mesma empresa), `test_ator_do_suporte_sem_acesso_e_recusado`. Os dois falham com o código anterior.
- C-03: `test_ip_do_cliente_ignora_xff_forjado_sem_proxy`, `test_ip_do_cliente_com_proxy_confiavel_pega_a_entrada_da_direita` (exemplo da ADR: 203.0.113.9, nunca 1.2.3.4), `test_ip_do_cliente_com_cabecalho_curto_vale_o_remote_addr`, sem cabeçalho, vazio e inválido, IPv6, sem redes configuradas.
- O `conftest.py` cria `giro_app` e `giro_expurgo` (`NOLOGIN`) no banco de teste se faltarem e aplica as permissões. O papel do teste precisa poder criar papel (superusuário no Compose e no CI).

**Já entregue na T-033 (incluída nesta branch pelo merge):** `@tarefa_de_empresa`/`na_empresa` recusam `public`, empresa inexistente, fora de status e schema apagado, e restauram ator e schema.

**Para o devops (T-035):**
- `GRANT giro_expurgo TO giro_migracao` no `01-papeis.sh`: o `post_migrate` roda como `giro_migracao` e faz `ALTER FUNCTION ... OWNER TO giro_expurgo`, que exige ser membro do papel. Sem isso a migração falha quando os papéis estiverem separados.
- `GIRO_REDES_PROXY` e `GIRO_PROXIES_CONFIAVEIS` já são lidos pelo backend; o padrão do backend para `GIRO_REDES_PROXY` é vazio (não confia), então o `.env.example` e os ambientes precisam defini-lo.
- O backend não lê `DATABASE_URL_MIGRACAO`: rode `migrate_schemas` com `DATABASE_URL` apontando para o papel de migração. A conexão própria de `criar_empresa` fica para a T-010.
- Teste com `giro_app` de verdade no CI: a suíte já prova o `REVOKE` com `SET ROLE`; rodar a aplicação inteira como `giro_app` fica a seu critério.

**O que ficou de fora:**
- Tarefa mensal que chama `auditoria_expurgar`: não há código `AUT-NN` para ela nas regras (a tabela vai de AUT-01 a AUT-15). Fica a função; a tarefa entra quando o produto der o código.
- C-06 (requisição anônima auditada como Sistema) e cadeia de hash (ADR 0016 item 4): fora do escopo.

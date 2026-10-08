# T-033 · Dados sensíveis na fundação · backend → orquestrador, seguranca, qa, devops

**O que foi feito:** ADR 0014 itens 2 e 3, achados C-01 e C-02 da T-039 e ADR 0018 item 3, tudo em `backend/comum/`:
- `cripto.py`: só AES-256-GCM (`AESGCM`), nonce aleatório de 12 bytes, formato `v<id_da_chave>:<base64(nonce + cifrado)>`. Dado associado `empresa_id|tabela|campo|id_cifra`. Várias chaves por variável (`1:<b64>,2:<b64>`): a de maior id cifra, as outras só decifram (troca de chave sem migração em massa). `hash_busca` é HMAC-SHA256 do valor normalizado com chave por empresa, `HMAC(GIRO_PEPPER_HMAC, empresa_id)`.
- `models.ModeloComCifra`: `id_cifra` UUID único, gerado na criação e imutável (o `save()` recusa troca).
- `campos.CampoCifrado(tipo=DADOS_PESSOAIS|SEGREDOS)`: guarda só o cifrado, não editável (fora do Admin e de formulários); `obj.definir_<campo>(valor)` cifra e preenche os `CampoHashBusca` ligados; `obj.<campo>_claro()` decifra sob demanda. `CampoHashBusca(de=..., unique=True | db_index=True)`. `anonimizar_cifrado(obj, campo)` para AUD-06 (apaga o cifrado e troca o hash por aleatório; quem chama grava `anonimizado_em`).
- `classificacao.py`: `CAMPOS_AUDITORIA = {"omitir", "mascarar", "inteiro"}` e as máscaras da tabela da ADR 0014. Omitidos sem declarar: `password`, todo `CampoCifrado`, todo `CampoHashBusca` e todo `*_hash`. Campo omitido vira `{"alterado": true}`.
- `auditoria.py` (C-01): o retrato guarda os valores reais, o diff é feito sobre eles e só depois a classificação mascara ou omite. Troca de CPF com a mesma máscara agora gera evento.
- `tarefas.py` (C-02 e ADR 0018 item 3): `na_empresa(schema, *, regra, ator, inclui_suspensas)` confere no public que a empresa existe, está num status permitido e que o schema existe em `pg_namespace`; senão `EmpresaIndisponivel`, e `@tarefa_de_empresa` registra aviso e não faz nada. `ator_para_fila()` devolve `{"tipo", "id", "acesso_suporte_id"}` (sem nome) para passar como `ator=` ao agendar; a tarefa busca o nome no schema (usuário) ou no public (suporte).
- `Usuario` e `EventoAuditoria` classificados; `apps.auditoria`/`contas` sem migração nova.

**Onde:** `backend/comum/{cripto,campos,classificacao,auditoria,tarefas,models}.py`, `backend/tests/app_exemplo/` (`Pessoa` e `Credencial`, migração 0002), `backend/tests/test_campos_sensiveis.py`, `backend/config/settings/{base,test}.py`, `.env.example`, `backend/README.md`.

**Dependência nova:** `cryptography>=44` em `backend/requirements.txt`. Motivo: AES-256-GCM com dado associado (ADR 0014); Fernet não aceita AAD.

**Segredos novos no `.env.example`** (valores só de dev; homologação e produção pelo cofre, devops): `GIRO_CHAVE_DADOS_PESSOAIS`, `GIRO_CHAVE_SEGREDOS` (formato `<id>:<base64 de 32 bytes>`, várias por vírgula) e `GIRO_PEPPER_HMAC`. Nenhum é a `DJANGO_SECRET_KEY`. Perder uma chave é perder os dados cifrados: backup das chaves fora do backup do banco.

**Regras e testes:**
- CLI-01: `test_cli_01_cpf_unico_pelo_hash`, `test_cli_01_mesmo_cpf_em_outra_empresa_pode`, `test_busca_exata_pelo_hash`.
- AUD-01: `test_aud_01_troca_de_cpf_com_mesma_mascara_gera_evento` (C-01), `test_aud_01_troca_de_senha_nao_grava_hash`, `test_aud_01_troca_de_documento_cifrado_gera_evento_sem_valor`.
- AUD-06: `test_aud_06_auditoria_de_pessoa_nao_guarda_nome_nem_documento_completos`, `test_aud_06_anonimizar_apaga_o_cifrado_e_troca_o_hash`.
- Cifra: cifrado copiado para outra linha, outro campo e outra empresa não decifra; adulterado não decifra; troca de chave; chaves separadas; `id_cifra` imutável; par `id_cifra` + cifrado copiado para outra linha recusado (único).
- Segredo: `test_conta_pagamento_chave_nao_aparece_em_formulario_e_auditoria` (sobre o model de teste `Credencial`).
- Arquitetura: `tests/test_campos_sensiveis.py` falha se um model do Giro tiver campo de nome sensível sem classificação, `CampoCifrado` fora de `ModeloComCifra` ou `CampoHashBusca` apontando para campo que não é cifrado.
- C-02: `test_tarefa_de_empresa_com_schema_apagado_nao_cai_no_public`, `..._inexistente_...`, `..._suspensa_nao_roda_e_nao_falha`, `test_tarefa_de_leitura_roda_em_empresa_suspensa`.
- Ator: `test_tarefa_pedida_por_pessoa_age_em_nome_dela`, `test_tarefa_sem_ator_e_do_sistema_e_sistema_nao_vai_para_a_fila`.
- `ruff check`, `ruff format --check`, `mypy` (estrito) e `pytest`: verde, 127 testes, no container do worktree.

**O que ficou de fora:**
- `plataforma.ContaPagamento` ainda não existe; o teste usa o model de teste `Credencial` (mesmo campo). Quando o model real entrar, o teste `test_conta_pagamento_chave_nao_aparece_em_serializer_admin_e_auditoria` vai com ele (serializer não existe hoje).
- `Cliente` com `documento`, `cnh_numero`, `responsavel_cpf` cifrados e os hashes: T-014. A máscara de AUD-04 no serializer também.
- `contas.Sessao` e `test_usr_04_desativar_derruba_access_na_proxima_requisicao`: T-011 (ADR 0014 item 1).
- `REGRA_TRANSICAO = "transicao_<entidade>"` (ADR 0018 item 2) e `ip_do_cliente` (item 4): não são desta tarefa; o item 4 está na T-034.

**Próximo passo para quem recebe:**
- seguranca: conferir `comum/cripto.py`, `classificacao.py` e o diff da auditoria contra S-05, S-06, S-07 e C-01/C-02.
- devops: os três segredos por ambiente no cofre e o backup das chaves.
- backend (T-011, T-014): models com dado pessoal herdam `ModeloComCifra` e declaram `CAMPOS_AUDITORIA`; o teste de arquitetura cobra.

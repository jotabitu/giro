# T-058 · Correções de segurança da T-057 · backend → seguranca, qa, frontend, arquiteto, devops, orquestrador

**O que foi feito** (P-01 a P-04 de `docs/seguranca/2026-10-08-codigo-t010.md`):
- **P-01 · Admin:** o login do Django Admin usa `contas/login_admin.py` (`LoginDoAdmin`, ligado em `config/urls_publico.py`). Ele passa pelo mesmo `dois_fatores.tentar_entrar` da API: 3 códigos ou 5 senhas errados bloqueiam por 15 minutos e, enquanto o bloqueio vale, o código certo é recusado. Cada entrada e cada falha geram `usuario.entrar` e `usuario.entrar_falhou`, com IP e aparelho. Conta sem `is_staff` ou sem autenticador é recusada, e a recusa também fica auditada. O atraso progressivo do django-otp continua desligado, porque o bloqueio do Giro vale agora nos dois caminhos.
- **P-02 · corrida:** `tentar_entrar` (senha e código) e `verificar_codigo` (etapa `pre_2fa`) abrem uma transação que começa com `select_for_update` na linha do usuário. Depois conferem o bloqueio, verificam a senha e o código e contam o erro. As tentativas da mesma conta passam uma de cada vez. Com isso, o mesmo código TOTP ou de recuperação não é aceito duas vezes (o `last_t` e o `delete` do `StaticToken` rodam com a trava).
- **P-03 · senha:** quem tem autenticador e não manda código recebe o mesmo 401 `credenciais_invalidas` da senha errada, e esse caso conta como senha errada. A 5ª senha errada bloqueia por 15 minutos com 429 `PLT-08` "Acesso bloqueado por 15 minutos depois de 5 senhas erradas" e o evento `usuario.bloqueado` com o motivo "5 senhas erradas". Isso segue a decisão de 08/10 e a PLT-08 do PR #39 (T-059). Entrar com sucesso zera as duas contagens. Senha certa com código errado não zera a de senhas, para a contagem não revelar a senha. Campo novo: `Usuario.senhas_erradas` (migração `contas.0004`).
- **P-03 · throttle:** em `comum/limites.py` (DRF, cache Redis). O `entrar` aceita 10 por minuto e 50 por hora por IP e por e-mail (o e-mail entra em hash na chave, exista ou não). `convites/{token}/`, `aceitar/`, `renovar`, `sair` e `2fa/` aceitam 30 por minuto por IP. Acima disso, a resposta é 429 `muitas_requisicoes` com `detalhes.tentar_de_novo_em_segundos` e `Retry-After`. As taxas ficam em `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.
- **P-04 · schema:** `public`, `information-schema` e qualquer `pg-*` passaram a ser reservados. Um subdomínio cujo schema já existe no Postgres sem ser de empresa é recusado em `validar_criacao` com 400 `validacao` "Este endereço é reservado. Escolha outro.". `criar_empresa` cria o schema com `create_schema(check_if_exists=False)`: se ele aparecer entre a validação e a criação, a transação volta inteira (400) e o schema nunca é reaproveitado.

**Onde:** `backend/apps/contas/dois_fatores.py`, `login_admin.py`, `api/plataforma.py`, `models.py` e a migração `0004_usuario_senhas_erradas`. Também `backend/apps/plataforma/services.py`, `backend/comum/limites.py`, `backend/comum/erros.py` (429 `muitas_requisicoes`), `backend/config/settings/base.py`, `backend/config/urls_publico.py`, `backend/conftest.py` (o cache é limpo a cada teste), `backend/tests/aceitacao/test_t058_seguranca.py` e o CA-010-18 em `test_t010_plataforma.py`.

**Contrato:** `docs/api/plataforma.md` (`entrar` e `2fa/verificar`). O OpenAPI gerado é igual ao `docs/api/openapi.yaml`.

**Regras e testes:**
- P-01: `test_plt_08_admin_entra_com_codigo_certo_e_audita`, `test_plt_08_admin_bloqueia_depois_de_3_codigos_errados`, `test_plt_08_admin_bloqueado_recusa_codigo_certo`, `test_plt_08_admin_bloqueia_depois_de_5_senhas_erradas` e `test_plt_08_admin_recusa_quem_nao_e_da_equipe_do_admin`.
- P-02: `test_plt_08_codigos_em_paralelo_nao_passam_do_limite` (12 threads, cada uma com a própria conexão: no máximo 3 verificações) e `test_plt_08_mesmo_codigo_em_paralelo_aceito_uma_vez`. Conferi que os dois falham sem a trava: 12 verificações e o código aceito 3 vezes.
- P-03: `test_plt_08_ca_010_18_cinco_senhas_erradas_bloqueiam_por_15_minutos` (CA-010-18 do PR #39), `test_plt_08_senha_certa_sem_codigo_responde_como_senha_errada`, `test_plt_08_bloqueio_por_senha_tem_mensagem_propria`, `test_plt_08_senha_certa_com_codigo_errado_nao_zera_as_senhas`, `test_plt_08_entrar_com_limite_por_ip_e_por_email` e `test_plt_08_convite_e_renovar_com_limite_por_ip`.
- P-04: `test_plt_01_subdominio_de_schema_existente_recusado` (`information-schema`, `public`, `pg-catalog`, `pg-toast`, `pg-temp-1`), `test_plt_01_subdominio_de_schema_de_fora_do_giro_recusado` e `test_plt_01_criar_empresa_nao_reaproveita_schema`.

**Check:** ruff check, ruff format --check e mypy limpos. O pytest dá `280 passed, 71 xfailed` (os xfail são da T-011, T-013 e T-014). Rodei na imagem `giro-backend` com o worktree montado e `--entrypoint sh`, porque o entrypoint da imagem espera o host `db`. O banco foi o Postgres descartável na 55432, nas mesmas condições da T-010, numa rede Docker própria (`giro-t058`). Removi o container e a rede no fim.

**O que ficou de fora:**
- **Para o frontend:** a tela de login da plataforma não recebe mais o 400 "Informe o código do autenticador.", só o 401. E há um 429 novo, `muitas_requisicoes`, sem `tentar_de_novo_em`, só com segundos e `Retry-After`. A tela já manda os três campos juntos, então nada quebra.
- **Para o arquiteto:** mudei o contrato em `docs/api/plataforma.md` porque o relatório pedia (o 401 no lugar do 400 sem código, o 429 de senha e o 429 de limite). Confira. O formato `muitas_requisicoes` também vale para a T-011 (`/api/auth/entrar/`), que pode reusar `tentar_entrar` e `comum.limites`.
- **Para a segurança (resíduos):**
  1. O 429 do bloqueio só existe para e-mail cadastrado. Depois de 5 tentativas, ele mostra que a conta existe, mas a quantidade de tentativas é a mesma do limite.
  2. Quem tem a senha certa e erra o código ainda vê o 429 no 3º erro, e não no 5º. Isso revela que a senha estava certa, mas custa 3 tentativas a cada 15 minutos.
  3. Conta `desativado` ou com convite pendente continua recebendo 403 `usuario_inativo`, mas agora só depois de senha e código certos.
  4. A defesa a mais no model `Usuario` (recusar `perfil` no `public` real) não entrou.
  5. P-05 a P-09 seguem na T-011.
- **Para o devops:** o limite no proxy para `/api/*/auth/` e `/admin/login/` (S-17) continua com vocês. O Admin não tem throttle no Django, só o bloqueio por conta.

**Próximo passo para quem recebe:** a segurança confere P-01 a P-04 e fecha os achados. O qa pode usar o CA-010-18 e os testes acima. Quando o PR #39 (T-059) entrar na main, faço `git merge origin/main` nesta branch e rodo o check de novo.

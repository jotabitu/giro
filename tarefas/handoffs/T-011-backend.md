# T-011 · Contas: login, sessões e 2 etapas da empresa · backend → frontend, qa, seguranca, arquiteto, orquestrador

Parte 1 da T-011, como combinado com o Orquestrador em 09/10. Usuários e convite da empresa ficaram para a T-069, o modo suporte para a T-070 e a navegação do `eu` para a T-071.

**O que foi feito:**
- **Rotas da empresa** (`/api/auth/`, contrato `docs/api/contas.md`): `entrar`, `2fa/verificar`, `2fa/configurar`, `2fa/ativar`, `2fa/desativar`, `2fa/codigos-recuperacao`, `renovar`, `sair`, `eu` (GET e PATCH), `sessoes`, `sessoes/{id}/encerrar`, `sessoes/encerrar-outras`, `senha/trocar`, `senha/esqueci` e `senha/redefinir`. `entrar` tem os limites da T-063 (10 por minuto e 50 por hora, por IP e por e-mail); as outras, 30 por minuto por IP.
- **Sessões (ADR 0014):** `contas.Sessao`. Access e refresh levam o `sid`, e token sem `sid` não vale. A sessão acaba com 12 h sem uso no desktop e 30 dias no celular (`USR-06`), contados do último uso. A autenticação confere a sessão a cada requisição, com cache de 30 s que é apagado na revogação. A sessão grava o `jti` do refresh vigente: se chegar outro refresh da mesma sessão (reuso, roubo ou dois `renovar` ao mesmo tempo), a sessão inteira é revogada (**P-07**). A plataforma usa as mesmas sessões. Toda revogação gera o evento `sessao.encerrar`.
- **2 etapas:** `contas.Autenticador` (TOTP com a semente cifrada por `GIRO_CHAVE_SEGREDOS`, com dado associado à linha) e `contas.CodigoRecuperacao` (só o HMAC por empresa, de uso único), no lugar do `otp_totp` e do `otp_static`, que saíram do `INSTALLED_APPS` (**P-08**). O Django Admin continua com 2 etapas: o `Autenticador` é um `Device` do django-otp.
- **Quem precisa:** `exige_2fa` vale para a plataforma, para administrador e financeiro, para todos quando `exige_2fa_todos` está ligado, e para quem ativou por conta própria (`USR-02`). `exige_2fa_pela_regra` é o `dois_fatores.obrigatorio` do `eu`, e quem é obrigado não desliga.
- **P-05:** com o convite aceito, a senha sozinha só cadastra o primeiro autenticador dentro do prazo do convite. Depois disso, responde 403 `convite_expirado`, tanto na empresa quanto na plataforma.
- **Bloqueio:** na empresa, 5 tentativas erradas, somando senha e código, bloqueiam por 15 minutos (429 `USR-06`). O evento `seguranca` é gravado e os administradores recebem um e-mail (`contas_avisar_bloqueio`). A plataforma continua com 5 senhas ou 3 códigos (`PLT-08`).
- **`pode`:** segue a tabela do contrato, e as permissões extras só somam (`USR-03`). Ficou registrado em `comum.permissoes.pode`. Para a T-069 já existe `selectors.extra_e_padrao_do_perfil`.
- **Senha:** os validadores (`apps/contas/senhas.py`) respondem textos prontos. A senha precisa de 12 caracteres ou mais, com letras e números, não pode ser o e-mail nem o nome da empresa e não pode estar na lista de senhas comuns. Isso vale também para a plataforma. O "Esqueci a senha" responde 202 sempre, aceita 3 pedidos por e-mail por hora, e o link vale 1 hora, uma vez só. O link sai como `/entrar/redefinir#<token>` (T-072). Redefinir encerra todas as sessões, e as 2 etapas continuam valendo.
- **`ConfiguracaoEmpresa`** (app `empresas`, aprovada pelo Arquiteto): uma linha só, criada junto com a empresa, por enquanto só com `exige_2fa_todos`. O serviço `definir_exige_2fa_todos` é auditado em `seguranca`. Não tem rota HTTP: ela sai com o contrato de configurações.
- **R-06:** `registrar_evento` recusa `antes`/`depois` sem objeto e recusa model que não é do Giro (django-otp, blacklist).
- **Bug corrigido:** um cookie de refresh malformado dava 500 em `renovar`, porque o backend do simplejwt levanta `TokenBackendError`. Agora responde 401 `nao_autenticado`.

**Onde:** `backend/apps/contas/` (`api/acesso.py`, `sessoes.py`, `selectors.py`, `senhas.py`, `dois_fatores.py`, `models.py`, `services.py`, `tasks.py`, migração `0005`), `backend/apps/empresas/` (models, services, selectors, eventos, migração `0001`), `backend/comum/autenticacao.py` (`registrar_sessoes`, `sid`, `JWTPre2FAOuAcesso`), `comum/permissoes.py` (`pode` e `resumo_das_filiais` registráveis), `comum/empresa.py` (`exige_2fa_todos`), `comum/auditoria.py` e os READMEs de contas, empresas e filiais.

**Contrato:** `docs/api/openapi.yaml` regerado. A mudança só acrescenta rotas e não muda nenhuma das existentes, e o gerador não dá aviso. Há quatro pontos fora do `contas.md` para o Arquiteto conferir:
1. `2fa/ativar` devolve, além de `codigos_recuperacao`, um `access` novo e grava um cookie novo, os dois com `otp` na mesma sessão. Sem isso, o próximo uso de quem acabou de ativar daria `2fa_obrigatorio`.
2. `MotivoRevogacao` ganhou `senha_alterada` e `refresh_reusado`.
3. `GET /sessoes/` mascara IPv6 pelo /64. O IPv4 continua no /24.
4. A tabela da ADR 0011 e o `modelo-de-dados.md` ainda citam `otp_totp` e `otp_static`. O certo agora é `contas.Autenticador` e `contas.CodigoRecuperacao`.

**Regras e testes:** `tests/aceitacao/test_t011_contas.py` e `tests/aceitacao/test_t011_seguranca.py`.
- Passam: CA-011-03 a 13, 19, 20, 21, 25 e 28 (parte de login).
- O CA-011-12 cobre só o mecanismo: o token sem `otp` cai quando o perfil passa a exigir 2 etapas. A rota e a auditoria `usuario.alterar_perfil` são da T-069.
- O CA-011-28 cobre login, falha, bloqueio e troca de senha. Os eventos de perfil, filiais, permissões, desativação e redefinição das 2 etapas entram com a T-069.
- Testes de segurança: `test_plt_08_configurar_2fa_recusado_depois_da_validade_do_convite`, `test_usr_02_configurar_2fa_recusado_depois_da_validade_do_convite` (P-05), `test_usr_04_refresh_reusado_revoga_a_sessao` (P-07), `test_plt_08_semente_e_codigos_de_recuperacao_nao_ficam_em_claro` (P-08), `test_aud_01_evento_sem_objeto_nao_leva_antes_nem_depois` e `test_aud_01_model_de_terceiro_nao_entra_na_auditoria` (R-06).
- Testes obrigatórios da ADR 0014: `test_aud_01_troca_de_senha_nao_grava_hash` e `test_usr_04_revogar_as_sessoes_derruba_o_access_na_proxima_requisicao`.
- Outros: `test_sessao_da_empresa_a_nao_vale_na_empresa_b` (isolamento), `test_renovar_com_cookie_invalido_responde_401` e `test_usr_02_configuracao_nasce_com_a_empresa`.

**Critérios que ficaram para outras tarefas:**
- **T-069:** CA-011-01, 02, 14, 15, 16, 17, 18, 22, 23 e 24, mais a rota do CA-011-12 e o resto do CA-011-28. Estão marcados `xfail` com "T-069".
- **T-070:** CA-011-26 e 27, marcados `xfail` com "T-070".

**Check:** ruff check, ruff format --check e mypy limpos. Depois do merge com a `origin/main` (2120ac8), o pytest dá `315 passed, 56 xfailed, 2 xpassed`. Os 2 xpassed são `xfail` não estritos que a T-072 pôs em `test_t058_seguranca.py` para as rotas novas do convite. Eles não vêm desta tarefa. O `makemigrations --check` não acusa nada. Rodei no Postgres descartável (porta 55432).

**O que ficou de fora:**
- Tudo de usuários e convite da empresa vai para a T-069: P-06, P-09 (contrato pronto na T-072, inclusive a migração da rota da plataforma para `consultar/` e `aceitar/` com o token no corpo; o teste de P-05 da plataforma usa a rota antiga e precisa mudar junto), `Lower(email)` único, F-03, `X-Filial: todas` para o financeiro e `pode_escolher_todas`, e `relatorios_todas_filiais` só em painel e relatórios.
- Modo suporte (T-070) e navegação do `eu` (T-071). Hoje o `eu` devolve `suporte: null` e não traz `navegacao`.
- As sementes que já estavam no `otp_totp` não foram copiadas. Não há ambiente com dados reais, e quem já tinha 2 etapas no ambiente de desenvolvimento configura de novo no próximo login.

**Para a Seguranca revisar:**
- Convite pendente que ainda não foi aceito recebe 403 `convite_pendente` sem conferir a senha, porque o CA-011-07 pede essa resposta e a pessoa nem tem senha. Isso revela que aquele e-mail tem um convite aberto.
- Dois `renovar` ao mesmo tempo com o mesmo cookie (duas abas) derrubam a sessão, como o P-07 sugeriu.
- A conta do `createsuperuser` sem autenticador continua cadastrando o primeiro autenticador só com a senha, porque está `ativo`.

**Para o Arquiteto:** o contrato pede 30 por minuto por IP nas rotas de `auth/`, e isso inclui `eu` e `sessoes`. Num escritório com várias pessoas atrás de um IP só, o limite pode estourar. Uma saída é contar as rotas logadas por usuário. Mantive o que está no contrato.

**Próximo passo para quem recebe:**
- **Frontend:** o login da empresa já é real: `etapa` `pronto`, `verificar_2fa` ou `configurar_2fa`, o cookie e o `X-Requested-With: giro` em `renovar` e `sair`. O `eu` traz `pode`, `dois_fatores` e `empresa`. Em `2fa/ativar`, troque o access pelo que vier na resposta.
- **QA:** os CAs das T-069 e T-070 continuam `xfail` com o número da tarefa. Para tokens de administrador ou financeiro nos testes de outros módulos, use `emitir_tokens(usuario, AMR_SENHA_E_CODIGO)`. Foi o que mudei em `test_t012_filiais.py`, porque o administrador agora exige 2 etapas.
- **Seguranca:** conferir P-05, P-07, P-08 e R-06 e os três pontos acima.

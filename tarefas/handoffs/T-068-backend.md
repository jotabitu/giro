# T-068 · Correções de segurança da T-064 (filiais) · backend → seguranca, arquiteto, devops, qa, orquestrador

**O que foi feito** (F-01, F-02, F-04 e F-05 de `docs/seguranca/2026-10-09-t058-t012.md`):
- **F-01 · permissões:** `comum.permissoes.com_padrao(*extras)` devolve as permissões padrão da API (`IsAuthenticated`, `EmpresaOperando`, `EscopoDeFilial`) mais as da view. As rotas de administrar filial passaram a usar `com_padrao(exige_perfil("administrador"))`. Com a empresa suspensa, pausada ou cancelada, criar, editar, tornar matriz, desativar, reativar e confirmar feriados respondem 403 `empresa_sem_operacao`, e um `X-Filial` fora do escopo dá 403 `USR-07` também nessas rotas. Ler continua funcionando. O teste de arquitetura `tests/test_permissoes_das_rotas.py` percorre o urlconf da empresa e exige `EmpresaOperando` e `EscopoDeFilial` em todo método de toda view. As exceções ficam numa lista explícita, hoje só a documentação da API.
- **F-02 · "todas" × sem filial** (combinado com o Arquiteto): `filial_da_requisicao` nunca devolve `None`. Devolve a `Filial` do `X-Filial`, que continua aceitando só filial ativa do escopo, ou `TodasAsFiliais(ids)`. Os `ids` são **todas** as filiais da empresa, ativas e desativadas, porque a desativada ainda tem contas e histórico (`USR-07` corrigida na T-067 e `FIL-06`). Pessoa sem filial ativa e sem cabeçalho recebe 403 `USR-07` "Você não tem acesso a nenhuma filial", levantado pela função. `/filiais/minhas/` não chama a função e responde a lista vazia. Helper novo `filtrar_por_filial(queryset, request, campo="filial")`, que é o único caminho dos módulos. Um teste de arquitetura confere que nenhum app fora de `filiais` usa `filial_da_requisicao`.
- **F-04 · limite por IP:** sem IP do cliente, o limite por IP não se aplica e fica um aviso no log (`comum.limites`), em vez de todo mundo cair na mesma chave. Em IPv6, a contagem é pelo prefixo /64. O DevOps conferiu: em dev, `REMOTE_ADDR` é o IP do container do frontend (nunca vazio, então o limite por IP vale por um IP só). Na homologação, o proxy vai ser TCP, sobrescrever o `X-Forwarded-For`, com `GIRO_PROXIES_CONFIAVEIS=1` e `GIRO_REDES_PROXY` igual à sub-rede do proxy.
- **F-05 · CEP:** `CepPorUsuario`, 30 por minuto por usuário em `/api/enderecos/cep/{cep}/`. Acima disso, 429 `muitas_requisicoes`.

**Onde:** `backend/comum/permissoes.py` (`com_padrao`), `backend/comum/limites.py`, `backend/config/settings/base.py` (taxa `cep_usuario`), `backend/apps/filiais/selectors.py`, `backend/apps/filiais/api/views.py`, `backend/apps/filiais/README.md`, `backend/tests/test_permissoes_das_rotas.py` e `backend/tests/aceitacao/test_t068_seguranca.py`.

**Contrato:** a tabela "Interface interna" de `docs/api/filiais.md` ganhou `filtrar_por_filial`, `filial_da_requisicao` sem `None` e `com_padrao`, como o Arquiteto pediu; ele confere no PR. O OpenAPI gerado é igual ao `docs/api/openapi.yaml`.

**Regras e testes:**
- F-01: `test_plt_03_empresa_suspensa_nao_cria_nem_edita_filial` (suspensa, pausada e cancelada), `test_usr_07_x_filial_fora_do_escopo_recusado_nas_rotas_de_administrar` e `test_toda_view_da_empresa_tem_as_permissoes_padrao`.
- F-02: `test_usr_07_pessoa_sem_filial_recebe_403`, `test_usr_07_todas_inclui_filiais_desativadas` e `test_outros_apps_filtram_filial_so_por_filtrar_por_filial`.
- F-04: `test_limite_por_ip_sem_ip_nao_junta_todos` e `test_limite_por_ip_conta_ipv6_pelo_prefixo_64`.
- F-05: `test_busca_de_cep_com_limite_por_usuario`.

Conferi que os testes reproduzem os achados: com o código da main, 10 dos 11 falham. O que passa é o teste de que nenhum outro app usa `filial_da_requisicao`, que é preventivo, porque ainda não há app de baixo.

**Check:** ruff check, ruff format --check e mypy limpos. O pytest dá `291 passed, 71 xfailed`. Rodei no Postgres descartável (porta 55432) e o removi no fim.

**O que ficou de fora:**
- F-03 (auditoria da troca de filiais da pessoa) fica na T-011, como o relatório distribui.
- Também na T-011: o financeiro com "todas" (já registrado como "Também"). E quem tem `relatorios_todas_filiais` só recebe "todas" em painel e relatórios: a view marca isso e `EscopoDeFilial` lê. Está anotado no README de filiais.
- O aviso ao dono quando uma conta da equipe é bloqueada e a trava no model `Usuario` são resíduos sem prazo.

**Próximo passo para quem recebe:**
- **Seguranca:** conferir F-01, F-02, F-04 e F-05.
- **T-013 em diante:** declarar permissões com `com_padrao(...)` e filtrar com `filtrar_por_filial`. Os dois testes de arquitetura pegam quem esquecer.
- **DevOps:** levar para a homologação a configuração descrita acima.

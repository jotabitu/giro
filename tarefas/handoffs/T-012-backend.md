# T-012 · Filiais · backend → frontend, qa, arquiteto, orquestrador

**O que foi feito:**
- `filiais`: `Filial`, `FeriadoFilial` e `UsuarioFilial`, com serviços, selectors e API no contrato `docs/api/filiais.md` (já corrigido na T-055).
- **Cadastro (FIL-01):** a primeira filial é sempre matriz e quem a criou fica ligado a ela. O nome é único sem diferenciar maiúsculas (409 `filial_nome_em_uso`) e só existe uma matriz: o banco tem restrição única e `tornar-matriz` trava as filiais, então duas chamadas simultâneas não deixam duas matrizes.
- **Limite do plano (PLT-03):** `exigir_limite` e `atualizar_uso` na mesma transação do cadastro e da reativação; a filial registra o contador `filiais` para o recálculo noturno. A lista traz `plano` (`usado`, `limite`, `aviso`, `bloqueado`, `nome_plano`).
- **Feriados (FIL-03):** sugestões dos nacionais de lei, com a Sexta-feira Santa pela Páscoa; nada vale antes da confirmação (decidido com o Arquiteto, o contrato já diz isso). `esta_aberta` e `proxima_abertura` contam feriado como dia fechado (base do `LOC-11`).
- **Escopo (USR-07):** `GET /api/filiais/minhas/`; o cabeçalho `X-Filial` é conferido em toda requisição da empresa por `comum.permissoes.EscopoDeFilial`, que entrou nas permissões padrão. Fora do escopo, ou `todas` para quem não é administrador, responde 403 `USR-07`. Sem o cabeçalho, `filial_da_requisicao` usa a matriz ou a primeira filial da pessoa.
- **Desativar (FIL-06):** responde 422 com todos os impedimentos de uma vez (`matriz`, `ultima_filial`, `operacao`). A operação vem dos contadores que `veiculos`, `locacoes` e `financeiro` vão registrar em `comum.leituras`; contador ausente vale 0. Os vínculos das pessoas ficam guardados e a desativação vai para a auditoria com o motivo.
- **Busca de CEP:** `GET /api/enderecos/cep/{cep}/` em `backend/integracoes/cep/` atrás de uma interface, com implementação falsa (CEPs do seed) e ViaCEP. O provedor é escolhido por `GIRO_PROVEDOR_CEP` (padrão `falso`). A resposta fica 30 dias em cache; falha do provedor não entra no cache.
- **`comum/leituras.py` (ADR 0015):** registro de anotações de leitura e de contadores por objeto, usado acima.

**Onde:** `backend/apps/filiais/` (models, migração 0001, calendario, services, selectors, eventos, apps, api/), `backend/comum/leituras.py`, `backend/comum/permissoes.py`, `backend/comum/erros.py` (`NaoEncontrado` 404), `backend/integracoes/cep/`, `backend/config/` (urls e settings), `backend/tests/aceitacao/test_t012_filiais.py`, `docs/api/openapi.yaml`.

**Contrato:** `docs/api/filiais.md` e `docs/api/openapi.yaml`.

**Regras cobertas:** FIL-01, FIL-02, FIL-03, FIL-06, PLT-03, USR-07 e a base do LOC-11. Os 17 critérios de `docs/qa/criterios/T-012.md` saíram de `xfail` e passam (18 testes: o CA-012-07 tem um a mais, com duas conexões de verdade disputando a matriz), mais `apps/filiais/tests/test_calendario.py` e `comum/tests/test_leituras.py`.

**Check:** ruff check, ruff format --check e mypy limpos; pytest com `258 passed, 71 xfailed` (os xfail são da T-011, da T-013 e da T-014). Os avisos são só `InsecureKeyLengthWarning` da chave curta de `config/settings/test.py`, anteriores a esta tarefa. Rodei depois do merge da main 504ba9b, contra o Postgres descartável, com o mesmo comando da T-010 (`tarefas/handoffs/T-010-backend.md`: `postgres:16` na porta 55432, `infra/postgres` montado, senhas só na linha de comando). Removi o container no fim (`docker rm -f giro-backend-teste-db`).

**Decisões de implementação (Arquiteto, confira):**
1. O GET do detalhe da filial vale para quem tem a filial no escopo; fora do escopo responde 404. As ações de administrar (lista, criar, editar, matriz, desativar, reativar, feriados) são só do administrador e respondem 403 aos demais. Assim os outros perfis veem `feriados_proximos` e os gerentes, como diz a seção de feriados do contrato.
2. Campos opcionais de texto (CNPJ, inscrições, contato, complemento) ficam vazios no banco e saem `null` na API.
3. A lista é paginada por `nome` (o cursor usa só o primeiro campo da ordem).
4. Os feriados nacionais sugeridos são os 10 de lei. Carnaval e Corpus Christi são ponto facultativo e entram como feriado local, se a filial fechar.
5. `X-Filial: todas` vale só para o perfil administrador. A permissão extra `relatorios_todas_filiais` (USR-03) entra com a T-011.

**O que ficou de fora:**
- **S-12** (SVG do logo): é do `ConfiguracaoEmpresa.logo`, não da filial. O Orquestrador moveu a nota para a tarefa da marca da empresa.
- **Indicadores** `veiculos`, `locacoes_ativas` e `ocupacao_pct` da lista: saem `null` até a T-013 e a T-015 registrarem as anotações; `usuarios` já vem da própria filial.
- **Contadores de operação** (veículos, locações, caixa): nesta tarefa o veto foi testado com contadores falsos. Com os módulos reais, o teste se repete na T-013, na T-015 e na T-017. O CA-012-16 (conta em aberto não impede) foi testado da mesma forma e precisa ser conferido de novo com o financeiro real na T-017.
- **Evento `contas.filiais_do_usuario_definidas`:** o assinante está pronto, mas quem publica é a T-011 (convite e edição de usuário).
- **Marcar o passo `filial`:** a criação marca o passo sempre, e não só no assistente (Onboarding-Filial). A operação pode ser repetida sem efeito.

**Próximo passo para quem recebe:**
- Frontend: as telas Filiais, Filial e o seletor de filial podem usar a API real. Mande `X-Filial` nas requisições depois que a pessoa escolher uma filial.
- QA: os testes da T-012 estão preenchidos e sem `xfail`. Atualize `docs/qa/cobertura-de-regras.md`.
- T-013, T-015 e T-017: registrem os contadores `veiculos`, `locacoes` e `caixas` e as anotações de indicadores em `comum.leituras` (ver `apps/filiais/README.md`).

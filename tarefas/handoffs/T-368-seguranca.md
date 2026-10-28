# T-368 · Antes de produção no backend (T-159 e T-160) · segurança → orquestrador, frontend

Feita pela segurança no lugar do Backend, que está com a fila cheia.

**O que foi feito:**
- **T-159 (USR-06):** o login (`POST /api/auth/entrar/`, `apps/contas/api/acesso.py`) não revela mais quem foi convidado.
  - Quem não existe e quem ainda não tem senha (convite pendente, ou reativado para convite pendente, USR-04) recebem o mesmo 401 `credenciais_invalidas`.
  - Os dois passam pelo mesmo cálculo de hash, então a resposta leva o mesmo tempo. O evento `usuario.entrar_falhou` grava o motivo `sem senha`, e quem não existe continua com `e-mail`.
  - O 403 `convite_pendente` só sai depois da senha certa, para quem tem senha e ainda não aceitou o convite. A senha errada desse caso conta no bloqueio da USR-06, como a de qualquer conta.
- **T-160 (S-17):** `config/settings/prod.py` deixa em `DEFAULT_RENDERER_CLASSES` só o `comum.renderizacao.JSONRenderer`. O resto do `REST_FRAMEWORK` de `base.py` continua valendo. Desenvolvimento e testes mantêm a API navegável.
- **Contrato:** `docs/api/contas.md`, na rota `entrar`, descreve o 401 de quem ainda não criou a senha e o 403 `convite_pendente` só depois da senha certa. O OpenAPI não muda, porque os códigos de resposta são os mesmos.

**Testes:**
- `test_usr_06_convite_pendente_nao_revela_email`: e-mail inexistente e convidado sem senha têm a mesma resposta e o mesmo hash. Com senha e o convite não aceito, senha errada dá 401 e senha certa dá 403.
- `test_t160_prod_sem_a_api_navegavel_do_drf`: sobe o `prod.py` num processo limpo e confere a lista.
- Ajustados para o comportamento novo: `test_usr_04_ca_011_07_quem_nao_pode_entrar` (João sem senha: 401) e a senha velha da reativação em `test_t011_contas.py` (401).
- `test_producao.py` com `test_t011_contas.py`: 118 passed.
- Regressão de `tests/`, `apps/contas`, `apps/plataforma` e `comum`: 1587 passed, 7 skipped, 7 xfailed e 1 failed. A falha foi `test_adr_0026_filho_so_com_path_e_lang_e_os_limites` (leitura do CRLV, limite de 5 s de CPU no processo filho), no fim de uma rodada de 65 min com a máquina carregada. Sozinho, passou. Não tem relação com esta tarefa.
- ruff, ruff format e mypy: sem erro.

**Para o frontend:** o login não recebe mais o 403 `convite_pendente` de quem não tem senha. Se a tela tinha mensagem própria para ele, ela continua valendo só no caso raro de quem tem senha e não aceitou o convite. Nada a mudar.

**Próximo passo:** o orquestrador revisa e abre o PR. Sigo na T-369.

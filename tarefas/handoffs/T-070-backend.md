# T-070 · Modo suporte · backend → frontend, qa, seguranca, arquiteto, orquestrador

**O que foi feito:**
- **`plataforma.AcessoSuporte`** (migração `plataforma/0006`): motivo, permissão (`ver` ou `ver_editar`), início e fim de 15, 30 ou 60 minutos. O status segue a máquina `ativo` → `encerrado` ou `revogado`. Valem `CHECK (fim > inicio)` e os índices do modelo de dados. O campo `chamado` ficou de fora, porque o model `Chamado` ainda não existe.
- **Abrir o acesso:** `POST /api/plataforma/empresas/{id}/acessos-suporte/`, para quem tem a permissão `entrar_como_suporte`.
  - Devolve `url_entrada` com o token no fragmento (`/suporte/entrar#<token>`).
  - Responde 422 `PLT-07` quando a empresa bloqueou o suporte.
  - Os administradores ativos recebem um e-mail depois do commit, com o nome de quem entrou, a permissão, o fim e o motivo.
- **Token `suporte`** (ADR 0013, item 2, em `comum.autenticacao`): não tem refresh nem `user_id` e vence no `fim`. A cada requisição, o acesso é conferido no `public`: tem de estar `ativo`, no prazo, ser da mesma empresa e a empresa não pode ter o suporte bloqueado. Qualquer falha responde 401 `PLT-07`, "O acesso de suporte terminou".
  - A autenticação monta um `AtorSuporte` em memória, sem `contas.Usuario`, com o alcance de um administrador em todas as filiais.
  - Na auditoria da empresa, o ator aparece como `suporte`, com `acesso_suporte_id` e sem `ator_id`.
- **Regras de rota.** É a própria view que decide:
  - `suporte_somente_leitura = True` libera a leitura no modo "só ver". Sem essa marca, ou com escrita, a resposta é 403 `PLT-07`, "No modo só ver você não pode fazer isto".
  - `suporte_proibido` responde 403 `PLT-07` mesmo com "ver e editar". Vale para:
    - as rotas da conta (sessões, senha e 2 etapas);
    - a escrita de usuários (incluindo convidar, desativar e as sessões de outra pessoa);
    - o `PATCH` do `eu`;
    - o controle do suporte (o suporte não se libera).
  - As rotas públicas (entrar, renovar, sair, senha e convite) e as da plataforma recusam o token de suporte com 403 `PLT-07`.
- **Lista "só ver"**, conferida por `test_plt_07_lista_de_rotas_que_o_suporte_le`: `auth/eu/`, `usuarios/`, `usuarios/{id}/`, `assinatura/`, `filiais/minhas/`, `filiais/`, `filiais/{id}/`, `filiais/{id}/feriados/`, `feriados/sugestoes/` e `enderecos/cep/`. Cada módulo novo marca as suas views de leitura. Exportação, URL assinada e dado pessoal completo ficam de fora.
- **`GET /api/auth/eu/` com o token de suporte:** devolve `suporte` (`acesso_suporte_id`, `nome`, `permissao`, `fim`, `motivo`), `perfil: "administrador"`, `id: null`, todas as filiais e o `pode`. No modo "ver", o `pode` mantém só `painel`, `veiculos` e `administracao`, e o resto vem desligado.
- **`POST /api/auth/suporte/sair/`:** o acesso vai para `encerrado`. Quem não é suporte recebe 403 `PLT-07`.
- **Controle do administrador**, no host da empresa: `GET /api/suporte/` (bloqueio e acessos dos últimos 90 dias), `POST /api/suporte/bloquear/` e `liberar/` (bloquear revoga na hora os acessos ativos) e `POST /api/suporte/acessos/{id}/revogar/`.
- **Auditoria:** entrar, sair, encerrar por prazo, revogar, bloquear e liberar vão para as duas auditorias, a da empresa e a do `public`, na categoria `suporte`, com o motivo (AUD-03).
- **AUT-15:** `aut_15_encerrar_acessos_de_suporte_vencidos` roda pelo Beat a cada minuto e é idempotente.
- O limite por usuário (CEP) conta o suporte pelo acesso, para não juntar todos os suportes na mesma chave `None`.

**Onde:** `backend/comum/autenticacao.py`, `comum/middleware.py`, `comum/limites.py`, `apps/plataforma/` (`models.py`, `services.py`, `tasks.py`, `apps.py`, `api/suporte.py`, `api/urls.py`, migração `0006`), `apps/contas/api/acesso.py`, `api/usuarios.py`, `api/plataforma.py`, `selectors.py`, `apps/filiais/api/views.py`, `config/settings/base.py` (Beat e o enum) e os READMEs de contas e plataforma.

**Contrato:** `docs/api/openapi.yaml` regerado com `--validate`, sem aviso, e só com acréscimos. Há quatro pontos para o Arquiteto conferir:
1. O contrato de contas diz que, com `ver`, o `pode` traz "só as chaves de leitura". Interpretei como `painel`, `veiculos` e `administracao`. A chave `veiculos` continua `editar`, porque não existe um valor só de leitura, e a tela usa a chave só para mostrar o menu.
2. `id` e `email` do `eu` vêm `null` no modo suporte. No OpenAPI, os dois passaram a aceitar `null`, e o `suporte` virou um objeto tipado.
3. `POST /api/suporte/acessos/{id}/revogar/` aceita `{ motivo? }` e devolve o item da lista. O contrato só diz "200".
4. A abertura do acesso é de fase 2 no `plataforma.md`. Ela entrou agora, como a tarefa pede, e por isso responde desde já.

**Regras e testes** (`tests/aceitacao/test_t011_contas.py`):
- `test_plt_07_ca_011_26_faixa_e_permissoes_do_suporte`: CA-011-26 inteiro, mais a escrita em "ver e editar" auditada com o ator `suporte`, o token de outra empresa (401) e as rotas da plataforma (403).
- `test_plt_07_ca_011_27_administrador_controla_o_suporte`: CA-011-27, com bloquear, liberar, sair, revogar e as duas auditorias.
- `test_aut_15_encerra_acessos_de_suporte_vencidos`.
- `test_plt_07_lista_de_rotas_que_o_suporte_le`.
- Não sobrou `xfail` de T-070.

**Check:**
- Ruff check, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `341 passed, 43 xfailed`, sem xpassed.
- Postgres descartável (`giro-backend-pg`), com `--rm` e `POSTGRES_HOST`.

**O que ficou de fora:**
- `AcessoSuporte.chamado`, porque não existe o model `Chamado` (suporte é fase 2).
- A tela da plataforma que abre o acesso. O backend está pronto.
- AUD-09 (CPF e CNH sempre mascarados para o suporte) é testada na T-014. Para isso o `AtorSuporte` tem `e_suporte = True`.

**Para a Seguranca revisar:**
- O token de suporte vale até o `fim` e é conferido no `public` a cada requisição, sem cache. Revogar ou bloquear derruba o acesso já na requisição seguinte.
- Para escolher o caminho da autenticação, `_tipo_do_token` lê o tipo do JWT sem conferir a assinatura. A conferência completa vem logo depois, com `TokenSuporte(bruto)`.
- O suporte nunca recebe 2 etapas próprias na empresa: o token vem do login da plataforma, que já exige o código (PLT-08).

**Próximo passo para quem recebe:**
- **Frontend:**
  - página `/suporte/entrar#<token>`: ler o fragmento e limpá-lo, como no convite;
  - faixa "Modo suporte" sempre que `eu.suporte` não for `null`;
  - em 401 `PLT-07`, mostrar "O acesso de suporte terminou";
  - tela de Administração com `GET /api/suporte/`, bloquear, liberar e revogar.
- **Backend (módulos novos):** marcar `suporte_somente_leitura = True` nas views de leitura, sem exportação nem URL assinada, e atualizar a lista do teste `test_plt_07_lista_de_rotas_que_o_suporte_le`.
- **DevOps:** o Beat ganhou `aut_15_encerrar_acessos_de_suporte_vencidos`, que roda a cada minuto.

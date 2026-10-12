# T-018 · Tela e consulta da auditoria · backend → frontend, qa, arquiteto, produto

**O que foi feito:** consulta da auditoria da empresa (Admin-Auditoria) e da plataforma (Plat-Auditoria), com filtros que combinam, textos prontos (`resumo`, `detalhe`), destaque do suporte e escopo por schema; exportação da auditoria em CSV com fila, e-mail, link 302 de 15 minutos e 410 depois de 7 dias; backup completo pedindo 2 etapas confirmadas há no máximo 15 minutos.

**Onde:**
- `backend/apps/auditoria/`: `selectors.py` (filtros, representação, pessoas), `textos.py` (frases de cada ação), `services.py` e `tasks.py` (exportação), `api/`, model `Exportacao` e migração `0004` (também troca `ocorrido_em` para o relógio do domínio, sem mudar o banco).
- `backend/apps/plataforma/auditoria.py` e `api/auditoria.py`: auditoria da plataforma (empresa de cada evento, filtro `?empresa=`, indicadores), permissão `SoDono`.
- `backend/comum/auditoria.py`: `registrar_formatador` e `registrar_consulta` (filiais, acessos de suporte e e-mails, registrados por `filiais`, `plataforma` e `contas`).
- `backend/comum/autenticacao.py`: claim `auth_time` só no login completo com código (não vai na rotação).
- `backend/comum/arquivos.py`: `apagar_temporario` (só para exportação vencida); `comum/erros.py`: `Expirado` (410).
- `backend/config/settings/base.py`: nomes fixos dos enums novos (nenhum enum existente mudou de nome no OpenAPI).

**Contrato:** `docs/api/auditoria.md`; OpenAPI em `docs/api/openapi.yaml` (só acrescenta componentes). Rotas: `GET /api/auditoria/eventos/`, `/{id}/`, `/api/auditoria/pessoas/`, `GET|POST /api/exportacoes/`, `GET /api/exportacoes/{id}/baixar/`, `GET /api/plataforma/auditoria/eventos/` e `/{id}/`.

**Regras cobertas:** AUD-01, AUD-02, AUD-03, AUD-07, AUD-09, PLT-07, PLT-08, PLT-09. Testes em `backend/tests/aceitacao/test_t018_auditoria.py`, um por critério (CA-018-01 a 16, 18 testes, todos passando), com o código da regra no nome.

**Conferido antes do push:** ruff, ruff format, mypy, `makemigrations --check`, os testes da T-018 e os afetados um arquivo por vez (comum: auditoria, arquivos, tarefas; tests: rotas, permissões das rotas, limites entre apps, campos sensíveis, formato das datas, autenticação, isolamento, fundação; aceitação T-010, T-011, T-011 segurança, T-012, T-014, T-058, T-068; apps plataforma e contas). No frontend, `npm run api:gerar` e `npm run typecheck` sem erro.

**Decisões de implementação (Arquiteto, confira):**
1. Formatadores: a auditoria traz os textos das ações que já existem (`textos.py`), lendo só o próprio evento; o app dono pode registrar o seu com `registrar_formatador` e ele passa na frente.
2. `ocorrido_em` passou de `auto_now_add` para o relógio do domínio (`comum.relogio`), como o resto da API; em produção é o mesmo `timezone.now()`.
3. Período: `7d|30d|90d` vai do começo do dia (fuso da empresa) até agora; `de`/`ate` são datas inclusivas.
4. No evento, `ator.nome` é "Sistema" ou "Suporte Giro" para esses tipos, e o atendente vai em `suporte.atendente`; `objeto.tipo` é o nome do model (`caixa`, `locacao`, `acessosuporte`).
5. Auditoria da plataforma: permissão própria `SoDono` (403 `PLT-09`) em vez de criar chave nova no `pode`, para não mudar o `eu`. Escrita responde 405 (não 404 como as rotas de fase 1).

**O que ficou de fora (no backlog):**
- `[divergência]` CPF e CNH cifrados saem `{"alterado": true}` (ADR 0014), não mascarados como no CA-018-06 e no contrato.
- `[decisão]` exportação: os outros itens, `planilha` e `zip` respondem 422 `exportacao_indisponivel`; exportação da plataforma (`/api/plataforma/exportacoes/`) e backup automático (`AUT-11`) também.
- `[divergência]` a T-017 grava `movimento_caixa.sangria` sem filial; o contrato diz `caixa.sangria` com o caixa. A auditoria escreve o texto certo para as duas.
- Ator "Desconhecido" para login bloqueado de e-mail que não existe na plataforma (CA-018-14): hoje esse caso não grava evento; fica com o login da plataforma.
- Exportar com a empresa suspensa: a tarefa aceita, mas o `POST` ainda passa pelo `EmpresaOperando` (403); decidir junto com a `AUD-08`.

**Próximo passo para quem recebe:**
- **Frontend:** telas `Admin-Auditoria` e `Plat-Auditoria` exibem `resumo`, `detalhe`, `ator.iniciais` e o bloco `suporte` como vêm (linha em destaque quando `suporte` não é nulo); filtro "Pessoa" de `/api/auditoria/pessoas/` (usuário vai em `?ator=`, Sistema e Suporte Giro em `?ator_tipo=`). O backup completo pede login com código há no máximo 15 minutos: o 403 `2fa_recente` leva a pessoa a entrar de novo com o código.
- **QA:** conferir na tela os 9 eventos do CA-018-09 quando o seed tiver o financeiro (T-017).
- **Produto e arquiteto:** as três entradas da T-018 no backlog.

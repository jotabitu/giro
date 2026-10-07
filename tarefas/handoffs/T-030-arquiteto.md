# T-030 · Contratos da API de plataforma e filiais · arquiteto → backend, frontend, orquestrador

**O que foi feito:**
- `docs/api/README.md`: convenções comuns de todos os contratos (endereços, ações de status por `POST .../<acao>/`, autenticação, formatos, envelope de lista com cursor e `contagens`, tabela de erros 400 a 429).
- `docs/api/plataforma.md`: autenticação da equipe com 2 etapas e convite, planos, lista e detalhe de empresas (com `situacao` decidida pela API), criação de empresa (serviço na fase 1, endpoint na fase 2), ações sobre a empresa, entrar como suporte, equipe interna, `GET /api/assinatura/` do lado da empresa e a interface interna `exigir_limite`/`atualizar_uso` (`PLT-03`) usada pelos outros apps. Cada endpoint marcado como fase 1 ou fase 2.
- `docs/api/filiais.md`: seletor `GET /api/filiais/minhas/` com cabeçalho `X-Filial` (`USR-07`), CRUD do administrador, `tornar-matriz`, `desativar`/`reativar`, consulta de CEP e a interface interna (`esta_aberta` para `LOC-11`).
- Revisão de segurança (T-032), feita nesta branch como o orquestrador pediu: ADR 0013 (S-01 a S-04, S-08) e ADR 0014 (S-05, S-06, S-07, S-13); modelo de dados atualizado (Cliente cifrado com hash único, `Sessao`, `UsoEmpresa`, campos de `Empresa` e `Filial`, regra de segurança dos modelos de contrato S-09).

**Onde:** `docs/api/README.md`, `docs/api/plataforma.md`, `docs/api/filiais.md`, `docs/decisoes/0013-*.md`, `docs/decisoes/0014-*.md`, `docs/decisoes/modelo-de-dados.md`, `docs/decisoes/README.md`, `tarefas/backlog.md`.

**Regras cobertas:** PLT-01, PLT-03, PLT-04, PLT-07, PLT-08, PLT-09, IMP-05, USR-07, LOC-11 (horário da filial).

**O que ficou de fora:**
- Indicadores por filial (veículos, locações, ocupação) da tela `Filiais`: vêm de `GET /api/relatorios/filiais/`, num contrato de relatórios futuro, porque `filiais` não pode depender de `veiculos`/`locacoes` (ADR 0011).
- `GET /api/plataforma/empresas/{id}/atividades/`: descrito, mas depende de nova conferência da segurança antes de implementar.
- Campos da tela `Filial` sem regra e a regra de desativação com operação: `[decisão]` no backlog para o produto.
- Divergências de dados de exemplo nas telas da plataforma: no backlog, para T-028.
- S-09 (marcadores fechados e `url_fetcher`) vai em detalhe no contrato da T-015; a restrição já está no modelo.

**Próximo passo para quem recebe:**
- Backend: T-010 implementa só o que está marcado "fase 1" em `plataforma.md`; T-012 implementa `filiais.md` inteiro. ADRs 0013 e 0014 entram em T-001 (cripto, campos, classificação da auditoria, serializers de token) e T-011 (sessões, 2 etapas, suporte).
- Frontend: pode montar login da plataforma, seletor de filial e telas de filiais com dados falsos a partir destes contratos.
- Orquestrador: próximos contratos que destravam a fase 1 são `contas.md` (T-011), `veiculos.md` (T-013) e `clientes.md` (T-014).

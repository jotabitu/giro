# T-006 · ADRs iniciais revisadas e modelo de dados · arquiteto → orquestrador, backend

**O que foi feito:**
- Revisão das ADRs 0001 a 0007: continuam válidas; as lacunas viraram ADRs novas (tabela "Revisão de 07 out 2026" em `docs/decisoes/README.md`). Corrigida a linha da 0007 que estava fora da tabela do índice.
- ADRs novas: 0008 (usuários e autenticação por schema), 0009 (fundação `backend/comum/`), 0010 (auditoria imutável), 0011 (apps, ordem de dependência, eventos, app novo `contratos`), 0012 (Celery por empresa sem biblioteca nova).
- `docs/decisoes/modelo-de-dados.md`: as 25 entidades com app dono, schema, campos, índices e restrições, mais as entidades de apoio e o resumo de restrições de integridade.

**Onde:** `docs/decisoes/0008` a `0012`, `docs/decisoes/README.md`, `docs/decisoes/modelo-de-dados.md`, `tarefas/backlog.md` (dúvidas `[decisão]`).

**Decisões que afetam o backend já em T-001:**
- `AUTH_USER_MODEL = "contas.Usuario"`, app `contas` em `SHARED_APPS` e `TENANT_APPS`; JWT com claim `schema` conferida em toda requisição (0008).
- `comum`: `ModeloBase`, `ModeloAtivavel`, `ModeloComCodigo` + `Sequencia`, `CentavosField`/`CentavosComSinalField`/`PercentualField`, `dinheiro.py` com `ROUND_HALF_UP`, `MaquinaDeEstados`, `ErroDeRegra` (422) / `TransicaoInvalida` e `Conflito` (409), `auditoria.py`, `eventos.py`, `tarefas.py`, `permissoes.py`, `arquivos.py` (0009).
- `auditoria.EventoAuditoria` nos dois schemas, com trigger que bloqueia `UPDATE`/`DELETE` (0010).
- Lista de `SHARED_APPS`/`TENANT_APPS` e teste de limites entre apps (0011).

**O que ficou de fora:**
- Contratos de API por módulo (`docs/api/<modulo>.md`): saem antes de cada tarefa do backend, começando por plataforma (T-010) e filiais (T-012).
- `backend/README.md` ainda não lista o app `contratos`; o backend acrescenta quando criar o app (T-015).
- Dúvidas para o produto, todas com proposta e sem bloquear a fase 1: status não listados nas regras, `cancelada` na venda (VEN-07), o que conta como "venda aberta", modo de arredondamento, chassi único.
- A segurança deve revisar: campos mascarados na auditoria (0010), guarda da chave da subconta Asaas (`plataforma.ContaPagamento.chave_api_cifrada`), token de suporte (0008).

**Próximo passo para quem recebe:** backend segue T-001 pelas ADRs 0008 a 0012; orquestrador pode liberar T-010 quando eu entregar `docs/api/plataforma.md`.

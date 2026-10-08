# T-050 · Revisão de segurança do código da T-033 · seguranca → orquestrador, backend, devops, qa

**O que foi feito:** revisei a branch `t-033-dados-sensiveis` (PR #16) contra os itens 2 e 3 da ADR 0014, o item 3 da ADR 0018, S-05, S-06 e S-07 (T-032) e C-01 e C-02 (T-039). Rodei a suíte no container do meu worktree: 127 testes, verde. Confirmei R-01 e R-05 executando código (teste temporário, não commitado).

**Onde:** `docs/seguranca/2026-10-08-codigo-t033.md`.

**Resultado:** nenhum achado alto. A cifra AES-256-GCM com dado associado e `id_cifra`, as chaves separadas, o HMAC por empresa, a anonimização e a classificação da auditoria estão conforme a ADR e testados. C-01, C-02 e o ator da fila (ADR 0018) estão resolvidos. Ficaram 1 achado médio e 5 baixos:
- R-01 (média): dentro de `na_empresa` e de `@tarefa_de_empresa`, cifra e hash de busca levantam `ErroDeCifra`, porque `schema_context` põe na conexão um `FakeTenant` sem `pk`. Isso quebra a importação (T-017) e qualquer tarefa que toque `Cliente`, e convida a um contorno que mistura empresas. Sugestão: entrar com `tenant_context(empresa)`.
- R-02 a R-06 (baixas):
  - R-02: o teste de arquitetura não cobra `nome` nem `pagador`.
  - R-03: as chaves de exemplo do `.env.example` não têm trava em produção.
  - R-04: um ator `suporte` sem `acesso_suporte_id` é aceito.
  - R-05: `decifrar` de valor truncado dá `ValueError`, e `definir_` com o mesmo valor gera "alterado" falso.
  - R-06: `registrar_evento` sem objeto não passa pela classificação, e os models do `django_otp` ficam fora do teste.

**O que ficou de fora:** o `Cliente` real (T-014), `ContaPagamento` e o serializer, e `Sessao` (T-011). Não revisei esses pontos porque ainda não existem.

**Próximo passo para quem recebe:**
- Orquestrador: distribuir conforme a tabela no fim do relatório. R-01 deve entrar antes da T-017; cabe na T-034, que já mexe em `na_empresa`.
- Backend: R-01 e R-04 na T-034; R-02 e R-05 na T-014; R-06 na T-011.
- DevOps: R-03 na T-035.
- QA: manter `test_aud_06_auditoria_de_cliente_nao_guarda_nome_nem_documento_completos` como critério da T-014.
- O PR #16 pode seguir: nenhum achado bloqueia.

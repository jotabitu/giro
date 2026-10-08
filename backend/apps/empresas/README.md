# app `empresas`

**Schema:** empresa
**Escopo:** Dados da empresa, marca (cor, logo, nome), configurações gerais, assistente de implantação, integrações.
**Regras:** IMP (ver `docs/regras-de-negocio.md`)
**Telas:** Admin-Marca, Config, Integracoes, Onboarding-* (ver `docs/telas/README.md`)

## Estrutura esperada

```
empresas/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/empresas.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-011)

- `ConfiguracaoEmpresa` (uma linha só, `unica = 1`), por enquanto só com `exige_2fa_todos` (padrão `False`). Nasce com a empresa: o assinante de `plataforma.empresa_criada` em `eventos.py` cria a linha. Os outros campos do modelo de dados entram com a tela Config.
- `services.definir_exige_2fa_todos(valor)`, auditado em `seguranca` (`empresa.exigir_2fa_todos`, `USR-02`). Sem rota HTTP até sair o contrato de configurações.
- `selectors.exige_2fa_todos()`, registrada em `comum.empresa` no `ready()`: `contas` lê sem importar `empresas` (mesmo nível na ADR 0011). Sem a linha, `False`.

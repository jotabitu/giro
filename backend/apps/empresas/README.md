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

## Implementado (T-129)

- `ConfiguracaoEmpresa` ganha a marca (`nome_exibicao`, `logo` com `logo_largura` e `logo_altura`, `cor_marca` `#RRGGBB` com `CHECK`, vazio = padrão) e `meta_ocupacao_pct` (80,00).
- `marca.py`: cores derivadas calculadas na leitura (fórmula do design-system em `giro-produto/cores-da-marca.md`: WCAG para `cor_sobre`, OKLCH para `cor_suave` e `cor_suave_escuro`; valores fixos do `wl-theme.css` para a cor padrão) e iniciais.
- `selectors.marca()` (cache `marca:<schema>`, 1 hora), registrada em `comum.empresa` (`marca()` e `nome_da_empresa()`): convite, senha, `issuer` do 2FA, `eu` e contratos leem o nome por ela. `selectors.meta_ocupacao_pct()` para o painel.
- `GET /api/marca/` (ETag, 304, `max-age=300`) e `GET /api/marca/logo/` (cabeçalhos da S-12), públicas, 120 por minuto por IP (`comum.limites.MarcaPorIP`).
- Falta a escrita da marca (Admin-Marca e Onboarding-Marca, com a sanitização da S-12): o serviço de escrita apaga `selectors.chave_da_marca()` no `on_commit`.

# app `relatorios`

**Schema:** empresa
**Escopo:** Indicadores das telas iniciais, relatórios e DRE (só leitura, a partir dos outros apps).
**Regras:** FIN-13, relatórios (ver `docs/regras-de-negocio.md`)
**Telas:** Main, Dashboard, Pos-Dashboard, Relatorios, inícios por perfil (ver `docs/telas/README.md`)

## Estrutura esperada

```
relatorios/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/relatorios.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-129)

- `GET /api/painel/contadores/` e `GET /api/painel/inicio/` (`docs/api/painel.md`, "Rotas, perfis e o que entra no MVP"), em `config/urls.py`, sem depender de `relatorios` em `GIRO_MODULOS_ATIVOS`.
- `selectors.py`: `contadores(usuario, escopo, chaves)` e `inicio(usuario, variante, escopo, periodo, empresa)`, só a partir dos `selectors` dos outros apps. Regra do MVP: número só com fonte existente; senão `null` (caixa, despesas, manutenção, vendas, conciliação).
- A variante e as chaves dos contadores vêm de `contas.selectors.navegacao_de` (a mesma navegação do `eu`). O escopo (`Escopo`) sai de `filtrar_por_filial` na view.
- Cache por schema, pessoa, filial e rota (`painel:<schema>:<usuario>:<filial ou todas>:<rota>[:<periodo>]`): 5 min no início, 60 s nos contadores. Suporte: "só ver", variante do administrador.
- Quando a T-017 (caixa) e a despesa entrarem, cada uma liga o seu bloco aqui (`caixa_hoje`, `caixas_do_dia`, `sai_hoje`, `despesas`, `contas_a_pagar`, `para_hoje`) com o teste do seed.

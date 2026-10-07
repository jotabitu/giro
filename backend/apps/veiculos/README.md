# app `veiculos`

**Schema:** empresa
**Escopo:** Categorias e tabela de preços, veículos, documentos, leitura de km, histórico de status.
**Regras:** VEI (ver `docs/regras-de-negocio.md`)
**Telas:** Frota, Veiculo, Precos (ver `docs/telas/README.md`)

## Estrutura esperada

```
veiculos/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/veiculos.md` (escrito pelo arquiteto antes da implementação).

# app `plataforma`

**Schema:** public
**Escopo:** Planos, empresas (tenants), faturas da assinatura, usuários da plataforma, acesso de suporte, implantações e chamados.
**Regras:** PLT, IMP (ver `docs/regras-de-negocio.md`)
**Telas:** Plat-*, Plataforma, Compra-*, Admin-Assinatura, Admin-Cancelar (ver `docs/telas/README.md`)

## Estrutura esperada

```
plataforma/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/plataforma.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-010, fase 1)

- `models.py`: `Plano` (os três do seed na migração 0005), `Empresa` (máquina de estados, `transicao_empresa`), `Dominio`, `UsoEmpresa` (resumo no public).
- `services.py`: `criar_empresa` (Django Admin no MVP; schema, domínio, uso, auditoria e o evento abaixo numa transação), `validar_criacao`, `exigir_limite`, `atualizar_uso`, `registrar_contador`, `recalcular_uso`, `registrar_passo_implantacao`, `registrar_acesso`.
- `selectors.py`: `empresa_atual`, `uso_do_plano`, `assinatura`, `com_situacao` (a ordem da tabela de situação em uma anotação SQL), `filtrar_empresas`, `contagens_das_empresas`, `detalhe_empresa`.
- `permissoes.py`: tabela do PLT-09, `pode(funcao)` e `exige_permissao(...)` (403 `PLT-09`).
- `tasks.py`: `plataforma_avisar_limite_90` (e-mail aos administradores, uma vez por item e por mês) e `plataforma_recalcular_uso` (Beat, 03:30).
- `api/`: `GET /api/plataforma/planos/`, `/empresas/`, `/empresas/{id}/` (host admin) e `GET /api/assinatura/` (host da empresa). Método de fase 2 responde 404.

## Eventos publicados

| Evento | Quando | Dados |
| --- | --- | --- |
| `plataforma.empresa_criada` | `criar_empresa`, já no schema da empresa nova | `empresa_id`, `administrador` (`nome`, `email`, `celular`) |

## Para os outros apps

Ao criar, desativar ou reativar filial, veículo ou usuário: `exigir_limite(item)` e `atualizar_uso(item, ±1)` na mesma transação. No `ready()`, registre a contagem real com `registrar_contador(item, funcao)` (contas já registra `usuarios`).

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

## Implementado (T-070: modo suporte, PLT-07)

- `AcessoSuporte` (máquina `ativo` → `encerrado` ou `revogado`; `fim - inicio` de 15, 30 ou 60 min). Tudo do acesso roda em `schema_context(public)`, porque do host da empresa o `search_path` acharia a tabela de usuários da empresa.
- `services.py`: `abrir_acesso_suporte` (422 `PLT-07` com o suporte bloqueado; e-mail aos administradores depois do commit), `conferir_acesso_suporte` (registrada em `comum.autenticacao` no `ready()`), `sair_do_suporte`, `revogar_acesso_suporte`, `definir_bloqueio_do_suporte` (bloquear revoga os ativos na hora) e `encerrar_acessos_vencidos` (AUT-15). Cada fato vai para as duas auditorias; na da empresa, a entrada e a saída têm o ator `suporte` com o `acesso_suporte_id` (AUD-03).
- `api/suporte.py`: `POST /api/plataforma/empresas/{id}/acessos-suporte/` (função com `entrar_como_suporte`; a URL de entrada leva o token no fragmento) e, no host da empresa, `GET /api/suporte/`, `POST /api/suporte/bloquear/`, `liberar/` e `acessos/{id}/revogar/` (administrador; o suporte nunca usa).
- Tarefas: `plataforma_avisar_entrada_do_suporte` e `aut_15_encerrar_acessos_de_suporte_vencidos` (Beat, a cada minuto).

## Implementado (T-184: faturas da assinatura e conta principal)

Contrato: `docs/api/assinatura.md` ("Faturas, cobrança e régua", "De onde vem o endereço", "Tomador da fatura"); ADR 0023.

- `models.py`: `Empresa.email_cobranca`, `endereco_*`, `ciclo_proximo`, `dia_vencimento`; `FaturaAssinatura` (máquina `aberta` → `paga`, `atrasada`, `cancelada`; código `FAT-0001` por empresa, sequência `FAT-<empresa_id>` no public; uma mensalidade viva por competência; campos da nota, do tomador e do cancelamento); `FormaPagamentoAssinatura` (1:1, token do cartão cifrado, nunca na API nem na auditoria).
- `calendario.py`: `proximo_periodo`, `vencimento_seguinte` (mês sem o dia vence no último) e `descricao_da_fatura` (PLT-01, PLT-14), funções puras.
- `services.py`: `criar_empresa` cria a FAT-0001 (vence `teste_fim + 1`) e a forma vazia; `criar_fatura` (única porta), `criar_primeira_fatura`, `preco_no_ciclo`; `copiar_endereco_da_matriz` (chamado por `filiais.criar_filial`); `atualizar_pagador` (pagador na conta principal); `registrar_webhook_principal` e `processar_webhook_fatura` (baixa idempotente, consulta o parceiro, guarda o cartão só com a forma `cartao`); `gravar_tomador` (na baixa enquanto a NFS-e está desligada).
- `tasks.py`: `plataforma_processar_webhook_fatura` (tenta de novo com o parceiro fora) e `plataforma_pedir_notas_pendentes` (só conta enquanto a T-197 não existe).
- `admin.py`: faturas de todas as empresas só para leitura, com o filtro "nota pendente".
- O webhook (`financeiro/api/views.py`) procura a `ContaPagamento` pelo token; sem ela, confere o hash da conta principal (`GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH`) e grava o aviso no public.

## Eventos publicados

| Evento | Quando | Dados |
| --- | --- | --- |
| `plataforma.empresa_criada` | `criar_empresa`, já no schema da empresa nova | `empresa_id`, `administrador` (`nome`, `email`, `celular`) |

## Para os outros apps

Ao criar, desativar ou reativar filial, veículo ou usuário: `exigir_limite(item)` e `atualizar_uso(item, ±1)` na mesma transação. No `ready()`, registre a contagem real com `registrar_contador(item, funcao)` (contas já registra `usuarios`).

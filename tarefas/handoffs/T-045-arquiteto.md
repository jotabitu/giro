# T-045 · Conferência das decisões da T-001 · arquiteto → backend, devops, seguranca, orquestrador

**O que foi feito:** li o código da T-001 na `main` (`backend/config/`, `backend/comum/`, `apps/plataforma`, `apps/contas`, `apps/auditoria`, migrações e testes de fundação) e conferi contra as ADRs 0008 a 0012, a 0013 (parte da T-001) e o modelo de dados. O código segue as ADRs. O resultado está abaixo; o que precisou de decisão virou a ADR 0018.

## As 5 decisões do handoff da T-001

| Decisão | Veredito |
| --- | --- |
| `Empresa` e `Usuario` mínimos, completados na T-010 e na T-011 | Aceita. Na T-011, o `Usuario` precisa de `status` (`convite_pendente`, `ativo`, `desativado`) no lugar de `ativo` (bool), com `is_active = status == "ativo"`: o convite pendente conta no limite do plano e não entra (`USR-01`, `USR-04`, ADR 0008 item 3). E o e-mail único precisa ser `UniqueConstraint(Lower("email"))` (modelo de dados), não só `unique=True` com `lower()` no manager. |
| `comum.auditoria` grava por `apps.get_model`, sem import | Aceita como exceção única e registrada (ADR 0018, item 1). O teste de limites deve recusar outro `apps.get_model` em `comum`. |
| Status de empresa copiados em `comum/empresa.py`, com teste de igualdade | Aceita. Está de acordo com a 0011. |
| Sem `SHOW_PUBLIC_IF_NO_TENANT_FOUND`; host desconhecido dá 404; linha do public em `Empresa` com `admin.<DOMINIO_BASE>` (e `localhost`, `127.0.0.1` em dev) | Aceita. Bate com a ADR 0013 (`empresa_id` do public) e com `docs/api/README.md`. O domínio raiz (páginas de compra) entra na fase 2. |
| `Usuario.is_active` como propriedade sobre `ativo` | Aceita no formato, mas passa a ler `status` na T-011 (ver acima). |

## Pontos achados no código, fora da lista

| # | Ponto | Encaminhamento |
| --- | --- | --- |
| 1 | `na_empresa` sempre usa o ator "Sistema"; a importação (T-044) e outras tarefas disparadas por uma pessoa precisam auditar em nome dela | ADR 0018, item 3. Tarefa para o backend, **junto com a T-033** (que já mexe em `na_empresa` pelo achado C-02). |
| 2 | Código do 409 de transição sai de `REGRA_TRANSICAO`; a ADR 0009 dava `VEI-xx` de exemplo, os contratos usam `transicao_<entidade>` | ADR 0018, item 2. Só convenção: cada model usa `transicao_<entidade>`. |
| 3 | `AtorDaRequisicaoMiddleware` lê `REMOTE_ADDR`; atrás do proxy de mesma origem (ADR 0013) isso é o IP do proxy, e a auditoria e os bloqueios por IP ficam errados | ADR 0018, item 4. Tarefa para o backend (`X-Forwarded-For` com `GIRO_PROXIES_CONFIAVEIS`) e para o devops (variável e proxy). |
| 4 | `comum/dinheiro.py` não tem a conta de juros da `FIN-03` com um arredondamento só; compor `aplicar_percentual` e `proporcional` arredondaria duas vezes (Rafael daria 1122 ou 1123 conforme a ordem) | Tarefa para o backend na T-017: `juros_pro_rata(valor_centavos, pct_mes, dias)` em `Decimal`, `ROUND_HALF_UP` uma vez (CA-017-08: Carlos 70, Rafael 1123). |
| 5 | `/api/schema/` e `/api/docs/` respondem sem login em todo host, inclusive em produção | Tarefa para o backend: só em dev e homologação, ou exigir login de administrador em produção. Avisar a segurança. |
| 6 | `PaginacaoPorCursor` devolve só `resultados`, `proximo` e `anterior`; os contratos põem `contagens` e `indicadores` no mesmo corpo | Tarefa pequena para o backend: aceitar extras no envelope (ex.: `get_paginated_response(data, extras=...)`), para cada view não remontar a resposta. |
| 7 | Trigger da auditoria ainda usa a variável de sessão e não pega `TRUNCATE` | Já coberto pela ADR 0016 e pela T-034 do backend. Nada novo. |
| 8 | `importacao` fora de `TENANT_APPS` | Esperado: o app nasce na T-027 (ADR 0017). |

Nenhum desses pontos bloqueia a T-033.

**Onde:** `docs/decisoes/0018-ajustes-da-conferencia-da-fundacao.md`, `docs/decisoes/README.md`, este handoff.

**Próximo passo para quem recebe:**
- Orquestrador: criar as tarefas dos pontos 1, 3, 5 e 6 (ou anexá-las à T-033 e à T-034) e lembrar o ponto 4 na T-017 e os ajustes do `Usuario` na T-011.
- Backend: ADR 0018.
- DevOps: `GIRO_PROXIES_CONFIAVEIS` e o `X-Forwarded-For` no proxy da mesma origem.
- Segurança: pontos 3 e 5.

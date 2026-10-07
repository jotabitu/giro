# Apps Django, dependências e comunicação entre apps

**Status:** aceita · 07 out 2026 · detalha a 0001

## Contexto

A ADR 0001 diz que apps conversam só por serviços ou eventos, mas não diz quem pode depender de quem. Sem essa ordem aparecem importações circulares (locação gera parcela, parcela paga ativa locação) e migrações que dependem uma da outra. Contrato é usado por locação e por venda, e estava dentro de `locacoes`.

## Decisão

### 1. Apps e schemas

| App | `SHARED_APPS` (public) | `TENANT_APPS` (empresa) |
| --- | --- | --- |
| `django_tenants`, `plataforma` | sim | não |
| `comum`, `auditoria`, `contas`, `django.contrib.auth`, `contenttypes`, `admin`, `sessions`, `messages`, `django_otp` (+ `otp_totp`, `otp_static`), `rest_framework_simplejwt.token_blacklist` | sim | sim |
| `empresas`, `filiais`, `veiculos`, `clientes`, `contratos`, `locacoes`, `vistorias`, `vendas`, `aprovacoes`, `financeiro`, `manutencao`, `notificacoes`, `automacoes`, `relatorios` | não | sim |

App novo: **`contratos`** (modelos de contrato versionados e contratos gerados, assinatura eletrônica, PDF). Sai de `locacoes` para que `vendas` não dependa de `locacoes`.

### 2. Quem pode depender de quem

Um app só importa (serviços, selectors, models para chave estrangeira) de apps que estão **acima** dele nesta lista. Importar de baixo para cima é proibido; o que precisa subir vai por evento.

```
 1. comum
 2. auditoria
 3. plataforma            (public; os apps da empresa leem o plano e o status por selector)
 4. empresas, contas
 5. filiais, notificacoes  (notificacoes é canal: recebe destinatário, modelo e contexto; não conhece a origem)
 6. clientes, veiculos
 7. contratos, aprovacoes
 8. financeiro
 9. manutencao
10. locacoes
11. vistorias
12. vendas
13. automacoes, relatorios   (só orquestram/leem; ninguém depende deles)
```

- Chave estrangeira entre apps é permitida no sentido da lista (ex.: `locacoes.Locacao.veiculo → veiculos.Veiculo`), sempre `on_delete=PROTECT`.
- Escrever em model de outro app é proibido: chame `outro_app.services`. Ler é por `outro_app.selectors`.
- `financeiro`, `aprovacoes` e `contratos` não conhecem a origem do que guardam. Eles usam **origem genérica**: `origem_tipo` (enum fechado: `locacao`, `venda`, `ordem_servico`, `despesa`, `devolucao`, `caixa`, `cliente`, `veiculo`), `origem_id` (bigint) e `origem_codigo` (texto copiado, ex.: `LOC-2836`), com índice em `(origem_tipo, origem_id)`. Não usamos `GenericForeignKey`.

### 3. Eventos de domínio

`comum.eventos` é um despachante em processo:

- `publicar("financeiro.parcela_paga", parcela_id=..., origem_tipo=..., origem_id=...)` chama os assinantes **na mesma transação**, em ordem de registro. Se um assinante falha, a transação toda volta.
- Assinantes ficam em `<app>/eventos.py` e são registrados no `AppConfig.ready()`.
- Efeito externo (WhatsApp, e-mail, parceiro de pagamento, PDF) nunca roda dentro do assinante: o assinante agenda uma tarefa Celery com `transaction.on_commit`.
- Nome do evento: `<app>.<fato_no_passado>`. Cada app documenta os eventos que publica no `README.md` dele.

Eventos iniciais (fase 1):

| Evento | Publicado por | Assinado por |
| --- | --- | --- |
| `financeiro.parcela_paga` | financeiro | locacoes (1º pagamento libera a ativação), clientes (desbloqueio `CLI-05`) |
| `financeiro.parcela_atrasou` | financeiro (tarefa diária) | clientes (bloqueio com 15 dias), locacoes (sinal e régua) |
| `contratos.contrato_assinado` | contratos | locacoes, vendas |
| `aprovacoes.pedido_decidido` | aprovacoes | o app da origem (locacoes, vendas, financeiro, manutencao, clientes, veiculos) |
| `locacoes.locacao_encerrada` | locacoes | manutencao (preventivas `MAN-03`) |

Mensagens (WhatsApp, e-mail, push, sino) são pedidas por chamada direta a `notificacoes.services.enviar(...)`, agendada com `on_commit`; a marca usada é sempre a da locadora.

Chamada direta de serviço (para baixo na lista) continua sendo o caminho padrão quando o efeito faz parte da mesma regra, ex.: `vistorias.services.concluir_saida` chama `locacoes.services.registrar_vistoria_saida`, que chama `veiculos.services.transicionar(..., "alugado")`.

### 4. Estrutura de cada app

`models.py`, `services.py` (único lugar que muda status e grava auditoria), `selectors.py`, `eventos.py`, `api/` (serializers, views, urls finos), `tasks.py`, `admin.py`, `tests/`. Um teste de arquitetura em `backend/tests/test_limites_entre_apps.py` lê os imports e falha se algum app importar de um app abaixo dele.

## Consequências

- Sem ciclo de import e sem ciclo de migração.
- O backend cria o app `contratos` e atualiza `backend/README.md` quando o módulo de locação começar (T-015); em T-001 basta a lista de apps acima no `settings`.
- Mudar a ordem da lista exige nova ADR.

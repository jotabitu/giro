# Ajustes da conferência da fundação (T-001)

**Status:** aceita · 07 out 2026 · complementa as ADRs 0009, 0010, 0011 e 0012 (conferência T-045)

## Contexto

A T-045 conferiu o código da T-001 (`backend/comum/`, `config/`, `apps/plataforma`, `apps/contas`, `apps/auditoria`) contra as ADRs 0008 a 0012 e o modelo de dados. O código segue as ADRs. Quatro pontos, porém, precisam de uma decisão escrita: dois que o código resolveu de um jeito que as ADRs não previam e dois em que as ADRs estavam incompletas para os contratos escritos depois (importação, T-044; auditoria, T-043).

## Decisão

### 1. `comum.auditoria` acha o model de evento por nome (complementa 0010 e 0011)

`comum` está acima de `auditoria` na ordem da ADR 0011 e não pode importá-lo. O código resolve `auditoria.EventoAuditoria` com `django.apps.apps.get_model` na hora de gravar. Isso fica **aceito como a única exceção** à regra de importação: `comum` pode resolver por nome só esse model, só para gravar evento. O teste de limites entre apps continua proibindo `import` e passa a recusar qualquer outro `apps.get_model` dentro de `comum`.

### 2. Código do erro de transição (corrige o exemplo da 0009)

A 0009 dava como exemplo `REGRA_TRANSICAO = "VEI-xx"`. As tabelas de transição das regras não têm número, e os contratos usam `transicao_<entidade>`. Fica: `REGRA_TRANSICAO = "transicao_<entidade>"` (`transicao_veiculo`, `transicao_locacao`, `transicao_cliente`, `transicao_conta`, `transicao_caixa`, `transicao_usuario`, `transicao_empresa`, `transicao_pedido`). Quando uma transição específica tem regra numerada (ex.: `VEI-04` na transferência, `LOC-03`), o serviço levanta o erro com o código da regra antes de chamar `transicionar`.

### 3. Ator nas tarefas (complementa 0010, item 5, e 0012)

`na_empresa(schema_name, *, regra="", ator=None)`:
- sem `ator`, o ator é "Sistema" com a `regra` da tarefa, como hoje (`AUT-02` etc.);
- com `ator`, a tarefa age em nome de quem pediu: tarefas disparadas por uma pessoa (importação, exportação, geração de PDF) recebem `ator = {"tipo", "id", "acesso_suporte_id"}`, **sem nome nem outro dado pessoal** na fila. A tarefa busca o nome no schema (usuário) ou no `public` (atendente do suporte) ao entrar.
- `tarefa_de_empresa` repassa um argumento nomeado `ator` para `na_empresa`, se vier.
- `na_empresa` também confere que o schema existe e é de uma empresa (achado C-02 da segurança, em andamento na T-033); as duas mudanças entram juntas.

### 4. IP do ator atrás do proxy (complementa 0010, item 5, e 0013, item 5)

Com frontend e API na mesma origem (ADR 0013), toda requisição chega ao Django pelo proxy, e `REMOTE_ADDR` é o IP do proxy. O IP gravado na auditoria (`AUD-01`), usado nos bloqueios de login e nos limites por IP vem de `X-Forwarded-For`, contando **da direita** o número de proxies confiáveis configurado em `GIRO_PROXIES_CONFIAVEIS` (padrão 1). Nunca se usa o primeiro valor da lista, que o cliente pode forjar. Sem o cabeçalho (dev sem proxy), vale `REMOTE_ADDR`.

## Consequências

- Backend: os itens 1 a 4 entram como tarefa (ver `tarefas/handoffs/T-045-arquiteto.md`); o item 3 junto com a T-033.
- DevOps: definir `GIRO_PROXIES_CONFIAVEIS` por ambiente e garantir que o proxy da mesma origem acrescenta (e não repassa como veio) o `X-Forwarded-For`.
- Os contratos já escritos não mudam: eles já usam `transicao_<entidade>` e, na importação, o ator de quem pediu.

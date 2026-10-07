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

Com frontend e API na mesma origem (ADR 0013), toda requisição chega ao Django pelo proxy, e `REMOTE_ADDR` é o IP do proxy. O IP gravado na auditoria (`AUD-01`) e usado nos bloqueios de login e nos limites por IP sai de uma função só, `comum.rede.ip_do_cliente(request)`, com estas regras:

- **Só confia no `X-Forwarded-For` se `REMOTE_ADDR` for de um proxy confiável**, ou seja, estiver numa das redes de `GIRO_REDES_PROXY` (lista de CIDR por ambiente). Quem chega direto ao backend, de fora dessas redes, tem o cabeçalho ignorado e vale o `REMOTE_ADDR`. O devops garante também, pela rede, que o Django só é alcançável pelo proxy.
- Confiando, com N = `GIRO_PROXIES_CONFIAVEIS` (padrão 1), o IP do cliente é **`xff[-N]`**, a N-ésima entrada contando da direita. O proxy mais próximo é o próprio `REMOTE_ADDR` e não aparece na lista; o que ele acrescenta (o IP de quem falou com ele) é a última entrada. Nunca o primeiro valor da lista, que o cliente pode forjar.
  Exemplo: N = 1, `REMOTE_ADDR` = proxy, `X-Forwarded-For: 1.2.3.4, 203.0.113.9` → cliente **203.0.113.9** (o `1.2.3.4` foi forjado pelo cliente).
- Se o `X-Forwarded-For` tiver menos entradas do que `GIRO_PROXIES_CONFIAVEIS`, ou um valor que não é IP, vale o `REMOTE_ADDR`, não o primeiro valor.
- Sem o cabeçalho (dev sem proxy), vale o `REMOTE_ADDR`.

Testes: `test_ip_do_cliente_ignora_xff_forjado_sem_proxy`, um com proxy confiável usando o exemplo acima (resultado 203.0.113.9, nunca 1.2.3.4) e um com o cabeçalho curto. *(Os dois últimos casos foram acrescentados pela segurança na conferência, achado C-03 da T-039.)*

## Consequências

- Backend: os itens 1 a 4 entram como tarefa (ver `tarefas/handoffs/T-045-arquiteto.md`); o item 3 junto com a T-033.
- DevOps: definir `GIRO_PROXIES_CONFIAVEIS` e `GIRO_REDES_PROXY` por ambiente, deixar o Django alcançável só pelo proxy e garantir que o proxy da mesma origem acrescenta (e não repassa como veio) o `X-Forwarded-For`.
- Os contratos já escritos não mudam: eles já usam `transicao_<entidade>` e, na importação, o ator de quem pediu.

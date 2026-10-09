# T-088 · Formato das datas na API · arquiteto → orquestrador, backend, frontend, qa, produto

**Decisão (ADR 0020, detalha a 0006 e o `docs/api/README.md`):**
- **Formato único:** momento sai como `AAAA-MM-DDTHH:MM:SSZ`, em UTC, sem fração de segundo (`"2026-10-07T12:12:00Z"`). Na entrada, sempre com fuso. Data sem hora não muda (`"2026-10-21"`).
- **Ponto de configuração:** o renderizador JSON de `comum`, ligado no DRF. Não é um campo novo.
  - `comum/renderizacao.py` traz `EncoderDoGiro` e `JSONRenderer`.
  - No `REST_FRAMEWORK`, `DATETIME_FORMAT: None` e `DEFAULT_RENDERER_CLASSES` com o renderizador de `comum` primeiro.
  - Com `DATETIME_FORMAT = None`, o `DateTimeField` devolve o `datetime` cru, e só o encoder formata. Isso cobre também os valores soltos num `dict`, como contas inteiro e `detalhes.tentar_de_novo_em`.
  - Momento sem fuso numa resposta levanta `TypeError`.
- **Proibido fora de `comum/renderizacao.py`:** `DateTimeField(format=...)`, `DateTimeField(default_timezone=...)`, `strftime("%Y-%m-%dT...")` e `renderer_classes`.
- `TIME_ZONE` continua `America/Sao_Paulo`, porque `relogio.hoje()` depende dele.

**Como está hoje** (conferido no container, DRF 3.18.3; a T-014 viu só parte):
- **Campo de serializer:** sai `-03:00` com microssegundos. É o caso de aprovações, veículos, filiais (`criado_em`) e plataforma.
- **`dict` montado à mão:** sai `Z` com microssegundos. É o caso de contas, que usa o serializer só no OpenAPI.
- **Clientes e `dois_fatores`:** saem `Z`, mas cada um formata por conta própria.
- Os testes não pegavam a diferença porque o relógio congelado não tem fração.

**Teste de arquitetura:** `backend/tests/test_formato_das_datas.py`.
- Três testes de comportamento: campo de serializer, valor solto e momento sem fuso. Ficam `xfail(strict=True)` até a T-093. Quando ela ligar o renderizador, eles passam, e o `strict` obriga a tirar a marca.
- `test_adr_0020_ninguem_formata_momento_por_conta_propria` já vale. Ele varre `apps/` e `comum/` e só aceita os dois arquivos de `PENDENTES_T089`. Qualquer arquivo novo que formate momento por conta própria quebra o teste.

**Prova de conceito** (feita fora do repositório, numa cópia dentro do container):
- Fiz o renderizador e as duas chaves, e tirei o `_momento` e o `strftime`.
- Os 4 testes passam.
- A suíte inteira deu `441 passed`. Os 5 erros são da carteira da T-056, que lê `docs/` e não estava montada no container. Nenhum outro teste mudou.
- O OpenAPI gerado sai **idêntico**, então o cliente tipado do frontend não muda.

**Tarefa do backend (proposta: T-093, "Momentos em UTC na API", pequena):**
- criar `comum/renderizacao.py` como na ADR;
- ligar as duas chaves dentro do dict `REST_FRAMEWORK` (escrito por fora do dict, o mypy reclama);
- trocar o `_momento` de `clientes/api/serializers.py` por `DateTimeField` puro;
- passar `usuario.bloqueado_ate` em `contas/dois_fatores.py`, sem `strftime`;
- tirar o `xfail` e esvaziar `PENDENTES_T089`;
- conferir `make api-schema` (diff vazio).
Ela uniformiza contas, aprovações, plataforma, veículos, filiais e clientes de uma vez, sem mexer nos serializers deles. Se o número 089 já estiver tomado, troque no `reason` do `xfail` e no nome `PENDENTES_T089`.

**Diferenças de contrato dos handoffs:**

| Origem | Item | Destino |
| --- | --- | --- |
| T-013 | 1 `historico_status` com `origem_tipo` e `motivo` | emenda `veiculos.md` |
| T-013 | 2 extras: só ativos, `?ativo=false` | emenda `veiculos.md` |
| T-013 | 3 `PUT` do preço agendado igual ao `POST`, 409 `preco_ja_vigente` | emenda `veiculos.md` |
| T-013 | 4 `corrigir_km` `true` para o vistoriador; km não menor responde 400 | emenda `veiculos.md` |
| T-013 | 5 valores de `situacao.tom` | emenda `veiculos.md` |
| T-013 | 6 `documentos_resumo` `null`, `VEI-03` no desbloquear, `VEN-10` | sem emenda: T-079 (`VEI-03`) e a tarefa de vendas (`VEN-10`, fase 2) |
| T-013 | 7 `PATCH` de categoria recusa trocar a filial com veículos | emenda `veiculos.md` |
| T-013 | 8 ocupação pelo tempo exato | emenda `veiculos.md` e `[decisão]` para o produto (fração de dia na `VEI-06`) |
| T-013 | 9 exportação da frota | sem tarefa nova: fase 2 (`AUD-07`, "exportação e cancelamento" no backlog) |
| T-081 | 1 evento com `motivo_pedido` | emenda `aprovacoes.md` |
| T-081 | 2 `decidido_por` no cancelar | emenda `aprovacoes.md` |
| T-081 | 3 403 `so_quem_pediu` | emenda `aprovacoes.md` |
| T-081 | 4 motivo da aprovação só na auditoria e no evento | emenda `aprovacoes.md` |
| T-081 | 5 `pct` em texto com 2 casas | sem emenda: já é a convenção do README |
| T-081 | 6 quem não decide recebe lista vazia | emenda `aprovacoes.md` |
| T-014 | 1 `contagens.inativos` | emenda `clientes.md` |
| T-014 | 2 momentos | ADR 0020 e T-093 |
| T-014 | 3 `conta_mais_antiga_id` no bloco `financeiro` | emenda `clientes.md` e `financeiro.md`; código na T-017 |
| T-014 | 4 eventos do financeiro com `cliente_id` | emenda `financeiro.md`, código na T-017. `parcela_paga`: `conta_id`, `cliente_id`, `tipo`, `origem_tipo`, `origem_id`, `valor_centavos`, `pago_em`. `parcela_atrasou`: `conta_id`, `cliente_id`, `tipo`, `origem_tipo`, `origem_id`, `vencimento`, `dias_atraso`. Esse contrato vale no lugar do exemplo `parcela_id` da ADR 0011. |
| T-014 | 5 contadores `contas_atrasadas_15_dias`, `em_aberto_centavos`, `locacao_aberta`, `venda_aberta` | emenda `clientes.md`, `financeiro.md` e `locacoes.md`; código na T-015 e na T-017, e `venda_aberta` com vendas (fase 2) |
| T-014 | 6 `bloqueio.descricao` e os campos `bloqueio_desde`, `bloqueio_descricao` e `responsavel_celular` | emenda `clientes.md` e `modelo-de-dados.md` |
| T-014 | 7 sem `pg_trgm` | emenda `clientes.md` e `modelo-de-dados.md` (`icontains` com `Lower(nome)`). Sem tarefa agora: o trigram volta com ADR de infraestrutura quando o volume pedir |
| T-014 | 8 `analisar` sem documentos | emenda `clientes.md` |
| T-014 | 9 desbloquear quem não está bloqueado responde 409 | emenda `clientes.md`. Também ficou escrito que o desbloqueio direto cancela o `APR-05` pendente |
| T-014 | 10 exportações e LGPD do titular | sem tarefa nova: fase 2 (`AUD-06`, `AUD-07`) |

Única tarefa nova: a **T-093**. O resto vira emenda, ou já tem tarefa (T-015, T-017, T-079, fase 2).

**Onde:**
- `docs/decisoes/0020-formato-dos-momentos-na-api.md` e o índice em `docs/decisoes/README.md`.
- `docs/api/README.md`: a linha de Formatos.
- Contratos: `docs/api/veiculos.md`, `aprovacoes.md`, `clientes.md`, `financeiro.md` e `locacoes.md`, com a versão "emendas de 09 out 2026 (T-088)".
- `docs/decisoes/modelo-de-dados.md`: Cliente.
- `backend/tests/test_formato_das_datas.py`.
- `tarefas/backlog.md`: a `[decisão]` da `VEI-06`. `tarefas/em-andamento.md`.

**Check:**
- No arquivo novo, ruff, `ruff format --check` e mypy estão limpos.
- Pytest do arquivo: `1 passed, 3 xfailed`. Rodei no container `giro-backend` com o código montado só para leitura.
- A suíte inteira só rodou na prova de conceito, num Postgres descartável (rede e container `t088-*`, já removidos).

**Próximo passo para quem recebe:**
- **Orquestrador:** criar a T-093 no quadro. A T-017 ganha os eventos com `cliente_id`, os contadores e o `conta_mais_antiga_id`, que já estão no contrato. A T-015 ganha o contador `locacao_aberta`.
- **Backend:** fazer a T-093 pela ADR 0020. Nas próximas tarefas, passe sempre o `datetime` com fuso e deixe o formato com o renderizador.
- **Frontend:** nada muda no tipo. Compare momentos por `Date`, não por texto: aprovações e veículos vão deixar de vir com `-03:00`.
- **QA:** momento em teste se compara com `Z` e sem fração.
- **Produto:** a `[decisão]` da `VEI-06` (fração de dia na ocupação).

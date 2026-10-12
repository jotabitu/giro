# T-017 · Contas a receber, caixa do dia, baixa · backend → orquestrador, frontend, qa, arquiteto, produto, seguranca

**O que foi feito** (`docs/api/financeiro.md`, `docs/qa/criterios/T-017.md`, CA-017-01 a 23):

- **Contas a receber** (`GET/POST /api/financeiro/contas-receber/`, detalhe com `historico`):
  - status pela data (`vence_hoje`, `atrasada`), sem tarefa à meia-noite;
  - `dias_atraso` e `faixa_atraso` (`FIN-02`);
  - `valor_hoje` pela `devido_ate` da T-114 (`FIN-03`, conta que nasce vencida inclusive);
  - indicadores e abas da `FIN-15`;
  - filtros `periodo`, `situacao`, `faixa`, `cliente`, `origem_tipo`/`origem_id`, `forma`, `busca`, `ordem`;
  - `acoes` por perfil e status.
- **Baixa:**
  - `receber` no caixa aberto da filial do `X-Filial` (`FIN-04`). O valor tem de ser o `valor_hoje`; diferente → 422 `FIN-01`. Multa e juros ficam gravados.
  - Uma baixa só (`services._baixar`) para caixa, webhook e caução, sempre publicando `financeiro.parcela_paga`.
- **Cancelar, renegociar e estornar** (`FIN-01`):
  - renegociar usa a `Renegociacao` de origem `cliente`;
  - estornar: a original continua `paga`, com `estornada_em`; nasce uma conta aberta igual, com `estorno_de`, e o movimento de estorno no caixa aberto.
- **Pix e boleto** (`cobranca/`):
  - interface `integracoes/pagamentos/` (`base.py`, `falso.py` com `simular_pagamento`);
  - `plataforma.ContaPagamento` mínima, para achar a empresa pelo hash do token e para o 422 `recebimentos_desligados`;
  - `comum.WebhookRecebido` com `evento_id` único.
- **Webhook** `POST /api/webhooks/pagamentos/asaas/`, no host da plataforma:
  - token conferido por hash e `compare_digest`; inválido → 401, e nada é gravado;
  - evento repetido → 200 sem efeito;
  - a tarefa `aut_05_processar_webhook` consulta o parceiro. Valor igual: baixa (ator Sistema, `AUT-05`), entra no caixa se a cobrança foi gerada nele e manda o recibo por WhatsApp. Valor diferente, conta já fechada ou estorno no parceiro: `PendenciaPagamento` e aviso ao administrador e ao financeiro.
  - Pendências: `GET /api/financeiro/pendencias-pagamento/` e `.../resolver/`.
- **Cobrar e régua:** `cobrar/` e `cobrar-em-lote/` (WhatsApp, uma vez por conta por dia). `aut_03_regua_de_cobranca` às 09:00 publica `financeiro.parcela_atrasou`: Rafael bloqueia; conta vencida em 23 set bloqueia em 08 out; quitar desbloqueia.
- **Caixa do dia:**
  - `caixas/hoje/`, abrir (409 `FIN-07`, restrição única), `movimentos/`, `sangria/` (422 `sangria_maior_que_gaveta`), `movimentos/{mid}/estornar/` e `fechar/`;
  - diferença exige motivo e abre o pedido `APR-04`; aprovado → `fechado`; recusado ou cancelado → `aberto`; quem fechou não aprova (`APR-09`);
  - `aut_08_fechamento_automatico_do_caixa` às 23:59 → `fechado_sem_conferencia` e aviso aos gerentes;
  - `MovimentoCaixa` imutável (`MovimentoImutavel`);
  - contador `caixas` para o `FIL-06`.
- **Despesas** (`despesas/`, `despesas/{id}/`, `pagar/`):
  - até R$ 500 nasce `a_pagar`, ou `paga` no caixa; acima, `aguardando_aprovacao` com o pedido `APR-03`, decidido pelo assinante em `financeiro/eventos.py`;
  - vistoriador só lança manutenção;
  - nota em armazenamento privado com URL assinada;
  - custo no veículo (`indicadores_financeiros.custo_manutencao_ano_centavos`; `rendeu_no_ano_centavos` vem de `locacoes`).
- **Reembolsos:** `GET /api/financeiro/reembolsos/` e `reembolsos/{id}/feito/`. A devolução em dinheiro sai pelo caixa aberto e nasce `feito`; sem caixa, 422 `FIN-07` "Abra o caixa do dia para devolver em dinheiro" (CA-016-18).
- **Ligações (T-128, T-129):**
  - painel: `caixa_hoje` (seed: recebido 111190, a receber hoje 262580, despesas 4800, saldo 106390), `caixas_do_dia`, KPI `sai_hoje`, despesas em `para_hoje` e contadores `despesas` (sem as próprias, `APR-09`) e `contas_a_pagar`;
  - `financeiro` entrou em `GIRO_MODULOS_ATIVOS` (contador `receber` = 2);
  - clientes: bloco `financeiro` (total pago sem caução, em aberto, a devolver, conta mais antiga), item `historico` da análise, filtro e contagem `em_aberto`, `em_aberto_total_centavos` (164640) e os contadores do `CLI-05` e do `CLI-09`.

**Onde:**
- `backend/apps/financeiro/` (`models.py`, migração `0004`, `services.py`, `selectors.py`, `leituras.py`, `eventos.py`, `tasks.py`, `api/`, `README.md`);
- `backend/integracoes/pagamentos/`;
- `backend/comum/` (`models.WebhookRecebido` com a migração `0002`, `leituras.registrar_total`/`total`, `limites.WebhookPorIP`);
- `backend/apps/plataforma/` (`ContaPagamento`, migração `0007`);
- `backend/apps/locacoes/leituras.py`, `backend/apps/clientes/selectors.py`, `backend/apps/relatorios/selectors.py`, `backend/apps/contas/navegacao.py`;
- `backend/config/` (settings: módulo, provedor, Beat das AUT-03 e AUT-08, throttle e nomes de enum; urls e urls_publico);
- `docs/api/openapi.yaml`.

**Contrato:** `docs/api/financeiro.md`, `docs/api/painel.md` (ver `docs/api/openapi.yaml`, validado sem avisos e só com acréscimos).

**Regras cobertas:** FIN-01 a FIN-08, FIN-15, APR-03, APR-04, APR-09, LOC-04, LOC-05, LOC-07, CLI-05, FIL-06, AUT-03, AUT-05, AUT-08, DEV-02. Testes em `backend/tests/aceitacao/test_t017_financeiro.py` (31, um ou mais por critério: `test_fin_01_ca_017_01_*` a `test_fin_03_ca_017_23_*`, mais painel, isolamento e permissão) e `test_fin_07_ca_016_18_*` em `test_t016_vistorias.py`, que deixou de ser `xfail`.

**Check** (`rodar.sh`, imagem `giro-backend:latest`, um arquivo por vez): ruff, `ruff format --check`, mypy e `makemigrations --check` limpos. Pytest: todos os 48 arquivos passam, sem nenhum `xfail` (o do CA-016-18 era o último). Frontend: `api:gerar`, `typecheck` e 274 testes passando, sem mudança de código.

**Testes antigos ajustados:**
- T-014: em aberto `0` em vez de `null`, porque o fornecedor agora existe; os testes que trocam fornecedores devolvem o de `financeiro`.
- T-129: o financeiro passou a ter os itens `receber` e `contas_a_pagar`; `sai_hoje` vale 0; `caixas_do_dia` vem `[]`.
- T-011: `conciliacao` entra na lista de todos os módulos.

**Decisões técnicas que tomei (sem regra nova; conferir):**
1. Receber e gerar Pix acham a conta em qualquer filial da empresa: a conta pode ser paga no caixa de outra filial (`FIL-06`). Lista e detalhe seguem o `X-Filial`.
2. O webhook confere o token assim: o provedor lê o corpo e o token do cabeçalho (`EventoWebhook.token`), e a view compara o hash com `ContaPagamento.webhook_token_hash`.
3. A baixa pelo webhook grava a multa e os juros do dia em que a cobrança foi gerada, que somam o valor pago.
4. O estorno de movimento repete o tipo e a forma do original, e o resumo do dia desconta. Conta paga com a caução não se estorna aqui (422 `DEV-02`).
5. A conciliação (fase 2) passou para `modulo="conciliacao"` na navegação. Com `financeiro` ligado, o item levaria a uma tela que não existe.
6. Pendências e avisos do webhook vão para o administrador e o financeiro (todos ativos).

**Para o arquiteto (diferenças do contrato):**
- Campos a mais na conta: `dias_atraso`, `observacao`, `estorno_de` e `estornada_em`.
- `cobranca/` aceita `no_caixa: true`, o jeito de a tela `Caixa` ligar o Pix ao caixa.
- `cobrar/` e o lote respondem 202 `{enviadas}`.
- O `historico` do detalhe é `[{em, acao, por, motivo}]`, da auditoria e das cobranças.
- Rota a mais: `GET /api/financeiro/despesas/{id}/`.
- `caixa_hoje` do painel aparece com o caixa de hoje em qualquer status, porque o campo `status` existe; só sem caixa é `null`.
- `ContaPagamento` ainda sem `chave_api_cifrada` (fica para a T-029).

**O que ficou de fora:**
- Asaas real, subconta, cobrança recorrente (`AUT-04`) e `FaturaAssinatura`: T-029.
- `?ordem=-total_pago` na lista de clientes continua ordenando por criação. A anotação existe (`fin_total_pago`), mas `clientes` não a conhece.
- Três `[decisão]` no backlog para o produto: item `historico` da análise, período `semana` e caução na lista, e os dias e textos da régua.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR, pedir ao arquiteto a revisão das diferenças acima e ao produto as três `[decisão]`.
- **Frontend (T-023):** telas `Receber`, `Caixa` e `Financeiro` sobre o OpenAPI.
  - Erros: 422 `FIN-01`, `FIN-07` e `recebimentos_desligados`; 409 `FIN-07` "Este caixa já foi fechado".
  - O Pix do caixa vai com `no_caixa: true`.
  - Na ficha do cliente, usar o bloco `financeiro`.
- **QA:** os números do seed estão nos testes. O caixa de 07 out usa lançamentos avulsos no lugar das contas de Juliana, Diego e da diária da Urbana: os valores são os mesmos, as descrições não.
- **Segurança:** conferir o webhook: token por hash e `compare_digest`, `WebhookRecebido` idempotente, limite de 120 por minuto por IP e consulta ao parceiro antes de baixar (S-14).

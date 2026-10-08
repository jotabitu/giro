# Financeiro: contas a receber, caixa do dia, despesas e pagamentos

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-043) · **App:** `financeiro` (schema da empresa) · **Regras:** FIN-01 a FIN-08, APR-03, APR-04, APR-09, LOC-04, LOC-05, LOC-07, CLI-05, DEV-02, FIL-06, AUT-03, AUT-04, AUT-05, AUT-08 · **ADRs:** 0007, 0011, 0012, 0014 · **Segurança:** S-05, S-14 · **Critérios:** `docs/qa/criterios/T-017.md` · **Telas:** Receber, Caixa, Despesas, Financeiro

Convenções gerais em `docs/api/README.md`. Modelo: itens 18, 19, 21 e 22 e apoio em `docs/decisoes/modelo-de-dados.md`. Base: `/api/financeiro/`.

**Fase 1:** contas a receber, baixa, cobrança por Pix e boleto, caixa do dia, despesas, devoluções ao cliente, webhooks. **Fase 2:** comissões (`FIN-09`, `FIN-10`), conciliação bancária (`FIN-11`, `FIN-12`), DRE e relatórios (`FIN-13`, `FIN-14`), saldo em contas e fluxo de caixa previsto da tela `Financeiro`.

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver contas a receber | todas as filiais | sua filial | sua filial | — | todas as filiais |
| Receber no caixa, gerar Pix ou boleto, cobrar | sim | sim | sim | — | sim |
| Lançamento avulso, cancelar, renegociar, estornar | sim | sim | — | — | sim |
| Abrir e fechar caixa, sangria | sim | sim | sim (sua filial) | — | sim |
| Aprovar diferença de caixa (`APR-04`) | sim | sim | — | — | — |
| Lançar despesa | sim | sim | sim | só manutenção | sim |
| Aprovar despesa acima de R$ 500 (`APR-03`) | sim | sim | — | — | — |
| Pagar despesa, marcar devolução ao cliente como feita | sim | — | — | — | sim |

Quem lançou ou pediu nunca aprova o próprio pedido (`APR-09`). O vistoriador recebe 403 em todo o app.

---

## Valor de uma conta no dia (FIN-03)

Toda conta devolve o valor a pagar **hoje**, calculado pela API:

```json
"valor_hoje": { "data": "2026-10-07", "dias_atraso": 7, "principal_centavos": 29940,
                "multa_centavos": 599, "juros_centavos": 70, "total_centavos": 30609,
                "cobra_juros": true }
```

- `dias_atraso`: dias corridos do dia seguinte ao vencimento até a data do pagamento, no fuso da filial.
- Multa: `multa_atraso_pct` da empresa (padrão e teto 2,00) sobre o principal, uma vez, a partir de 1 dia de atraso.
- Juros (`FIN-03`, decidido em 07 out 2026): `principal × juros_mes_pct ÷ 100 ÷ 30 × dias_atraso`, em `Decimal`, arredondado **uma vez** para o centavo com `ROUND_HALF_UP` (padrão e teto: 1,00% ao mês).
- `cobra_juros` é falso quando o contrato da origem não tem a cláusula (`Contrato.clausula_juros`, `contratos.md`): multa e juros saem 0.
- Paga no vencimento ou antes: multa e juros 0.
- Casos do seed em 07 out: Carlos (LOC-2841, 29940, 7 dias) → multa 599, juros 70, total **30609**; Rafael (LOC-2790, 134700, 25 dias) → multa 2694, juros 1122,5 → **1123**, total **138517**.
- Na baixa, `multa_centavos` e `juros_centavos` ficam gravados na conta.

## Contas a receber

### Representação

```json
{
  "id": 9010, "tipo": "parcela", "numero": 2, "total_parcelas": 5,
  "origem": { "tipo": "locacao", "id": 2841, "codigo": "LOC-2841" },
  "cliente": { "id": 1188, "nome": "Carlos Menezes" },
  "filial": { "id": 1, "nome": "Filial Centro" },
  "veiculo_placa": "QXA4B21",
  "vencimento": "2026-09-30", "valor_centavos": 29940,
  "status": "atrasada", "faixa_atraso": "1_7",
  "forma_prevista": "pix_automatico",
  "valor_hoje": { ... },
  "pago_em": null, "forma": null, "multa_centavos": 0, "juros_centavos": 0,
  "cobranca_aberta": { "id": 55, "tipo": "pix", "vence_em": "...", "pix_copia_e_cola": "...", "qr_code_url": "..." },
  "acoes": { "receber": true, "gerar_pix": true, "gerar_boleto": true, "cobrar": true,
             "cancelar": true, "renegociar": true, "estornar": false }
}
```

- `tipo`: `parcela`, `caucao`, `multa`, `avaria`, `acerto`, `outro`. Caução não é receita (`LOC-04`): não entra em "previsto", "recebido" nem "em aberto".
- `status` como na `FIN-01`: o banco guarda `aberta`, `paga`, `cancelada`, `renegociada`; a API devolve `vence_hoje` (vencimento hoje) e `atrasada` (vencimento antes de hoje) para contas `aberta`, sem tarefa à meia-noite.
- `faixa_atraso` (`FIN-02`): `1_7`, `8_30`, `mais_30`, ou `null` (não atrasada).

### GET /api/financeiro/contas-receber/
Query: `?periodo=hoje|semana|mes` (vencimento), `?situacao=atrasadas|vencem_hoje|a_vencer|pagas|canceladas`, `?faixa=1_7|8_30|mais_30`, `?cliente=<id>`, `?origem_tipo=&origem_id=`, `?forma=`, `?busca=` (cliente, código), `?ordem=vencimento|-valor`. Filial pelo `X-Filial` (`todas` para administrador e financeiro).
200:
```json
{
  "indicadores": {
    "previsto_mes_centavos": 5200210, "previsto_mes_parcelas": 128,
    "recebido_mes_centavos": 1340170, "recebido_pct": "25.77",
    "vence_hoje_centavos": 262580, "vence_hoje_parcelas": 6,
    "em_atraso_centavos": 164640, "em_atraso_clientes": 2, "em_atraso_parcelas": 2,
    "faixas": { "1_7": 29940, "8_30": 134700, "mais_30": 0 }
  },
  "contagens": { "todas": 130, "atrasadas": 2, "vencem_hoje": 6, "a_vencer": 92, "pagas": 30 },
  "resultados": [ { ...representação... } ],
  "proximo": "...", "anterior": null
}
```
Caso do seed (`FIN-01`, CA-017-03): em aberto = Carlos 29940 + Rafael 134700 = **164640** em 2 clientes; Carlos na faixa `1_7`, Rafael na `8_30`.

Números da `FIN-15` (base: contas da filial, sem caução e sem `cancelada` e `renegociada`, valores sem multa e juros):
- `previsto_mes_*`: contas com vencimento no mês corrente, pagas ou não. `recebido_mes_*`: as `paga` desse previsto (não o que foi pago no mês). `recebido_pct` = recebido ÷ previsto, em valor, com 2 casas (`ROUND_HALF_UP`): 1340170 ÷ 5200210 = **"25.77"**.
- `vence_hoje_*`: contas não pagas com vencimento hoje. `em_atraso_*` e `faixas`: todas as `atrasada`, de qualquer mês. Os indicadores não mudam com `?periodo=` nem `?situacao=`.
- `contagens` são as abas da tela, uma chave por aba: `atrasadas` ignora o período (todas as atrasadas); `vencem_hoje`, `a_vencer` e `pagas` seguem o `?periodo=` pelo vencimento; **`todas` = soma das quatro** (aqui 2 + 6 + 92 + 30 = 130). `canceladas` não é aba e não entra em `todas`. O filtro `?situacao=` devolve exatamente as contas contadas na aba.
- Com `?periodo=mes`, `previsto_mes_parcelas` = `pagas` + `vencem_hoje` + `a_vencer` + as atrasadas que vencem no próprio mês (aqui nenhuma: Carlos venceu em 30 set e Rafael em setembro), então 30 + 6 + 92 = 128.
- O contador `receber` de `GET /api/painel/contadores/` é `contagens.atrasadas` (`FIN-15`; seed: 2).

Caso do seed (`FIN-15`, linha "Contas a receber de outubro em 07 out" das regras, carteira em `docs/qa/carteira-outubro/`): Filial Centro, `?periodo=mes`, em 07 out. A vencer soma 3597460 em 92 parcelas.

### GET /api/financeiro/contas-receber/{id}/
200: representação mais `historico` (cobranças geradas, mensagens enviadas, baixa, estorno).

### POST /api/financeiro/contas-receber/
"Novo lançamento" avulso. Perfis: administrador, gerente, financeiro.
Corpo: `{ cliente_id, tipo: "multa" | "avaria" | "outro", descricao, vencimento, valor_centavos, origem?: { tipo, id } }`. 201.
As parcelas e a caução de locação **não** nascem aqui: vêm de `locacoes.services` (`locacoes.md`).

### POST /api/financeiro/contas-receber/{id}/receber/
Baixa no caixa (`FIN-04`: dinheiro e cartão). Perfis: quem recebe.
Corpo: `{ "forma": "dinheiro" | "cartao_debito" | "cartao_credito", "valor_centavos": 30609 }`.
- Usa o caixa `aberto` da filial da requisição (`X-Filial`), que pode ser diferente da filial da conta (`FIL-06`); a conta mantém a filial de origem.
- `valor_centavos` tem que ser igual a `valor_hoje.total_centavos`. Diferente → 422 `{ "codigo": "FIN-01", "mensagem": "Não existe pagamento parcial. Receba o valor inteiro ou renegocie." }` (CA-017-06).
200: conta `paga`, com `forma`, `pago_em`, multa e juros gravados, e o `MovimentoCaixa` de entrada ligado. Publica `financeiro.parcela_paga`.
422 `{ "codigo": "FIN-07", "mensagem": "Abra o caixa do dia para receber" }` sem caixa aberto. 409 `transicao_conta` se não estiver `aberta`.

### POST /api/financeiro/contas-receber/{id}/cobranca/
"Gerar Pix" e boleto. Corpo: `{ "tipo": "pix" | "boleto" }`.
201: a `CobrancaExterna`:
```json
{ "id": 55, "tipo": "pix", "valor_centavos": 30609, "vence_em": "2026-10-07",
  "pix_copia_e_cola": "000201...", "qr_code_url": "...", "linha_digitavel": null, "boleto_url": null,
  "status": "aguardando" }
```
- O valor é o `valor_hoje` do dia; Pix vence no fim do dia, boleto na data pedida (`{ "vence_em" }`, padrão: vencimento da conta, ou hoje se já venceu).
- Gerar outra cobrança cancela a aberta no parceiro.
- Gerada pela tela `Caixa`, a cobrança guarda o caixa: a baixa pelo webhook entra como entrada `pix` nesse caixa (`FIN-07`). Gerada fora do caixa (régua, `AUT-03`), não passa pelo caixa.
- Sem subconta aprovada (`plataforma.ContaPagamento`): 422 `{ "codigo": "recebimentos_desligados", "mensagem": "Conecte os recebimentos para gerar Pix e boleto" }` (implantação, passo 10).

### POST /api/financeiro/contas-receber/{id}/cobrar/ · POST /api/financeiro/contas-receber/cobrar-em-lote/
"Cobrar" e "Cobrar todos pelo WhatsApp". Corpo do lote: `{ "ids": [ ... ] }` (até 100). 202. Envia a mensagem de cobrança com Pix do valor do dia, com a marca da locadora (`AUT-03`), uma vez por conta por dia.

### POST /api/financeiro/contas-receber/{id}/cancelar/
Perfis: administrador, gerente, financeiro. Corpo: `{ motivo }`. Só `aberta`. 200 `cancelada`. Também chamado por serviço (locação cancelada antes da retirada, `LOC-12`).

### POST /api/financeiro/contas-receber/renegociar/
Corpo: `{ "contas": [9010], "novas": [ { "vencimento": "2026-10-15", "valor_centavos": 15000 }, { "vencimento": "2026-10-22", "valor_centavos": 15609 } ], "motivo": "..." }`.
201: as novas contas (`aberta`, `renegociada_em` = original); as originais vão para `renegociada` e saem do em aberto (`FIN-01`). Conta `paga` ou `cancelada` → 409.

### POST /api/financeiro/contas-receber/{id}/estornar/
Só `paga`. Corpo: `{ motivo }`. Conta paga não se edita: a correção é estorno (CA-017-09).
200: a original continua `paga` com `estornada_em`; nasce uma conta `aberta` igual (mesmo valor e vencimento) com `estorno_de` = original, e, se a baixa foi no caixa, um movimento de estorno no caixa aberto. Para **devolver dinheiro** ao cliente, use as devoluções abaixo, não o estorno.

### Cobrança recorrente (AUT-04)

Locação com `forma_pagamento = pix_automatico` (ou cartão recorrente) ganha uma autorização no parceiro na ativação (`AutorizacaoRecorrente`). No vencimento de cada parcela, `aut_04_cobranca_recorrente` cria a `CobrancaExterna` daquela conta usando a autorização; a baixa vem pelo webhook. A referência externa de cada cobrança é o `id` da conta, para casar o pagamento sem ambiguidade.

---

## Devoluções ao cliente

Dinheiro que sai para o cliente (caução da devolução, `DEV-02`; o que foi pago numa locação cancelada antes da retirada, `LOC-12`; crédito de semanas, `LOC-13`) vira um `Reembolso`.

```json
{ "id": 31, "cliente": { "id": 1201, "nome": "Juliana Rocha" }, "origem": { "tipo": "devolucao", "codigo": "LOC-2836" },
  "valor_centavos": 18300, "forma": "pix", "status": "a_fazer", "feito_em": null, "comprovante": null }
```

- `dinheiro`: sai no caixa aberto na hora (movimento de saída) e nasce `feito`.
- `pix`: nasce `a_fazer`; a pessoa faz o Pix pela conta da locadora e marca como feito com o comprovante. Transferência automática pelo parceiro fica para depois (precisa das proteções de saque da subconta, S-05).
- `estorno_cartao`: nasce `a_fazer`; marcado como feito depois do estorno na maquininha.

`GET /api/financeiro/reembolsos/?status=a_fazer` · `POST /api/financeiro/reembolsos/{id}/feito/` (`multipart`: `comprovante?`) · administrador, financeiro, gerente.

Reembolsos `a_fazer` entram em "Para hoje" do início do financeiro (todas as filiais) e do gerente da filial de origem, e geram aviso no sino. Decidido pelo dono do produto em 07 out 2026 (item 21, opção A).

---

## Caixa do dia (FIN-07, FIN-08, APR-04)

### Representação

```json
{
  "id": 240, "filial": { "id": 1, "nome": "Filial Centro" }, "data": "2026-10-07",
  "status": "aberto", "aberto_por": { "id": 3, "nome": "Bruna Alves" }, "aberto_em": "2026-10-07T10:55:00Z",
  "resumo": {
    "entrou_hoje_centavos": 111190, "recebimentos": 5,
    "por_forma": { "pix": { "centavos": 37390, "quantidade": 2 }, "cartao": { "centavos": 10900, "quantidade": 1, "texto": "cai em 30 dias" },
                   "dinheiro": { "centavos": 62900, "quantidade": 2 } },
    "gaveta": { "troco_centavos": 20000, "entradas_dinheiro_centavos": 62900, "saidas_dinheiro_centavos": 54800,
                "esperado_centavos": 28100 }
  },
  "fechamento": null,
  "acoes": { "sangria": true, "fechar": true, "receber": true }
}
```

**Caso do seed (CA-017-13):** entradas 32900 pix (Juliana, LOC-2836) + 10900 cartão (Diego, LOC-2848, renovação de 1 diária, `LOC-08`) + 32900 dinheiro + 30000 dinheiro (caução do Lucas, LOC-2856) + 4490 pix (diária Urbana retirada hoje) = **111190** em 5 recebimentos; saídas em dinheiro 50000 (sangria) + 4800 (óleo) = 54800; gaveta = 20000 + 62900 − 54800 = **28100** (R$ 281,00).

`resumo.entrou_hoje_centavos` conta as entradas, inclusive a caução recebida (é dinheiro que entrou no caixa, ainda que não seja receita).

### GET /api/financeiro/caixas/hoje/
Caixa de hoje da filial do `X-Filial` (data no fuso `America/Sao_Paulo`). 200: representação, ou `{ "caixa": null, "pode_abrir": true }`.

### POST /api/financeiro/caixas/
Abrir. Corpo: `{ "troco_centavos": 20000 }`. 201: `aberto`.
409 `{ "codigo": "FIN-07", "mensagem": "O caixa de hoje desta filial já foi aberto" }`, também em duas chamadas simultâneas (restrição única `(filial, data)`).

### GET /api/financeiro/caixas/{id}/movimentos/
Query: `?tipo=entrada|saida|sangria`. 200: `{ "resultados": [ { "id", "hora": "...", "tipo": "entrada", "forma": "pix", "descricao": "Juliana Rocha · LOC-2836 · 2ª semana", "valor_centavos": 32900, "origem": { ... }, "registrado_por": "...", "estorno_de": null } ] }`. Saídas e sangrias vêm com o valor positivo e `tipo` diz o sentido; a tela mostra o sinal.

### POST /api/financeiro/caixas/{id}/sangria/
Corpo: `{ valor_centavos, descricao }` (ex.: "depósito no banco"). 201: o movimento. 422 `{ "codigo": "sangria_maior_que_gaveta" }` se passar do esperado na gaveta.

### POST /api/financeiro/caixas/{id}/movimentos/{mid}/estornar/
Corpo: `{ motivo }`. 201: movimento de estorno, no caixa aberto de hoje, com `estorno_de`; o original não muda (CA-017-17). Estornar a entrada de uma conta recebida usa `contas-receber/{id}/estornar/`.

### POST /api/financeiro/caixas/{id}/fechar/
Corpo: `{ "contado_centavos": 28100, "motivo_diferenca": null }`.
- Contado = esperado → `fechado`, com `contado`, `esperado` e `diferenca_centavos = 0`.
- Diferente (falta ou sobra) → exige `motivo_diferenca` (400 `validacao` sem ele); o caixa vai para `aguardando_aprovacao` e nasce o pedido `APR-04`, avisando os gerentes da filial. Aprovado → `fechado` com a diferença registrada; recusado → volta a `aberto` para contar de novo.
- Depois de `fechado`, qualquer movimento nesse caixa → 409 `{ "codigo": "FIN-07", "mensagem": "Este caixa já foi fechado" }`.
Caso CA-017-15: contado 27100 com motivo "Troco errado" → `aguardando_aprovacao`, `diferenca_centavos: -1000`.

### Fechamento automático (FIN-08, AUT-08)
`aut_08_fechamento_automatico_do_caixa`, às 23:59 em `America/Sao_Paulo`: caixa ainda `aberto` → `fechado_sem_conferencia` (sem contado e sem diferença) e tarefa para os gerentes da filial. Caixa `aguardando_aprovacao` não é mexido.

---

## Despesas (FIN-05, FIN-06, APR-03)

### Representação
```json
{ "id": 801, "data": "2026-10-07", "descricao": "Pneus (2 unidades)", "categoria": "manutencao",
  "veiculo": { "id": 88, "placa": "PMZ3E17" }, "filial": { "id": 1 },
  "valor_centavos": 120000, "vencimento": "2026-10-07", "status": "aguardando_aprovacao",
  "pago_em": null, "forma": null, "lancada_por": { "id": 4, "nome": "João Silva" },
  "nota": { "url": "...", "url_expira_em": "..." }, "pedido_aprovacao_id": 91,
  "rotulo_situacao": "Aguardando gerente" }
```

### GET /api/financeiro/despesas/
Query: `?mes=2026-10`, `?status=`, `?categoria=`, `?veiculo=<id>`. Filial pelo `X-Filial`.
200 com `indicadores`: `{ "gasto_mes_centavos": 706670, "aguardando_aprovacao_centavos": 120000, "aguardando_aprovacao_quantidade": 1, "a_pagar_semana_centavos": 41230, "por_categoria": { "fixas": 391230, "rastreamento": 172000, "manutencao": 124800, "impostos": 18640 } }` e `contagens` por status.
Caso do seed (CA-017-19): outubro **706670**; aguardando aprovação **120000** (só os pneus; o IPVA de 18640 nasce `a_pagar`).

### POST /api/financeiro/despesas/
`multipart/form-data`: `descricao`, `valor_centavos`, `data`, `vencimento`, `categoria` (`fixas`, `manutencao`, `rastreamento`, `impostos`, `pessoal`, `outros`), `veiculo_id?`, `nota?` (imagem ou PDF até 10 MB), `pago_no_caixa?` (bool), `forma?`.
- Até 50000 (R$ 500,00) → `a_pagar`; com `pago_no_caixa`, nasce `paga` com um movimento de saída em dinheiro no caixa aberto.
- Acima de 50000 → `aguardando_aprovacao` e pedido `APR-03`; não pode ser lançada como paga no caixa (422 `APR-03`).
- Vistoriador só lança `manutencao` (403 nas outras).
201. Regras: FIN-05, FIN-06, APR-03.

### POST /api/financeiro/despesas/{id}/pagar/
Perfis: administrador, financeiro. Corpo: `{ forma: "pix" | "boleto" | "cartao" | "transferencia" | "dinheiro", pago_em, comprovante? }`. Só `a_pagar`. `dinheiro` sai do caixa aberto. 200 `paga`.

A aprovação e a recusa (`aguardando_aprovacao` → `a_pagar` ou `recusada`) passam pelo pedido em `aprovacoes.md`.

---

## Interface de pagamentos (para a T-029)

`backend/integracoes/pagamentos/base.py` define a interface; `falso.py` é a implementação padrão em desenvolvimento e testes; `asaas.py` é a real (ADR 0007). Só `financeiro` e `plataforma` chamam a interface, e a chave da subconta só é decifrada dentro dela (S-05).

```python
class ProvedorPagamentos(Protocol):
    def criar_subconta(self, empresa: DadosEmpresa) -> Subconta: ...                   # passo "Recebimentos"
    def criar_cobranca(self, conta: ContaPagamentoRef, pedido: PedidoCobranca) -> Cobranca: ...
        # PedidoCobranca: tipo (pix|boleto|cartao_link), valor_centavos, vencimento,
        #                 referencia_externa (id da ContaReceber ou da FaturaAssinatura), pagador (nome, documento, contato)
    def cancelar_cobranca(self, conta, cobranca_id: str) -> None: ...
    def consultar_cobranca(self, conta, cobranca_id: str) -> SituacaoCobranca: ...
        # status (aguardando|paga|vencida|cancelada|estornada), valor_pago_centavos, pago_em, forma
    def criar_autorizacao_recorrente(self, conta, pedido: PedidoRecorrencia) -> Autorizacao: ...  # Pix Automático ou cartão
    def cobrar_com_autorizacao(self, conta, autorizacao_id: str, pedido: PedidoCobranca) -> Cobranca: ...
    def cancelar_autorizacao(self, conta, autorizacao_id: str) -> None: ...
    def validar_webhook(self, cabecalhos: Mapping[str, str], corpo: bytes) -> EventoWebhook | None: ...
        # devolve provedor, evento_id, tipo, cobranca_id, referencia_externa; None se o token não confere
```

- Valores sempre em centavos; datas como `date`. Nenhum tipo do SDK do parceiro sai da interface.
- A implementação falsa guarda as cobranças em memória e oferece `simular_pagamento(cobranca_id, valor_centavos=None)` para os testes (CA-017-07).
- `ContaPagamentoRef` é a conta principal do Giro (faturas, `plataforma`) ou a subconta da empresa (`plataforma.ContaPagamento`).

## Webhooks (FIN-04, AUT-05, S-14)

### POST /api/webhooks/pagamentos/asaas/
Servido no host `admin.<dominio>` (schema `public`), sem autenticação de usuário. Rate limit por IP.
1. `validar_webhook` confere o token do cabeçalho com `hmac.compare_digest` contra o `webhook_token_hash` de cada `ContaPagamento` (e da conta principal). Não confere → 401 e nada é gravado.
2. Acha a empresa pela conta, entra no schema dela e grava `WebhookRecebido` (`provedor`, `evento_id` **único**, `recebido_em`, corpo bruto). Evento repetido → 200 sem fazer nada (idempotência, CA-017-07).
3. Responde **200** na hora. Não baixa nada dentro da requisição.
4. A task `aut_05_processar_webhook(schema, webhook_id)` consulta a cobrança no parceiro (`consultar_cobranca`, com a chave da subconta) e **não confia no corpo do webhook**:
   - paga e `valor_pago_centavos == CobrancaExterna.valor_centavos` → baixa a conta (`forma` = `pix` ou `boleto`), registra a entrada no caixa se a cobrança foi gerada no caixa, publica `financeiro.parcela_paga` e envia o recibo por WhatsApp. Ator da auditoria: `sistema`, regra `AUT-05`.
   - paga com valor diferente → não baixa; cria uma pendência para o financeiro (`PendenciaPagamento`) e avisa o administrador e o financeiro.
   - estornada no parceiro → pendência, nunca reabre sozinha.
   - `processado_em` e `resultado` gravados no `WebhookRecebido`.
O mesmo fluxo vale para a `FaturaAssinatura` no `public` (`plataforma`).

`GET /api/financeiro/pendencias-pagamento/` e `POST .../{id}/resolver/` `{ acao: "baixar" | "ignorar", motivo }` · administrador, financeiro.

---

## Eventos e interface interna

| Item | Uso |
| --- | --- |
| `financeiro.services.criar_contas_da_origem(origem, contas)` | locações (parcelas e caução), devolução (saldo negativo, `DEV-02`). |
| `financeiro.services.pagar_com_caucao(conta_caucao, cobrancas)` | acerto da devolução (`vistorias.md`): cobranças pagas com `forma = caucao`. |
| `financeiro.services.devolver_ao_cliente(origem, valor, forma)` | cria o `Reembolso`. |
| `financeiro.services.cancelar_contas_da_origem(origem, motivo)` | locação cancelada antes da retirada. |
| evento `financeiro.parcela_paga` | `locacoes` (1º pagamento), `clientes` (desbloqueio `CLI-05`). |
| evento `financeiro.parcela_atrasou` | tarefa diária às 09:00 junto da régua (`AUT-03`): publica para cada conta que completou 1, 3, 7 e 15 dias de atraso; `clientes` bloqueia no 15º (CA-017-11: vencida em 23 set → bloqueio em 08 out). |
| anotações fornecidas (ADR 0015) | bloco `financeiro` de `clientes`, `indicadores_financeiros` de `veiculos` (`VEI-05`), contador de caixas abertos para `filiais` (`FIL-06`), filtro `em_aberto`. |
| tarefas | `aut_03_regua_de_cobranca` (09:00), `aut_04_cobranca_recorrente` (no vencimento), `aut_05_processar_webhook`, `aut_08_fechamento_automatico_do_caixa` (23:59). |

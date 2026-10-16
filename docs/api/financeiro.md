# Financeiro: contas a receber, caixa do dia, despesas e pagamentos

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-043), emendas de 09 out 2026 (T-088) 12 out 2026 (T-144, diferenças da T-017) e 13 out 2026 (T-177, despesas: busca, exportar, despesa por veículo, nota obrigatória) · **App:** `financeiro` (schema da empresa) · **Regras:** FIN-01 a FIN-08, FIN-16, AUD-07, APR-03, APR-04, APR-09, LOC-04, LOC-05, LOC-07, CLI-05, DEV-02, FIL-06, AUT-03, AUT-04, AUT-05, AUT-08 · **ADRs:** 0007, 0011, 0012, 0014 · **Segurança:** S-05, S-14 · **Critérios:** `docs/qa/criterios/T-017.md`, `docs/qa/criterios/despesas.md` · **Telas:** Receber, Caixa, Despesas, Financeiro

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
| Lançar despesa como paga no caixa (`FIN-05`) | sim | sim | sim (sua filial) | — | sim |
| Exportar as despesas em CSV (`FIN-16`, `AUD-07`) | sim | — | — | — | sim |
| Aprovar despesa acima de R$ 500 (`APR-03`) | sim | sim | — | — | — |
| Pagar despesa, marcar devolução ao cliente como feita | sim | — | — | — | sim |

Quem lançou ou pediu não aprova o próprio pedido, salvo o administrador (`APR-09`, T-249; `aprovacoes.md`, "Administrador decide o próprio pedido"). O vistoriador recebe 403 em todo o app.

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
  "forma_prevista": "pix_automatico", "dias_atraso": 7, "observacao": null,
  "valor_hoje": { ... },
  "pago_em": null, "forma": null, "multa_centavos": 0, "juros_centavos": 0,
  "estorno_de": null, "estornada_em": null,
  "cobranca_aberta": { "id": 55, "tipo": "pix", "vence_em": "...", "pix_copia_e_cola": "...", "qr_code_url": "..." },
  "acoes": { "receber": true, "gerar_pix": true, "gerar_boleto": true, "cobrar": true,
             "cancelar": true, "renegociar": true, "estornar": false }
}
```

- `tipo`: `parcela`, `caucao`, `multa`, `avaria`, `acerto`, `outro`. Caução não é receita (`LOC-04`): não entra em "previsto", "recebido" nem "em aberto".
- `status` como na `FIN-01`: o banco guarda `aberta`, `paga`, `cancelada`, `renegociada`; a API devolve `vence_hoje` (vencimento hoje) e `atrasada` (vencimento antes de hoje) para contas `aberta`, sem tarefa à meia-noite.
- `faixa_atraso` (`FIN-02`): `1_7`, `8_30`, `mais_30`, ou `null` (não atrasada).
- `dias_atraso` (T-144): o mesmo `valor_hoje.dias_atraso`, repetido no topo para a coluna da lista; 0 quando não está atrasada.
- `observacao` (T-144): texto curto (até 150) que o serviço de origem grava na conta; `null` quando vazio. Só leitura.
- `estorno_de` e `estornada_em` (T-144): ver o estorno abaixo. `estorno_de` é o `id` da conta original (na conta nova); `estornada_em` é quando a original foi estornada.

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
- Com `?cliente=`, `?origem_tipo=&origem_id=` ou `?busca=`, as contagens contam só as contas desse recorte, sem a caução, e a lista continua trazendo a caução (Lucas em 07 out: 2 linhas, parcela e caução; `todas` 1). `?situacao=`, `?faixa=` e `?forma=` não mudam as contagens, e os indicadores são sempre os da filial (ou de todas, com `X-Filial: todas`), sem filtro. Com só `?periodo=` e esses recortes, `?situacao=` devolve exatamente as contas contadas na aba (T-148, FIN-15).
- Com `?periodo=mes`, `previsto_mes_parcelas` = `pagas` + `vencem_hoje` + `a_vencer` + as atrasadas que vencem no próprio mês (aqui nenhuma: Carlos venceu em 30 set e Rafael em setembro), então 30 + 6 + 92 = 128.
- O contador `receber` de `GET /api/painel/contadores/` é `contagens.atrasadas` (`FIN-15`; seed: 2).

Caso do seed (`FIN-15`, linha "Contas a receber de outubro em 07 out" das regras, carteira em `docs/qa/carteira-outubro/`): Filial Centro, `?periodo=mes`, em 07 out. A vencer soma 3597460 em 92 parcelas.

### GET /api/financeiro/contas-receber/{id}/
200: representação mais `historico`, do mais antigo para o mais novo (T-144):
```json
"historico": [ { "em": "2026-10-07T13:02:00Z", "acao": "conta_receber.cobrar", "por": null, "motivo": null },
               { "em": "2026-10-07T13:02:00Z", "acao": "cobranca.pix", "por": null, "motivo": null } ]
```
- `acao` é o código do evento de auditoria da conta (`conta_receber.criar`, `.pagar`, `.cobrar`, `.cancelar`, `.renegociar`, `.estornar`, `.ajustar_valor`) ou `cobranca.pix` / `cobranca.boleto` para cada cobrança gerada. O frontend traduz o código em texto; código desconhecido aparece como está.
- `por`: nome de quem fez, `null` para o sistema. `motivo`: o motivo informado, quando houver.

### POST /api/financeiro/contas-receber/
"Novo lançamento" avulso. Perfis: administrador, gerente, financeiro.
Corpo: `{ cliente_id, tipo: "multa" | "avaria" | "outro", descricao, vencimento, valor_centavos, origem?: { tipo, id } }`. 201.
As parcelas e a caução de locação **não** nascem aqui: vêm de `locacoes.services` (`locacoes.md`).

### POST /api/financeiro/contas-receber/{id}/receber/
Baixa no caixa (`FIN-04`: dinheiro e cartão). Perfis: quem recebe. A conta é achada em qualquer filial do escopo da pessoa, sem filtrar pelo `X-Filial` (`FIL-06`: paga-se no caixa de outra filial); lista e detalhe seguem o `X-Filial` (T-144).
Corpo: `{ "forma": "dinheiro" | "cartao_debito" | "cartao_credito", "valor_centavos": 30609 }`.
- Usa o caixa `aberto` da filial da requisição (`X-Filial`), que pode ser diferente da filial da conta (`FIL-06`); a conta mantém a filial de origem.
- `valor_centavos` tem que ser igual a `valor_hoje.total_centavos`. Diferente → 422 `{ "codigo": "FIN-01", "mensagem": "Não existe pagamento parcial. Receba o valor inteiro ou renegocie." }` (CA-017-06).
200: conta `paga`, com `forma`, `pago_em`, multa e juros gravados, e o `MovimentoCaixa` de entrada ligado. Publica `financeiro.parcela_paga`.
422 `{ "codigo": "FIN-07", "mensagem": "Abra o caixa do dia para receber" }` sem caixa aberto. 409 `transicao_conta` se não estiver `aberta`.

### POST /api/financeiro/contas-receber/{id}/cobranca/
"Gerar Pix" e boleto. Corpo: `{ "tipo": "pix" | "boleto", "vence_em"?: "2026-10-10", "no_caixa"?: false }`. A conta é achada como em `receber/` (`FIL-06`).
201: a `CobrancaExterna`:
```json
{ "id": 55, "tipo": "pix", "valor_centavos": 30609, "vence_em": "2026-10-07",
  "pix_copia_e_cola": "000201...", "qr_code_url": "...", "linha_digitavel": null, "boleto_url": null,
  "status": "aguardando" }
```
- O valor é o `valor_hoje` do dia; multa e juros ficam os do dia em que a cobrança foi gerada, e são esses que a baixa pelo webhook grava na conta (T-144). Pix vence no fim do dia, boleto na data pedida (`{ "vence_em" }`, padrão: vencimento da conta, ou hoje se já venceu).
- Gerar outra cobrança cancela a aberta no parceiro.
- `no_caixa: true` (T-144) é como a tela `Caixa` gera o Pix: a cobrança guarda o caixa `aberto` da filial do `X-Filial`, e a baixa pelo webhook entra como entrada `pix` nesse caixa (`FIN-07`). Sem caixa aberto: 422 `FIN-07` "Abra o caixa do dia para receber"; com `X-Filial: todas`: 400 `validacao` (`filial`). Se o caixa fechar antes do pagamento, a baixa acontece sem movimento (Pix não passa pela gaveta e caixa fechado não recebe movimento). Sem `no_caixa` (tela `Receber`, régua `AUT-03`), não passa pelo caixa.
- Sem subconta aprovada (`plataforma.ContaPagamento`): 422 `{ "codigo": "recebimentos_desligados", "mensagem": "Conecte os recebimentos para gerar Pix e boleto" }` (implantação, passo 10).
- Plano sem `recebimento_parceiro` (Essencial): 403 `PLT-12` ("Seu plano não inclui Pix e boleto automáticos. Para usar, mude de plano."), antes de olhar a subconta (`plataforma.md`, "Módulos por plano"). O cliente paga no caixa (`PLT-12`).

### POST /api/financeiro/contas-receber/{id}/cobrar/ · POST /api/financeiro/contas-receber/cobrar-em-lote/
"Cobrar" e "Cobrar todos pelo WhatsApp". Corpo do lote: `{ "ids": [ ... ] }` (até 100). 202 `{ "enviadas": 1 }` nos dois (T-144). `enviadas`: quantas contas foram cobradas (uma por conta, pelo WhatsApp, pelo e-mail ou pelos dois). Conta que não está `aberta`, cliente sem celular e sem e-mail ou conta já cobrada hoje não conta e não é erro. No dia do vencimento e em atraso, com os recebimentos ligados, a mensagem gera um Pix novo do valor do dia (o que cancela a cobrança aberta, como acima); antes do vencimento é só o lembrete, sem Pix. Envia a mensagem de cobrança com a marca da locadora (`AUT-03`), uma vez por conta por dia, pelo WhatsApp e por e-mail, com os textos de "Régua de cobrança: textos".

### POST /api/financeiro/contas-receber/{id}/cancelar/
Perfis: administrador, gerente, financeiro. Corpo: `{ motivo }`. Só `aberta`. 200 `cancelada`. Também chamado por serviço (locação cancelada antes da retirada, `LOC-12`).

### POST /api/financeiro/contas-receber/renegociar/
Corpo: `{ "contas": [9010], "novas": [ { "vencimento": "2026-10-15", "valor_centavos": 15000 }, { "vencimento": "2026-10-22", "valor_centavos": 15609 } ], "motivo": "..." }`.
201: as novas contas (`aberta`). Nasce uma `Renegociacao` (motivo, origem `cliente`, quem fez e quando): as originais vão para `renegociada`, com `renegociada_em` apontando para ela, e saem do em aberto (`FIN-01`); as novas guardam `nasceu_de` = a mesma `Renegociacao`. Assim cabem N originais em M novas, e uma conta nova pode ser renegociada de novo (T-114). Conta `paga` ou `cancelada` → 409.

### POST /api/financeiro/contas-receber/{id}/estornar/
Só `paga`. Corpo: `{ motivo }`. Conta paga não se edita: a correção é estorno (CA-017-09).
Conta paga com a caução (`forma = caucao`, `DEV-02`) não se estorna aqui: 422 `DEV-02` (T-144).
200: a original continua `paga` com `estornada_em`; nasce uma conta `aberta` igual (mesmo valor e vencimento) com `estorno_de` = original, e, se a baixa foi no caixa, um movimento de estorno no caixa aberto. Para **devolver dinheiro** ao cliente, use as devoluções abaixo, não o estorno.

### Cobrança recorrente (AUT-04)

Locação com `forma_pagamento = pix_automatico` (ou cartão recorrente) ganha uma autorização no parceiro na ativação (`AutorizacaoRecorrente`). No vencimento de cada parcela, `aut_04_cobranca_recorrente` cria a `CobrancaExterna` daquela conta usando a autorização; a baixa vem pelo webhook. A referência externa de cada cobrança é o `id` da conta, para casar o pagamento sem ambiguidade.

### Régua de cobrança: textos (AUT-03, AUT-05)

Textos fixados pelo produto (T-147, opção B da análise da T-017). Mudança de texto passa pelo produto. Os exemplos são do Carlos (LOC-2841, Street semanal R$ 299,40, 5 parcelas) e da Moto Rápida.

**Partes do texto**

- Abertura: `{marca}: olá, {primeiro nome}.`, com o nome da locadora, nunca Giro.
- Conta, pelo `tipo`, com a origem por extenso (`locação` ou `venda`) e o código:
  - `parcela`: "a parcela 2 de 5 da locação LOC-2841";
  - `acerto`, `multa`, `avaria`: "a cobrança de acerto da locação LOC-2841" (de multa, de avaria);
  - `outro`: "a cobrança da locação LOC-2841".
  No começo da frase, com maiúscula ("A parcela 2 de 5...").
- Valor: o `valor_hoje` do dia (`FIN-03`, `devido_ate`). A mensagem não faz conta.
- Pix: com os recebimentos ligados, "Pague pelo Pix copia e cola: {código}" (cobrança gerada como em `POST .../cobranca/`). Sem subconta (`recebimentos_desligados`), "Pague na loja ou fale com a gente por aqui."

**Mensagens**

| Momento | Texto (WhatsApp) | Assunto do e-mail |
| --- | --- | --- |
| D-1 | "Moto Rápida: olá, Carlos. A parcela 3 de 5 da locação LOC-2841, de R$ 299,40, vence amanhã, 07/10." | "Moto Rápida: lembrete de vencimento" |
| D0 | "Moto Rápida: olá, Carlos. A parcela 3 de 5 da locação LOC-2841, de R$ 299,40, vence hoje. Pague pelo Pix copia e cola: …" | "Moto Rápida: vence hoje" |
| D+3 e D+7 | "Moto Rápida: olá, Carlos. A parcela 2 de 5 da locação LOC-2841 venceu em 30/09. O valor hoje é R$ 306,09, com multa e juros. Pague pelo Pix copia e cola: …" (D+7, 07/10; em D+3, 03/10, R$ 305,69) | "Moto Rápida: conta em atraso" |
| "Cobrar" manual antes de D-1 | "Moto Rápida: olá, Carlos. A parcela 4 de 5 da locação LOC-2841, de R$ 299,40, vence em 14/10." | "Moto Rápida: lembrete de vencimento" |
| "Cobrar" manual em atraso, fora de D+3 e D+7 | o texto de D+3 e D+7, com o valor do dia | "Moto Rápida: conta em atraso" |
| Conta de outro tipo, D-1 | "Moto Rápida: olá, Carlos. A cobrança de acerto da locação LOC-2841, de R$ 365,37, vence amanhã, 10/10." | "Moto Rápida: lembrete de vencimento" |
| Recibo (`AUT-05`) | "Moto Rápida: recebemos R$ 306,09 por Pix em 07/10, da parcela 2 de 5 da locação LOC-2841. Este é o seu recibo." | (só WhatsApp, `AUT-05`) |

- Em atraso sem multa nem juros (contrato sem a cláusula, `contratos.selectors.permite_juros`), sai "O valor é R$ 299,40." sem "com multa e juros".
- Forma no recibo: "por Pix", "por boleto", "pelo Pix automático", "no cartão de crédito", "no cartão de débito", "em dinheiro". O dia é o do pagamento em `America/Sao_Paulo`; o valor, o total pago (principal, multa e juros).
- Canais (`AUT-03`): WhatsApp quando o cliente tem celular e e-mail quando tem e-mail; os dois quando tem os dois. Sem `cobranca_whatsapp` na empresa (Essencial, `PLT-12`, ADR 0024), só e-mail: cliente sem e-mail não recebe nada, e a conta segue na lista. Sem `recebimento_parceiro` (Essencial), nunca há Pix nem boleto na mensagem: vale o texto de `recebimentos_desligados` ("Pague na loja..."), e não há recibo da `AUT-05`. O e-mail sai com o nome da locadora como remetente e o mesmo texto no corpo. Cliente sem celular e sem e-mail não recebe nada, e a conta segue na lista de cobrança.
- Uma vez por conta por dia, contando os dois canais.

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
Corpo: `{ motivo }`. 201: movimento de estorno, no caixa aberto de hoje, com `estorno_de`, o mesmo `tipo` e a mesma `forma` do original; o resumo do dia desconta o estornado. O original não muda (CA-017-17). Estornar a entrada de uma conta recebida usa `contas-receber/{id}/estornar/`.

### POST /api/financeiro/caixas/{id}/fechar/
Corpo: `{ "contado_centavos": 28100, "motivo_diferenca": null }`.
- Contado = esperado → `fechado`, com `contado`, `esperado` e `diferenca_centavos = 0`.
- Diferente (falta ou sobra) → exige `motivo_diferenca` (400 `validacao` sem ele); o caixa vai para `aguardando_aprovacao` e nasce o pedido `APR-04`, avisando os gerentes da filial. Aprovado → `fechado` com a diferença registrada; recusado → volta a `aberto` para contar de novo.
- Depois de `fechado`, qualquer movimento nesse caixa → 409 `{ "codigo": "FIN-07", "mensagem": "Este caixa já foi fechado" }`.
Caso CA-017-15: contado 27100 com motivo "Troco errado" → `aguardando_aprovacao`, `diferenca_centavos: -1000`.

### Fechamento automático (FIN-08, AUT-08)
`aut_08_fechamento_automatico_do_caixa`, às 23:59 em `America/Sao_Paulo`: caixa ainda `aberto` → `fechado_sem_conferencia` (sem contado e sem diferença) e tarefa para os gerentes da filial. Caixa `aguardando_aprovacao` não é mexido.

---

## Despesas (FIN-05, FIN-06, FIN-16, APR-03)

### Representação
```json
{ "id": 801, "data": "2026-10-07", "descricao": "Pneus (2 unidades)", "categoria": "manutencao",
  "veiculo": { "id": 88, "placa": "PMZ3E17" }, "filial": { "id": 1 },
  "valor_centavos": 120000, "vencimento": "2026-10-07", "status": "aguardando_aprovacao",
  "pago_em": null, "forma": null, "lancada_por": { "id": 4, "nome": "João Silva" },
  "nota": { "url": "...", "url_expira_em": "..." }, "pedido_aprovacao_id": 91,
  "rotulo_situacao": "Aguardando gerente" }
```
`nota` vem `null` só nas despesas lançadas antes da nota obrigatória (T-177) e na que nascer da OS (`MAN-05`, fase 2).

### GET /api/financeiro/despesas/
Query: `?mes=2026-10` (padrão: o mês de hoje), `?status=`, `?categoria=`, `?veiculo=<id>`, `?busca=`. Filial pelo `X-Filial` (`todas` para administrador e financeiro).
200 (seed, Filial Centro, `?mes=2026-10&busca=pneu`):
```json
{
  "indicadores": {
    "gasto_mes_centavos": 706670, "despesa_por_veiculo_centavos": 8217,
    "aguardando_aprovacao_centavos": 120000, "aguardando_aprovacao_quantidade": 1,
    "a_pagar_semana_centavos": 41230,
    "por_categoria": { "fixas": 391230, "rastreamento": 172000, "manutencao": 124800, "impostos": 18640 }
  },
  "contagens": { "aguardando_aprovacao": 1, "a_pagar": 0, "paga": 0, "recusada": 0 },
  "resultados": [ { "id": 801, "descricao": "Pneus (2 unidades)", "...": "representação" } ],
  "proximo": null, "anterior": null
}
```
Caso do seed (CA-017-19, CA-DES-01): outubro na Filial Centro, **706670**; despesa por veículo **8217**; aguardando aprovação **120000** (só os pneus; o IPVA de 18640 nasce `a_pagar`).

Números da `FIN-16` (base: despesas da filial do `X-Filial`, ou de todas, com `data` no mês pedido):
- `gasto_mes_centavos`: soma do valor, pagas ou não, sem as `recusada`.
- `despesa_por_veiculo_centavos` (T-177): `gasto_mes_centavos` ÷ veículos da mesma filial (ou de todas) fora de `vendido` e `baixado`, contados no fim do último dia do mês em `America/Sao_Paulo`; no mês corrente e num mês futuro, hoje. Divisão em `Decimal`, arredondada **uma vez** para o centavo com `ROUND_HALF_UP`: 706670 ÷ 86 = 8217,09 → **8217**; com os pneus recusados e um veículo `baixado`, 586670 ÷ 85 = **6902** (CA-DES-02). Sem nenhum veículo, `null` (CA-DES-03): o frontend não mostra valor nem zero.
  - A contagem vem de uma função nova, `veiculos.selectors.frota_ativa_em(dia, filiais) -> int` (`financeiro` está abaixo de `veiculos` na ADR 0011), pelo último status do histórico (`HistoricoStatusVeiculo`) até o fim daquele dia: veículo cadastrado depois do dia não conta; o vendido ou baixado depois do dia conta. A filial é a atual do veículo (a troca de filial não tem histórico).
- `contagens`: uma chave por status, as despesas do mês. Seguem a `?busca=` (como em contas a receber); `?status=`, `?categoria=` e `?veiculo=` não mudam as contagens.
- **Os indicadores não mudam com nenhum filtro** (`?status=`, `?categoria=`, `?veiculo=`, `?busca=`): são sempre os do mês e da filial.

`?busca=` (`FIN-16`, T-177), dentro do mês e da filial:
- Acha a despesa quando o termo está na **descrição**, sem diferenciar maiúsculas, minúsculas e acentos ("oleo" acha "Óleo 1 litro"), **ou** na **placa** do veículo ligado, sem hífen nem espaço ("pmz-3e17" e "PMZ3E17" acham os pneus).
- Como fazer, sem extensão nova no PostgreSQL: a despesa ganha o campo `descricao_busca` (texto em minúsculas e sem acento, por `unicodedata` NFKD), gravado pelo serviço ao lançar, com migração de dados para as que já existem; o termo passa pela mesma função e entra em `descricao_busca__contains`. Para a placa, o termo passa por `veiculos.services.normalizar_placa` e entra em `veiculo__placa__contains` (a placa já é guardada assim); termo que fica vazio depois de normalizado não procura na placa. As duas condições se juntam com OU.
- Termo vazio ou só com espaços é ignorado; acima de 60 caracteres, 400 `validacao` no campo `busca`.
- Casos (CA-DES-04, CA-DES-05): "pneu" → só os pneus, contagens `aguardando_aprovacao` 1, `a_pagar` 0, `paga` 0, `recusada` 0, indicadores iguais aos sem busca; "pmz-3e17" → só os pneus; "ROE" → só "IPVA ROE-2A88"; "oleo" → só o óleo.

### POST /api/financeiro/despesas/
`multipart/form-data`: `descricao`, `valor_centavos`, `data`, `vencimento`, `categoria` (`fixas`, `manutencao`, `rastreamento`, `impostos`, `pessoal`, `outros`), `veiculo_id?`, `nota` (imagem ou PDF até 10 MB, **obrigatória**, `FIN-06`), `pago_no_caixa?` (bool). A filial é a do `X-Filial`, como hoje. Não há `forma` no lançamento: com `pago_no_caixa`, a forma é sempre dinheiro.
- Até 50000 (R$ 500,00) → `a_pagar`; com `pago_no_caixa`, nasce `paga`, forma `dinheiro`, com um movimento de saída em dinheiro no caixa aberto de hoje da filial (CA-DES-11).
- Acima de 50000 → `aguardando_aprovacao` e pedido `APR-03`.
- `data` e `vencimento` são obrigatórios. A tela começa com o vencimento igual à data (CA-DES-10); a API não copia um no outro.

Erros, nesta ordem. Em nenhum deles algo é gravado: nem a despesa, nem a nota no storage, nem o movimento no caixa.
1. 403 `{ "codigo": "FIN-06", "mensagem": "Seu perfil lança só despesas de manutenção." }`: vistoriador com outra categoria (como hoje).
2. 403 `{ "codigo": "FIN-05", "mensagem": "Seu perfil não paga despesa pelo caixa." }`: `pago_no_caixa: true` de quem não abre e fecha caixa (tabela "Quem pode": o vistoriador), CA-DES-14.
3. 400 `validacao` por campo: sem `nota`, `{ "nota": ["Envie a foto da nota."] }` (CA-DES-15); arquivo fora de imagem ou PDF, ou acima de 10 MB, com as mensagens de `comum.arquivos`; os outros campos como hoje.
4. 422 `{ "codigo": "APR-03", "mensagem": "Despesa acima de R$ 500,00 precisa da aprovação do gerente antes de ser paga." }`: `pago_no_caixa` acima de 50000, com ou sem caixa aberto (CA-DES-13).
5. 422 `{ "codigo": "FIN-07", "mensagem": "Abra o caixa do dia para pagar por ele" }`: `pago_no_caixa` sem caixa `aberto` hoje na filial, fechado ou não aberto (CA-DES-12). Muda só a mensagem; hoje o serviço diz "Abra o caixa do dia para pagar no caixa".

201: a representação. Regras: FIN-05, FIN-06, FIN-07, APR-03.

A nota obrigatória vale para o lançamento por esta rota. A despesa que nascer da OS concluída (`MAN-05`, fase 2) é criada pelo serviço de manutenção, sem passar por aqui, e segue as regras dela: `lancar_despesa` continua aceitando `nota=None`, e quem exige a nota é a rota. O seed lança as 6 despesas de outubro com nota (um PDF pequeno de exemplo).

### GET /api/financeiro/despesas/{id}/
200: a representação (T-144). Mesmos perfis e o mesmo `X-Filial` da lista; fora do escopo, 404.

### POST /api/financeiro/despesas/{id}/nota/
Anexar a nota depois (T-286, `MOV-04`, CA-246-14). Perfis: quem lança despesa (`despesas_lancar` = `todas`). `multipart/form-data`: `nota` (imagem ou PDF até 10 MB, `comum.arquivos`). Só na despesa sem nota; com nota, 409 `{ "codigo": "nota_existente" }`. Vale em qualquer status, inclusive `paga`. 200: a despesa, com `sem_nota: false`. Evento `despesa.anexar_nota`.

- **Origem `movimentacao` e `sem_nota` (T-286, ADR 0028, item 5).** A despesa da parada de uma movimentação nasce por `lancar_despesa(..., origem=...)`, com `origem_tipo = movimentacao` e o código `MOV-0001`, sem passar pela rota de lançamento; por isso pode nascer sem nota. A representação da despesa (lista e detalhe) ganha `sem_nota` (`true` quando não há nota) e `origem` (`{ "tipo": "movimentacao", "id", "codigo": "MOV-0001" }` ou `null`). A tela `Despesas` mostra a marca "sem nota" e o link para a movimentação. A rota `POST /api/financeiro/despesas/` continua exigindo a nota (`FIN-06`).

### POST /api/financeiro/despesas/{id}/pagar/
Perfis: administrador, financeiro. Corpo: `{ forma: "pix" | "boleto" | "cartao" | "transferencia" | "dinheiro", pago_em, comprovante? }`. Só `a_pagar`. `dinheiro` sai do caixa aberto. 200 `paga`.

A aprovação e a recusa (`aguardando_aprovacao` → `a_pagar` ou `recusada`) passam pelo pedido em `aprovacoes.md`.

### Exportar as despesas (`FIN-16`, `AUD-07`, T-177)

O botão "Exportar" da tela `Despesas`, só para o administrador e o financeiro (decisão do dono, 13 out 2026, no PR #187; o botão aparece com `pode.despesas_exportar`, `contas.md`), pede `POST /api/exportacoes/` com `{ "itens": ["despesas"], "formato": "csv", "mes": "2026-10", "filial_id": 1 | null }`, com o mês e a filial da tela (`null` = todas). A busca e a aba escolhidas não vão no pedido (CA-DES-07). O fluxo, o arquivo, as colunas e o texto em "Exportações recentes" estão em `auditoria.md`, "Despesas em CSV". As linhas do arquivo vêm de `financeiro.exportacao.linhas_das_despesas`, registrada no `auditoria` (seção "Eventos e interface interna", abaixo).

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
- `validar_webhook` (T-144) só lê o corpo e o token do cabeçalho e devolve o `EventoWebhook` com o `token` (ou `None` se o corpo não é um aviso). Quem confere o token é a view (passo 1 abaixo), porque o hash fica em `plataforma.ContaPagamento`, que o provedor não conhece.
- `ContaPagamento.chave_api_cifrada` entra na T-029 com o Asaas real; até lá, o provedor falso não precisa de chave.
- `ContaPagamentoRef` é a conta principal do Giro (faturas, `plataforma`) ou a subconta da empresa (`plataforma.ContaPagamento`).
- Para a assinatura (T-183, ADR 0023), a conta principal ganha `criar_ou_atualizar_pagador` (a empresa como cliente da conta principal), `cobrar_cartao_salvo(conta, token, pedido)` e, em `SituacaoCobranca`, `cartao` (token, bandeira, final) quando o pagamento foi no cartão. O número do cartão nunca entra na interface: o cartão é digitado na página do parceiro (`cartao_link`).

## Webhooks (FIN-04, AUT-05, S-14)

### POST /api/webhooks/pagamentos/asaas/
Servido no host `admin.<dominio>` (schema `public`), sem autenticação de usuário. Rate limit de 120 por minuto por IP (`webhook_ip`), contando também os recusados: 429 acima disso. Fora do OpenAPI.
1. `validar_webhook` extrai o evento e o token. A view calcula o SHA-256 do token e procura a `ContaPagamento` pelo `webhook_token_hash` (coluna única), conferindo com `hmac.compare_digest` (T-144). O token é aleatório e longo, por isso o hash sem sal basta e a busca pelo hash não vaza nada por tempo. Sem token, token que não confere ou corpo que não é aviso → 401 `{ "codigo": "webhook_invalido" }` e nada é gravado. A conta principal (`FaturaAssinatura`) entra na T-029.
2. Acha a empresa pela conta, entra no schema dela e grava `WebhookRecebido` (`provedor`, `evento_id` **único**, `recebido_em`, o evento extraído e o corpo recebido). Evento repetido → 200 sem fazer nada (idempotência, CA-017-07).
3. Responde **200** na hora. Não baixa nada dentro da requisição.
4. A task `aut_05_processar_webhook(schema, webhook_id)` consulta a cobrança no parceiro (`consultar_cobranca`, com a chave da subconta) e **não confia no corpo do webhook**:
   - paga e `valor_pago_centavos == CobrancaExterna.valor_centavos` → baixa a conta (`forma` = `pix` ou `boleto`), registra a entrada no caixa se a cobrança foi gerada no caixa, publica `financeiro.parcela_paga` e envia o recibo por WhatsApp. Ator da auditoria: `sistema`, regra `AUT-05`.
   - paga com valor diferente → não baixa; cria uma pendência para o financeiro (`PendenciaPagamento`) e avisa o administrador e o financeiro.
   - estornada no parceiro → pendência, nunca reabre sozinha.
   - paga, mas a conta já não está `aberta` (cancelada, renegociada, paga por outro caminho) → pendência, não baixa (T-144).
   - cobrança que a empresa não conhece → só registra o resultado `cobranca_desconhecida`.
   - a task trava o `WebhookRecebido` e não repete o que já tem `processado_em`.
   - `processado_em` e `resultado` gravados no `WebhookRecebido`.
O mesmo fluxo vale para a `FaturaAssinatura` no `public` (`plataforma`).

`GET /api/financeiro/pendencias-pagamento/` e `POST .../{id}/resolver/` `{ acao: "baixar" | "ignorar", motivo }` · administrador, financeiro. Pendências e avisos do webhook vão para todos os administradores e financeiros ativos.

---

## Eventos e interface interna

| Item | Uso |
| --- | --- |
| `financeiro.services.criar_contas_da_origem(origem, contas)` | locações (parcelas e caução), devolução (saldo negativo, `DEV-02`). |
| `financeiro.services.pagar_com_caucao(origem, disponivel, abertas, cobrancas, dia, vencimento_do_saldo)` | acerto da devolução (`vistorias.md`, `DEV-02`, T-114). Ordem: as parcelas em aberto, inteiras, da mais antiga para a mais nova, cada uma pelo `devido_ate(conta, dia)`, pagas com `forma = caucao` (multa e juros gravados na conta); a primeira que não cabe e todas as seguintes vão para `renegociada` (auditoria `conta_receber.renegociar`, regra `DEV-02`), ligadas por uma `Renegociacao` de origem `devolucao`, sem `por`. Depois, as outras cobranças viram contas pagas com a caução, até onde ela der. O que sobra abate as renegociadas. O que falta vira **uma** conta `acerto`, com vencimento em 3 dias e `nasceu_de` = a `Renegociacao`, igual a `-saldo` do acerto. Com saldo negativo, nenhum `Reembolso`. |
| `financeiro.selectors.devido_ate(conta, dia)` | **a única conta da `FIN-03`** (T-114): principal, multa e juros pro rata (`comum.dinheiro.juros_pro_rata`, um arredondamento só) até `dia`, contando o atraso do dia seguinte ao vencimento, ou ao dia em que a conta nasceu, se nasceu vencida. Taxas da configuração da empresa. Sem a cláusula no contrato da origem (`contratos.selectors.permite_juros`), sem multa e juros. O acerto da devolução, o `valor_hoje` e o recebimento no caixa (T-017) usam esta função. Ex.: 29940 vencida em 30 set, em 07 out → 30609. |
| `financeiro.services.devolver_ao_cliente(origem, valor, forma)` | cria o `Reembolso`. |
| `financeiro.services.cancelar_contas_da_origem(origem, motivo)` | locação cancelada antes da retirada. |
| evento `financeiro.parcela_paga` | `conta_id`, `cliente_id`, `tipo`, `origem_tipo`, `origem_id`, `valor_centavos`, `pago_em`. Assinado por `locacoes` (1º pagamento) e `clientes` (desbloqueio `CLI-05`). |
| evento `financeiro.parcela_atrasou` | `conta_id`, `cliente_id`, `tipo`, `origem_tipo`, `origem_id`, `vencimento`, `dias_atraso`. Tarefa diária às 09:00 junto da régua (`AUT-03`): publica para cada conta que completou 1, 3 e 7 dias de atraso e, a partir de 15 dias, uma vez por conta (a conta guarda `bloqueio_pedido_em`; se a tarefa não rodou no 15º dia, publica na próxima vez, `AUT-03`); `clientes` bloqueia com 15 dias ou mais (CA-017-11: vencida em 23 set → bloqueio em 08 out). Depois do desbloqueio manual (`CLI-05`), a mesma conta não pede o bloqueio de novo. |
| anotações fornecidas (ADR 0015) | bloco `financeiro` de `clientes` (com `conta_mais_antiga_id`), bloco `historico` da análise de `clientes`, contadores `contas_atrasadas_15_dias` e `em_aberto_centavos` por cliente, `indicadores_financeiros` de `veiculos` (`VEI-05`), contador de caixas abertos para `filiais` (`FIL-06`), filtro `em_aberto`. |
| item de exportação `despesas` (T-177) | `financeiro/exportacao.py` registra no `auditoria` (`auditoria.exportacao.registrar_item`) a validação do pedido, as linhas do CSV e o texto de "Exportações recentes" (`auditoria.md`, "Despesas em CSV"). |
| tarefas | `aut_03_regua_de_cobranca` (09:00), `aut_04_cobranca_recorrente` (no vencimento), `aut_05_processar_webhook`, `aut_08_fechamento_automatico_do_caixa` (23:59). |

# Locação com intenção de compra: tipo da locação, plano de compra, quitação por evento e a venda mínima

**Status:** aceita · 03 nov 2026 · T-420 (regras: `LOC-16`, `VEN-11`, tabela de transições do veículo `alugado` → `vendido`, `LOC-04`, `LOC-05`, `LOC-10`, `LOC-12`, `LOC-15`, `VEN-06`, `VEN-07`, `FIN-09`, `FIL-02`; critérios CA-420-01 a 17; decisões do dono de 29 e 30 out 2026) · detalha a 0011, a 0012 e a 0015 · vale com o padrão A dos dois pontos em aberto da `LOC-16` (plano de compra em `Precos`; encerramento sem multa)

## Contexto

A `LOC-16` cria um segundo tipo de locação: parcelas fixas, caução abatida na última e, ao quitar, o veículo passa ao cliente. A `VEN-11` faz nascer, na quitação, uma venda de R$ 0,00. Quatro pontos são caros de desfazer:

1. **A ordem dos apps (ADR 0011).** `vendas` (12) está abaixo de `locacoes` (10). A quitação nasce em `locacoes`, mas a venda é de `vendas`: `locacoes` não pode importar `vendas`.
2. **O app `vendas` está vazio.** A `VEN-11` precisa de uma `Venda` agora, antes do módulo de vendas (T-418 e seguintes). Criar só uma tabela "provisória" obrigaria a migrar dado depois.
3. **De onde vêm o valor e o prazo.** O padrão A do produto é um plano de compra cadastrado em `Precos`. O `PlanoEspecial` (`LOC-01`) tem outra forma (preço fixo ou desconto a partir de um período, várias categorias) e não diz número de parcelas.
4. **A "tarefa" da transferência.** Hoje "tarefa aos gerentes" (`AUT-06`) é só aviso. A da transferência se fecha à mão ("Transferência feita" e a data) e fica no histórico do veículo: precisa de estado.

## Decisão

### 1. `Locacao.tipo` e o plano congelado

`locacoes.Locacao` ganha:

| Campo | Tipo | Observação |
| --- | --- | --- |
| `tipo` | enum `comum`, `intencao_compra`, padrão `comum` | imutável depois do rascunho |
| `plano_compra` | FK → `PlanoCompra`, nulo | só no `intencao_compra` |
| `compra_parcelas` | smallint, nulo | congelado na confirmação (`LOC-15`) |
| `compra_valor_parcela_centavos` | centavos, nulo | congelado na confirmação |
| `quitada_em` | momento, nulo | a quitação (`LOC-16`) |

- `CHECK`: `tipo = 'comum'` com os quatro campos nulos; `tipo = 'intencao_compra'` com `plano_compra`, `compra_parcelas` e `compra_valor_parcela_centavos` preenchidos e `desconto_pct = 0`. Os extras (`LOC-02`) são recusados no serviço (400), como o desconto.
- `periodicidade` e `periodos` continuam sendo o calendário: `periodicidade` do plano e `periodos = compra_parcelas`. O fim previsto, as datas das parcelas e a 1ª parcela na retirada saem do código de hoje (`LOC-05`, ADR 0035), sem caminho novo.
- A caução é a da categoria, como na comum (`LOC-04`). A última parcela nasce com `compra_valor_parcela_centavos − caução`, no mínimo 0; a sobra (caução maior que a parcela, `max(0, caução − parcela)`) é calculada na quitação, não guardada, e devolvida ao cliente como a sobra da caução no acerto (`DEV-02`, CA-420-14).
- **Onde o tipo muda o fluxo comum**, todos em `locacoes.services` e por um único `if locacao.tipo == INTENCAO_COMPRA`: renovar e trocar (409 `LOC-16`); a `AUT` do atraso da devolução (`LOC-10`) ignora o tipo; o encerramento antes do fim (`LOC-12`) não calcula multa nem crédito (`LOC-13`), e cancela só as parcelas que vencem depois do dia; o novo "encerrar por atraso" (gerente e administrador, com motivo, sem `APR-02`) entra no mesmo núcleo.

### 2. `locacoes.PlanoCompra`, separado do `PlanoEspecial`

Model novo no app `locacoes`, ativável: `nome` texto(60) único, `categoria` FK → `veiculos.Categoria`, `periodicidade` enum `semanal`, `mensal`, `parcelas` smallint (`CHECK` 2 a 260), `valor_parcela_centavos` centavos (`CHECK` > 0), `condicoes` texto. Cadastro pelo administrador, como as categorias e os preços. Mudar o plano não muda locação confirmada (os campos congelados do item 1). Não reaproveitamos o `PlanoEspecial`: o `CHECK` dele já amarra `regra`, e um terceiro valor de regra deixaria metade dos campos sem sentido nos dois lados.

Se o dono escolher o padrão B (tabela da categoria com o prazo escolhido), o `PlanoCompra` sai e `compra_valor_parcela_centavos` passa a vir do preço da categoria; os campos congelados da locação não mudam.

### 3. Contrato: uma finalidade a mais

`contratos.Finalidade` ganha `locacao_compra` ("Locação com intenção de compra"), com um modelo pronto do Giro em `contratos.prontos`. `locacoes` pede o modelo publicado pela finalidade do tipo; sem ele, a confirmação é recusada (422 `LOC-16`, com o atalho para publicar, como a `IMP-04`). `contratos` continua sem conhecer a locação (origem genérica).

### 4. A quitação é de `locacoes`, a venda é de `vendas`, por evento

```
financeiro.parcela_paga ──► locacoes.eventos ──► locacoes.services.quitar_se_pago(locacao)
                                                     │  (todas as contas da locação pagas, nenhuma aberta)
                                                     │  locação → encerrada, quitada_em, auditoria do Sistema
                                                     │  sobra da caução: devolução pelo financeiro (DEV-02)
                                                     └─► publicar("locacoes.locacao_quitada", ...)
                                                              │
                                vendas.eventos ◄──────────────┘
                                  vendas.services.criar_venda_da_quitacao(...)
                                    Venda origem=quitacao_locacao, vendida, R$ 0,00
                                    veiculos.services.transicionar(veículo, "vendido", origem=venda)
                                    notificacoes: aviso aos gerentes da filial (FIL-02)
```

- Tudo na mesma transação (ADR 0011, eventos em processo): se a venda falha, a quitação volta, e nada fica pela metade.
- `quitar_se_pago` roda em todo `financeiro.parcela_paga` de uma conta da locação (parcela, caução, avaria): com a avaria aberta, pagar a 24ª não quita, e pagar a avaria depois quita (CA-420-13). Pagar várias parcelas de uma vez quita no último pagamento (CA-420-15). Idempotente: com `quitada_em` preenchido, não faz nada.
- O evento leva `locacao_id`, `codigo`, `filial_id`, `cliente_id`, `veiculo_id`, `vendedor_id` (quem criou a locação) e `quitada_em`. `vendas` não lê o model da locação; a FK `Venda.locacao` é permitida (vendas está abaixo).
- Quem passa o veículo a `vendido` é `vendas`, como em toda venda (`VEN-06`), com a origem na venda. A locação encerrada pela quitação **não** leva o veículo a `disponivel`: o encerramento pela quitação não tem devolução.
- O estorno de uma parcela depois da quitação não chama nada aqui: vira conta a receber do cliente, pelo `financeiro`.

### 5. `vendas.Venda` inteira, como no modelo de dados, com a origem

O backend cria agora a tabela do item 17 do modelo de dados inteira (para não migrar dado depois), com:

| Campo novo | Tipo | Observação |
| --- | --- | --- |
| `origem` | enum `balcao`, `quitacao_locacao`, padrão `balcao` | `VEN-11` |
| `locacao` | FK → `locacoes.Locacao`, nulo, único | só na quitação |
| `descricao` | texto(120), vazio | "Quitação da LOC-x" |
| `transferencia_feita_em` | data, nula | a tarefa do item 6 |
| `transferencia_registrada_por` | FK → `Usuario`, nulo | |

- `CHECK`: `origem = 'quitacao_locacao'` exige `locacao` e `preco_final_centavos = 0`. `forma` passa a nula (a quitação não tem forma).
- Nesta tarefa, `vendas.services` só tem `criar_venda_da_quitacao` e `registrar_transferencia`. O cancelamento (`VEN-07`) da venda de quitação responde 409 `VEN-11` desde já. Funil, conversão, meta e comissão (`VEN-08`, `VEN-09`, `FIN-09`) filtram `origem = 'balcao'` quando existirem.
- Leitura mínima agora: `GET /api/vendas/` e `GET /api/vendas/{id}/` (com o recurso `vendas_comissoes`) só com as vendas que existem (as da quitação), para a tela `Vendas` quando ela vier. Sem o recurso, a venda aparece no detalhe da locação e no histórico do veículo. O resto do módulo é da T-418 e seguintes.

### 6. A tarefa da transferência é a própria venda

Não há entidade genérica de tarefa. A pendência é a venda de quitação com `transferencia_feita_em` nula:

- ao nascer, os gerentes da filial da locação (`FIL-02`) recebem o aviso no sino e por e-mail, pelo `notificacoes`, com o texto da `LOC-16`;
- o painel do gerente lista as pendentes (`vendas.selectors.transferencias_pendentes(filiais)`, lido por `relatorios`, ADR 0015);
- "Transferência feita" é `POST /api/locacoes/{id}/transferencia/` `{ "feita_em": "2028-11-12" }`, só gerente e administrador da filial, com auditoria; a pendência sai e a linha fica no histórico do veículo (CA-420-16). A rota fica sob a locação, implementada em `apps/vendas/api` (como a troca de veículo em `vistorias`), porque `/api/vendas/...` só abre com o recurso `vendas_comissoes` (`PLT-12`), e a locação com intenção de compra existe em qualquer plano que aluga.

## Consequências

- A ordem dos apps não muda, e nenhuma ADR de dependência é reaberta.
- `vendas` deixa de ser vazio antes do módulo de vendas; a T-418 começa com a tabela pronta e com a regra de que só a `origem = 'balcao'` entra em funil, meta e comissão.
- O `if` do tipo fica em pontos contados de `locacoes.services` (renovar, trocar, atraso da devolução, encerramento, confirmação). Um terceiro tipo de locação pediria outra ADR para trocar o `if` por estratégia.
- O contrato da API (`docs/api/locacoes.md`, `docs/api/vendas.md` novo) e o modelo de dados saem na próxima parte do arquiteto, a partir desta ADR; o texto do andamento ("Parcela 5 de 24 · faltam 19 para a transferência") é montado por `locacoes.selectors` com as contas do `financeiro`.

# T-116 · Regra da devolução depois da data aprovada · produto → orquestrador, backend, frontend, qa

Em 10 out 2026, o dono do produto decidiu a `[decisão]` que o arquiteto levantou na revisão da T-114. Ficou a **opção B, com o ajuste**. No encerramento antecipado aprovado, vale o **dia da devolução**, e não o dia pedido (`cancelamento_data`):

- as parcelas que vencem até esse dia entram no acerto, com a multa e os juros da `FIN-03`;
- a multa da `LOC-12` e o crédito da `LOC-12` e da `LOC-13` são recalculados nesse dia, sobre o período em curso;
- o valor do pedido e da aprovação é uma estimativa;
- a aprovação não cancela parcelas. Quem cancela é o encerramento da devolução.

**O que foi feito:**

- **`docs/regras-de-negocio.md`:**
  - `LOC-12`: frase nova depois de "e acerto como numa devolução.".
  - `DEV-07`: frase nova depois de "e as que vencem depois são canceladas.", e o exemplo passou a citar o caso novo.
  - Notas de mudança da T-116, datadas de 10 out, no fim das seções Locação, Vistoria e devolução e Dados de referência.
  - Caso de referência novo: "Devolução antecipada depois da data aprovada".
  - Linha nova na tabela de decisões.
- **`docs/qa/criterios/T-016.md`:** CA-016-25.
- **`tarefas/backlog.md`:** a `[decisão]` da revisão da T-114 saiu e virou uma linha de registro.

**Por quê:**

- Na opção A (o código de hoje), o cliente fica com o veículo depois do dia aprovado sem pagar nada. A `LOC-10` não cobra, porque o fim previsto não passou. No mensal, ele ainda recebe de volta semanas que usou.
- A B ao pé da letra, sem o ajuste, cobra em dobro: a multa congelada incide sobre dias que a parcela seguinte já paga.
- As regras já falavam em "dia da devolução" e "dia do encerramento".

**Caso de referência (CA-016-25):** o Carlos, LOC-2841, tem a aprovação para 07 out (estimativa: multa 5988) e devolve em 16 out às 10:00.

| Item | Valor |
| --- | --- |
| Parcela 2 | 30699 |
| Parcela 3 | 30629 |
| Parcela 4 (14 out) | 30559 |
| Multa de encerramento | 5490 (5 dias do período de 14 a 21 out dão 4277, abaixo da diária de 5490) |
| Cobranças | 97377 |
| Caução | 30000 |
| **Cobrar** | **67377** |

Ao encerrar:

- a parcela 5 vai para `cancelada`;
- as parcelas 2, 3 e 4 vão para `renegociada`;
- a caução paga a multa e abate 24510;
- nasce uma conta `acerto` de 67377 com vencimento em 19 out.

Pela opção A, o acerto daria 37316.

**Casos de referência existentes:** nenhum muda. Em todos, a devolução cai no dia pedido:

- o CA-016-24 continua com 36537;
- a Patrícia (LOC-2812) continua com 8480 de multa e 28620 a devolver;
- a LOC-2836 continua com 18300.

## O que o backend precisa mudar (`locacoes`, `vistorias`)

1. **A aprovação não cancela parcelas.** Em `_aplicar_cancelamento` (`locacoes/services.py`), no ramo depois da retirada, sai o `financeiro.cancelar_abertas(..., vencendo_depois_de=dia)`. O ramo antes da retirada não muda: ele cancela tudo na hora, sem multa (`LOC-12`).
2. **O encerramento da devolução cancela pelo dia da devolução** (em `America/Sao_Paulo`): vão para `cancelada` as parcelas em aberto que vencem depois desse dia. Esse passo já existe e hoje só repete o cancelamento. Agora ele passa a ser o único. As que vencem até o dia entram no acerto como `parcela_aberta` (`DEV-01`).
3. **O acerto recalcula a multa e o crédito pelo dia da devolução,** com o mesmo cálculo de `cancelamento/simular` (`calcular_encerramento`).
   - Ele deixa de ler `multa_encerramento_centavos` e `credito_encerramento_centavos` congelados na aprovação. Esses campos ficam como a estimativa mostrada no pedido e na aprovação.
   - Em `credito_do_encerramento`, o mensal passa a usar o dia da devolução no lugar de `cancelamento_data`, para as semanas inteiras e para as parcelas que o encerramento cancela (`LOC-13`, mensal em 4 semanais).
   - A diária já usa a hora real da devolução e não muda.
4. **Devolução antes do dia pedido:** cai na mesma regra, porque tudo vale pelo dia da devolução. Não precisa de tratamento à parte.
5. **Entre a aprovação e a devolução,** as parcelas continuam como qualquer outra:
   - vencem, acendem `pagamento_atrasado` e contam para o bloqueio da `CLI-05`;
   - podem ser pagas no caixa ou por Pix. Uma parcela paga nesse intervalo não entra no acerto.
6. **Testes:**
   - `test_dev_07_ca_016_25_devolucao_depois_da_data_aprovada` (os números acima);
   - um teste de que a aprovação de 07 out deixa as parcelas 4 e 5 em aberto;
   - o CA-016-24 e o CA-015-29 continuam verdes sem mudar os números.
7. **Contrato:**
   - `docs/api/locacoes.md` passa a dizer, em "Cancelamento e encerramento antecipado", que `cancelamento.multa_centavos` e `devolver_centavos` são a estimativa para `data`, e que a aprovação não cancela parcelas. Hoje o texto diz que o acerto "inclui a multa e o crédito das semanas", sem dizer de qual dia.
   - `docs/api/vistorias.md`, linha do `multa_encerramento`: "calculado pelo dia da devolução".
   - O OpenAPI só muda se a descrição dos campos mudar.

## O que o frontend precisa mudar

1. **Pedido e aprovação do cancelamento** (detalhe da locação e a aprovação `APR-02`): a multa e o valor a devolver aparecem como estimativa. A frase é "Estimativa para 07 out. O valor final sai na devolução."
   - A data vem de `cancelamento` ou do `data` da simulação.
   - A tela não recalcula nada.
2. **Acerto da devolução:** a tela mostra a `multa_encerramento` e as parcelas que a API devolve. Se o valor for diferente da estimativa da aprovação, a tela não compara nem avisa por conta própria. Se o produto quiser esse aviso, ele vem da API em `acerto.avisos`, como os outros.
3. **Locação com o encerramento aprovado e ainda não devolvida:** as parcelas 4 e 5 continuam na lista como em aberto ou atrasadas. Não marque nenhuma como cancelada antes do encerramento.

## Próximo passo para quem recebe

- **Orquestrador:** abrir o PR e criar as tarefas de código (backend: itens 1 a 7; frontend: itens 1 a 3, depois do backend).
- **Backend:** implementar pelo CA-016-25, com os códigos `DEV-07` e `LOC-12` nos nomes dos testes.
- **QA:** validar pelo CA-016-25, e conferir de novo o CA-016-24 e o CA-015-29. Como no CA-016-24, a caução de 30000 da LOC-2841 vai na fixture.

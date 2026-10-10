# T-113 · Regras das decisões da T-109 · produto → orquestrador, backend, qa, arquiteto

Em 09 out 2026, o dono do produto decidiu os dois `[decisão]` que o backend levantou na T-109 e a devolução antes do fim sem encerramento antecipado aprovado:

1. **`DEV-02`, opção A com o ajuste:** a caução paga primeiro as parcelas em aberto, inteiras, da mais antiga para a mais nova, e depois as outras cobranças. A primeira parcela que não cabe inteira e as seguintes vão para `renegociada` e entram na conta única do saldo, com vencimento em 3 dias.
2. **`DEV-01`, opção B:** a parcela que vence no dia da devolução entra no acerto. As que vencem depois não entram.
3. **`DEV-07` (regra nova), opção A:** a devolução antes do dia do fim previsto exige o encerramento antecipado aprovado (`LOC-12`, `APR-02`), e as parcelas futuras são canceladas.

**O que foi feito:**

- **`docs/regras-de-negocio.md`:**
  - `DEV-01`: quais parcelas entram no acerto e por quanto (valor mais a multa e os juros da `FIN-03` até o dia da devolução).
  - `DEV-02`: a ordem do pagamento com a caução e a parcela que não cabe inteira, com exemplo.
  - `DEV-07`: regra nova.
  - `LOC-13`: o encerramento cancela só as parcelas que vencem depois do dia do encerramento, como já dizia o CA-015-29. O saldo não muda.
  - Notas de mudança em Locação, em Vistoria e devolução e nos Dados de referência; uma linha nova em "Decisões de 09 out 2026".
  - Caso novo "Devolução antecipada LOC-2841" (Carlos) nos dados de referência.
- **`docs/qa/criterios/T-016.md`:**
  - CA-016-13 corrigido: entra a parcela do dia, e cada parcela vale o devido com multa e juros.
  - CA-016-22 a 24 novos: a parcela que não cabe na caução, a devolução antes do fim e o caso do Carlos.
- **`tarefas/backlog.md`:** as duas `[decisão]` da T-109 saíram e viraram uma linha de registro.

**Casos de referência:** nenhum muda.

| Caso | Resultado |
|---|---|
| LOC-2836 | continua devolvendo R$ 183,00: as duas parcelas estão pagas e nenhuma vence em 14 out |
| Patrícia (LOC-2812) | continua devolvendo R$ 286,20 além da caução: não tem parcela em aberto |
| CA-016-11 | não muda: não tem parcela |
| CA-015-29 | não muda |

**Regras cobertas:** `DEV-01`, `DEV-02`, `DEV-07`, `LOC-13` (critérios CA-016-13, 22, 23 e 24).

## Para o backend: o que muda no código

**1. Itens do acerto** (`vistorias/services.py`, a montagem dos itens, hoje `vencimento__lt=dia`):

- Passar a `vencimento__lte=dia`: a parcela que vence no dia da devolução entra (`DEV-01`).
- O item `parcela_aberta` vale o valor mais a multa e os juros da `FIN-03` até o dia da devolução. Hoje ele soma `multa_centavos` e `juros_centavos` gravados na conta, que nascem 0.
- Não achei função que calcule a `FIN-03` (2% + 1% ao mês pro rata, conta que nasce vencida). Se ela não existe ainda, o acerto precisa dela. Combine com o arquiteto se ela fica em `financeiro` (a T-017 também vai usar).
- Conferência: a parcela de 29940 vencida em 30 set e devolvida em 07 out dá **30609** (CA-016-13 e CA-016-24).
- O texto do item da parcela do dia não pode dizer "venceu em": a parcela vence no dia.

**2. `financeiro.services.pagar_com_caucao`** (`DEV-02`):

- **Ordem:** as parcelas (`abertas`, já por `vencimento`, `id`) vêm primeiro, da mais antiga para a mais nova. Hoje, quando uma parcela não cabe, o laço faz `continue` e tenta a seguinte. Ele passa a **parar**: a primeira parcela que não cabe inteira e todas as seguintes vão para `renegociada`, com transição de estado e evento de auditoria, regra `DEV-02`, mesmo que uma seguinte coubesse.
- **Cobranças:** a sobra paga as outras cobranças, como hoje (a parte coberta vira conta paga com `forma = caucao`).
- **Conta do saldo:** depois das cobranças, o que sobrar da caução abate a conta do saldo. A conta `acerto` passa a valer a soma das parcelas renegociadas, mais a parte das cobranças sem cobertura, menos a sobra da caução. Isso sempre dá `-saldo` do `resultado`.
- Hoje a parcela que não cabe fica `aberta`/atrasada, e a sobra da caução não paga nada nem volta ao cliente. Exemplo: caução 30000, parcela de 32900 e avaria de 8500. A tela diz "cobrar R$ 114,00", mas o cliente fica devendo 32900, e 21500 da caução somem.
- **Ligação com a conta nova:** guardar na conta `acerto` (ou na `renegociada`) a referência às parcelas que ela substitui, para o extrato do cliente e a `CLI-05`. O arquiteto define o campo.
- **Invariante para teste:** com saldo negativo, nenhum `Reembolso`, e a conta `acerto` = `resultado.valor_centavos`. Com saldo positivo, todas as parcelas cabem, e nada muda.

**3. Encerrar a devolução** (`vistorias/services.py`, `encerrar`) (`DEV-07`):

- Se a chegada concluída é de um dia (em `America/Sao_Paulo`) anterior ao dia do fim previsto e a locação não tem `encerramento_antecipado_aprovado_em`, encerrar responde **422 `DEV-07`**, com a mensagem pedindo o encerramento antecipado (sugestão: "A devolução é antes do fim do contrato. Peça o encerramento antecipado ao gerente.").
- A devolução fica em `rascunho`, a locação e o veículo ficam como estavam, e nenhuma conta muda.
- Abrir a devolução e concluir a vistoria de chegada continuam permitidos.
- No próprio dia do fim, antes da hora, não é antecipada.
- O `acerto.resultado` dessa devolução pode trazer o aviso, para a tela mostrar sem calcular. Combine o campo com o arquiteto.
- **Com a aprovação:** as parcelas que vencem **depois do dia da devolução** vão para `cancelada`. `financeiro.services.cancelar_abertas(..., vencendo_depois_de=dia)` já faz isso. Confira que o `dia` é o da devolução e que a parcela do dia não é cancelada, porque ela entrou no acerto pelo item 1.
- No mensal em 4 semanais (`LOC-13`, T-111), o crédito menos as parcelas canceladas conta só as que vencem depois do dia. As que vencem até o dia já estão no acerto como `parcela_aberta`. Não podem contar duas vezes.

**4. Testes** (nome com o código da regra):

- `test_dev_01_*`: parcela do dia entra; parcela do dia seguinte fica fora; item com multa e juros (30609).
- `test_dev_02_*`: os dois casos do CA-016-22 (11400 e 11640) e a invariante conta = −saldo.
- `test_dev_07_*`: CA-016-23 (422 sem aprovação, no dia do fim passa) e CA-016-24 (Carlos: cobrar 36537, parcelas 2 e 3 `renegociada`, 4 e 5 `cancelada`, multa 5988 paga com a caução, conta `acerto` de 36537 vencendo em 10 out, locação `cancelada`).
- Os testes atuais do CA-016-09, 11, 13 e 14 continuam passando.

## Para o qa

- O CA-016-24 usa a LOC-2841 com caução de 30000 paga, que o seed ainda não tem (divergência da T-109 para a T-019). O teste grava a caução na fixture, como nos outros.
- A multa de encerramento de 5988 conta 7 dias restantes no período de 07 a 14 out (como os 8 da Patrícia, por data).

## Para o arquiteto

- Campo que liga a conta `acerto` às parcelas `renegociada`.
- Erro 422 `DEV-07` no `POST .../encerrar/`.
- Aviso de devolução antecipada no `acerto.resultado`.
- Onde fica o cálculo da `FIN-03`.
- Atualizar `docs/api/vistorias.md` ("Devolução") e `docs/api/financeiro.md` (`pagar_com_caucao`).

**O que ficou de fora:** nada das três decisões. Esta tarefa não muda código.

**Próximo passo:** o orquestrador abre o PR e cria a tarefa do backend com os itens 1 a 4 acima (depende da T-113; pode ir junto com a T-111, que mexe na `LOC-13`).

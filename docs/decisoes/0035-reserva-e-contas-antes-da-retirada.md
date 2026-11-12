# Reserva na confirmação, contas à espera da retirada e cancelamento automático

**Status:** aceita · 03 nov 2026 · T-410 (regras: tabela de transições do veículo, `LOC-05`, `LOC-12`, `FIN-03`, `AUT-17`, `MOV-03`; decisões do dono de 29 e 30 out 2026, PR #454) · detalha a 0011, a 0012 e a 0015

## Contexto

A T-410 muda três coisas que cruzam quatro apps:

1. **Reserva.** A locação confirmada reserva o veículo na hora, com qualquer data de início. Hoje `locacoes.services.confirmar` só reserva com início futuro, e o veículo da locação com início hoje ou passado fica `disponivel` até a retirada (a CDL-0B10 da LOC-2866 aparecia como disponível na Frota).
2. **Nada vence antes da retirada.** As contas da locação `aguardando_retirada` ficam `aberta`, sem `vence_hoje`, `atrasada`, sinal, régua, bloqueio nem análise do cliente, e a 1ª parcela e a caução pagas na retirada não têm multa nem juros. O vencimento gravado não muda.
3. **Cancelamento automático.** A locação não retirada até o 3º dia depois da data de início cai sozinha, com aviso aos gerentes no último dia.

O ponto caro de desfazer é o 2. O status `vence_hoje` e `atrasada` é calculado pela data (modelo de dados, item 18), em pelo menos oito lugares de `financeiro`, e também em `locacoes.leituras`, `vistorias.services` e `plataforma.services`. `financeiro` está abaixo de `locacoes` (ADR 0011): não pode perguntar o status da locação. Juntar a locação em cada consulta do Receber, do painel, da régua e do bloqueio seria uma junção entre apps em consultas de lista, que a ADR 0015 evita.

## Decisão

### 1. A conta guarda que espera a retirada

`financeiro.ContaReceber` ganha dois campos:

| Campo | Tipo | Quem grava | Uso |
| --- | --- | --- | --- |
| `aguarda_retirada` | bool, padrão `false` | `locacoes`, pelos serviços do `financeiro` | conta da locação `aguardando_retirada`: nunca fica `vence_hoje` nem `atrasada` |
| `liberada_em` | data, nula | o mesmo serviço, na retirada | dia local da retirada (`LOC-05`, `FIN-03`): o atraso não conta antes dele |

- **Quem liga:** `financeiro.services.criar_contas(..., aguarda_retirada=True)`, chamado por `locacoes.services.confirmar`. Toda conta que `locacoes` cria para uma locação `aguardando_retirada` nasce assim, inclusive as parcelas refeitas pela aprovação do desconto (`APR-01`).
- **Quem desliga:** `financeiro.services.liberar_contas_da_retirada(origem, dia)`, nova, chamada por `locacoes.services.verificar_ativacao` na mesma transação que leva a locação a `ativa`. Grava `aguarda_retirada = false` e `liberada_em = dia` em todas as contas da origem com `aguarda_retirada = true`, em qualquer status. Idempotente.
- **Cancelamento:** as contas abertas vão para `cancelada` como hoje; o campo fica como estava (histórico).
- **Status calculado:** `vence_hoje` e `atrasada` exigem `aguarda_retirada = false`. A expressão fica num lugar só, `financeiro.selectors.q_atrasada(hoje)` e `q_vence_hoje(hoje)`, e todo filtro, anotação e contagem usa as duas. Nenhum outro app escreve `vencimento__lt` em conta a receber: `locacoes.leituras`, `vistorias.services` e `plataforma.services` passam a chamar os selectors do `financeiro`.
- **Multa e juros (`FIN-03`):** `devido_ate(conta, dia)` continua a única conta. O começo do atraso passa a ser o mais tarde entre o vencimento, o dia em que a conta nasceu e `liberada_em`; com `aguarda_retirada = true`, multa e juros são 0, qualquer que seja o dia.
- **Índice:** o `(status, vencimento)` continua servindo; `aguarda_retirada` é seletivo no sentido contrário (quase tudo é `false`) e não ganha índice.

Por que dois campos e não um só "corre desde": a conta de venda, de devolução e a avulsa nunca esperam retirada, e um campo nulo com sentido de "ainda não corre" inverteria o padrão das contas que já existem. O booleano diz o estado, a data diz desde quando.

### 2. A reserva é sempre na confirmação

- `locacoes.services.confirmar` trava o veículo (`select_for_update`) e exige `disponivel`. Com outro status, 409 `LOC-03`, como hoje. O veículo vai para `reservado` na mesma transação, com a origem na locação e o motivo "Reserva da LOC-x", qualquer que seja a data de início. Sai o `if data_local(inicio) > hoje`.
- A Nova locação deixa de aceitar o veículo `reservado` (`impedimentos` da simulação): depois desta ADR, todo `reservado` é de uma locação `aguardando_retirada` ou de uma troca pendente (`LOC-09`), e nenhum dos dois pode ir para outro cliente.
- A restrição `uma_locacao_aberta_por_veiculo` continua sendo a última palavra.

### 3. `AUT-17` em `locacoes`, pelo estado e não pela data da execução

Duas tarefas de empresa (ADR 0012), em `apps/locacoes/tasks.py`, com o módulo `locacoes_vistoria` (`PLT-12`):

| Tarefa | Beat | Seleciona | Faz |
| --- | --- | --- | --- |
| `aut_17_cancelar_nao_retiradas` | 00:10 | `aguardando_retirada` com `ultimo_dia_retirada < hoje` | `locacoes.services.cancelar_nao_retirada`, uma transação por locação, com a locação travada e o status conferido de novo |
| `aut_17_avisar_nao_retiradas` | 08:00 | `aguardando_retirada` com `ultimo_dia_retirada == hoje` | aviso aos gerentes da filial, com chave de idempotência por locação |

- `ultimo_dia_retirada` = data local (`America/Sao_Paulo`, a da filial) do `inicio` + 3 dias corridos (`LOC-12`, padrão A do produto). É calculado, não guardado: o `inicio` só muda em `rascunho`. Uma função só, `locacoes.selectors.ultimo_dia_retirada(locacao)`, usada pelas tarefas, pela confirmação (409 `inicio_vencido`), pela simulação e pela representação.
- **Execução perdida:** como a seleção é "passou do último dia", e não "o último dia foi ontem", a próxima execução pega o que ficou para trás. A locação já `cancelada` não é selecionada de novo. O aviso de um dia perdido não é mandado depois: no dia seguinte, a locação já está na seleção do cancelamento e fora da do aviso (CA-410-19).
- **Corrida com a retirada:** a tarefa trava a locação e só cancela se ela ainda está `aguardando_retirada`. A retirada concluída entre 00:00 e 00:10 do dia seguinte ao prazo (assinatura remota, por exemplo) leva a locação a `ativa` antes da tarefa, e ela não cai. Aceito: é a mesma janela da `AUT-02`, e recusar a ativação pela hora pediria uma regra que o produto não escreveu.
- **Aviso na confirmação:** a locação confirmada no próprio último dia, depois das 08:00, recebe o aviso na confirmação (`transaction.on_commit`), pela mesma função e com a mesma chave.

### 4. Cancelamento automático reaproveita o cancelamento antes da retirada

`cancelar_nao_retirada(locacao)` chama o mesmo núcleo do cancelamento antes da retirada (`_aplicar_cancelamento`), com:

- motivo "Não retirada em 3 dias da data de início", auditoria `locacao.cancelar_nao_retirada`, ator Sistema (`usuario = None`), regra `LOC-12`;
- sem `APR-02`: pedidos abertos da locação (desconto `APR-01`, cancelamento `APR-02`) são fechados por `aprovacoes.cancelar_pendentes`, como já acontece;
- reembolso do que foi pago (`financeiro.devolver_ao_cliente`) sempre `a_fazer`: forma `estorno_cartao` se o 1º pagamento foi no cartão, senão `pix`. Nunca `dinheiro`, porque à meia-noite não há caixa aberto e o reembolso em dinheiro nasce `feito` pelo caixa. Quem paga o reembolso registra como fez, como em qualquer `a_fazer`.

### 5. Evento `locacoes.locacao_cancelada`

A vistoria de saída em rascunho é de `vistorias`, que está acima de `locacoes`. O cancelamento antes da retirada, pedido ou automático, publica `locacoes.locacao_cancelada` (`locacao_id`, `codigo`, `antes_da_retirada`, `automatico`, `motivo`) depois do commit. `vistorias` assina e descarta a saída em `rascunho` da locação (`vistoria.descartar`), deixando a concluída no histórico. Hoje o cancelamento pedido também não descarta a vistoria; o evento corrige os dois casos.

### 6. Canais do aviso

`notificacoes.services.avisar` ganha `por_email: bool = False`: o e-mail sai só para quem recebeu o aviso agora (a chave de idempotência já impede repetição), depois do commit, com o remetente da locadora (`financeiro.remetente()`), o título como assunto e corpo. O push não existe no código nem tem contrato (`PreferenciaNotificacao` está só no modelo de dados); a `AUT-17` sai com sino e e-mail, e o push entra quando o canal existir, sem mudar a tarefa.

## Consequências

- Uma migração em `financeiro` (dois campos) e a migração de dados do acerto (abaixo). Nenhuma em `locacoes` e `veiculos`.
- Toda consulta de atraso passa a depender de `q_atrasada`. Quem escrever `vencimento__lt=hoje` à mão em conta a receber reabre o Bug #1; o teste `test_loc_05_nada_vence_antes_da_retirada` cobre Receber, painel, régua, bloqueio, análise do cliente e a linha da lista de locações.
- **Acerto do ambiente que já existe** (CA-410-23): uma migração de dados em `financeiro` (ou o comando `acertar_reservas_t410`, idempotente) marca `aguarda_retirada = true` nas contas abertas de locação `aguardando_retirada`, e `locacoes` leva a `reservado` o veículo `disponivel` dessas locações, com o motivo "Reserva da LOC-x". A locação que já passou do prazo cai na próxima `AUT-17`.
- A régua (`AUT-03`), o evento `financeiro.parcela_atrasou` e o pedido de bloqueio por 15 dias (`CLI-05`) selecionam pelas mesmas `q_vence_hoje` e `q_atrasada`, então a conta que espera a retirada fica fora deles. Depois da retirada, seguem o calendário da conta, como sempre (CA-410-10). Como a retirada exige a 1ª parcela e a caução pagas e o prazo é de 3 dias, nenhuma conta liberada chega à régua já vencida.
- Se o dono escolher a opção B do período (o calendário anda para a retirada), o campo `liberada_em` continua útil, mas as contas teriam de ser refeitas na ativação: outra ADR.

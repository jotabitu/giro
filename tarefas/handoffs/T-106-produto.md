# T-106 · Pontos de regra da T-091 · produto → orquestrador, backend, qa

**O que foi feito:** as 2 divergências do backend na T-091 estão resolvidas na regra e nos critérios. As 5 decisões estão em "Pontos em aberto" de `docs/regras-de-negocio.md`, cada uma com as opções A e B, o padrão e o que muda no código. As linhas `[decisão]` e `[divergência]` do backlog ficaram como estavam.

**Divergências resolvidas:**
1. **CA-015-23** (`LOC-12`): na NMax mensal com 6 dias restantes, 20% dá 6360, abaixo da diária da NMax. A multa é **7990** (mínimo de 1 diária), e `cobrar_centavos` é 7990. A regra não mudou; o critério estava errado. O critério também cita a Patrícia (8 dias, 8480) como o caso em que o 20% passa da diária. O código e o teste da T-091 já dão 7990.
2. **Veículos:** a tabela de transições ganhou `reservado` → `disponivel`, "locação cancelada antes da retirada (`LOC-12`)", feita pelo sistema. "Desbloquear" e "Voltar para a frota" continuam fora, como o código faz. A nota de mudança está no fim da seção Veículos.

**Decisões para o dono do produto** (o padrão é a recomendação):

| # | Ponto | Padrão | O código da T-091 muda? |
| --- | --- | --- | --- |
| 1 | `LOC-11`: a filial fecha antes de a tolerância acabar | **A:** o prazo passa para a abertura seguinte mais a tolerância (sábado 11:30 → segunda até 09:00; às 08:30, sem atraso) | Não. Já faz A. Se aprovado, a `LOC-11` ganha uma frase. |
| 2 | `LOC-08`: renovação de uma locação com atraso | **A:** o período novo começa na hora da renovação, e o atraso até ali continua cobrado. Ex.: fim em 07 out 10:00 e renovação em 09 out 10:00 → 32900 + 10980, com fim em 16 out 10:00 e nenhum dia pago duas vezes | Sim. As parcelas novas começam no momento da renovação quando ela é feita depois do prazo, mesmo com a locação ainda `ativa`. |
| 3 | `LOC-12`: diária encerrada antes do fim | **A:** os dias usados contam em blocos de 24 h desde o início, e fração conta como dia. Ex.: Urbana, 5 diárias de 05 a 10 out 10:00, devolvida em 07 out 15:00 → devolve 2 diárias (8980); o código devolve 3 (13470) | Sim. A devolução usa a hora real, e a simulação mostra o valor para a devolução até a hora do início. |
| 4 | `LOC-13`: mensal em 4 semanais | **A:** o saldo é o mesmo do mês à vista; o crédito menos as parcelas canceladas pode ficar negativo e entra em `cobrar_centavos`. Ex.: NMax encerrada em 25 set com 2 semanais pagas → cobra 26500; o código cobra 21200 | Sim, pouco: tirar o `max(0, ...)` do crédito em `fim.py`. A Patrícia não muda (R$ 286,20). |
| 5 | `LOC-08`: desconto e extras na renovação | **A:** período e extras pelo preço de hoje; o percentual de desconto continua; o plano especial continua (preço fixo de hoje; o desconto conta os períodos desde o começo) | Sim, pouco: os extras usam o valor configurado hoje, e não o da confirmação. |

**Onde:** `docs/regras-de-negocio.md` (tabela de transições e nota em Veículos; 5 itens em Pontos em aberto), `docs/qa/criterios/T-015.md` (CA-015-23, com nota de mudança), `tarefas/em-andamento.md`.

**Regras cobertas:** `LOC-08`, `LOC-10`, `LOC-11`, `LOC-12`, `LOC-13`, `LOC-15`, a tabela de transições de Veículos.

**Check:** só documentação. As contas conferidas: 07 out 2026 é quarta, e 10 out é sábado. Urbana 4490 × 5 = 22450. NMax 159000 ÷ 30 × 20 = 106000, multa de 21200, 2 semanas = 74200, 159000 − 74200 − 79500 + 21200 = 26500. Street 2 × 5490 = 10980.

**O que ficou de fora:**
- O backlog fica para o orquestrador.
- O texto das regras para os pontos 1 a 5 só muda depois da decisão do dono do produto.
- O código não muda nesta tarefa. Se o dono aprovar os padrões, os pontos 2 a 5 viram uma tarefa do backend com critérios novos. Eu escrevo os critérios com os exemplos acima.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR, levar os 5 pontos ao dono do produto e acertar o backlog.
- **QA ou backend:** o teste do CA-015-23 já espera 7990. Só o comentário em `test_t091_locacao_fim.py:409` ("O CA-015-23 diz 6360") ficou velho e pode sair na próxima tarefa que mexer no arquivo.

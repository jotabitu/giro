# T-110 · Regras das 5 decisões da T-091 · produto → orquestrador, backend, qa

**O que foi feito:** o dono do produto aprovou a opção A nos 5 pontos da T-106. Os 5 saíram de "Pontos em aberto" e viraram regra nas `LOC-08`, `LOC-11`, `LOC-12` e `LOC-13`, com uma linha em "Decisões de 09 out 2026" e a nota de mudança no fim da seção Locação. Os critérios dos pontos 2 a 5 estão na T-015, com os números do seed.

**Regras novas no texto:**

| # | Regra | O que diz agora | Critério |
| --- | --- | --- | --- |
| 1 | `LOC-11` | Se a filial fecha antes de a tolerância acabar, o prazo passa para a abertura seguinte mais a tolerância (sábado 11:30 → segunda até 09:00). | CA-015-20 (frase nova: 08:30 sem atraso; 09:01 dá 5490) |
| 2 | `LOC-08` | Renovação depois do prazo começa o período novo na hora da renovação; o atraso até ali continua cobrado no acerto. Dentro do prazo, começa no fim antigo. | CA-015-26 |
| 3 | `LOC-12` | Diária encerrada antes do fim: dias usados em blocos de 24 h desde o início, fração conta como dia; as não usadas voltam ao cliente. | CA-015-28 |
| 4 | `LOC-13` | Mensal em 4 semanais: mesmo saldo do mês à vista; crédito menos parcelas canceladas pode ficar negativo e entra na conta a receber com a multa. | CA-015-29 |
| 5 | `LOC-08` | Na renovação: período e extras pelo preço de hoje; mesmo percentual de desconto, sem novo `APR-01`; plano especial mantido (fixo pelo valor de hoje; o de desconto conta os períodos desde o começo); plano desativado → tabela. | CA-015-27 |

**Números para o qa e o backend:**
- CA-015-26: Street semanal, fim 07 out 10:00. Renovada às 11:00 → sem atraso, período 07 a 14 out 10:00. Às 11:01 → 5490, período de 07 out 11:01 a 14 out 11:01. Em 09 out 10:00 → 10980, período de 09 a 16 out 10:00, parcela de 32900 vencendo em 09 out; total 43880.
- CA-015-27: extra de 1500 → 2000 desde 01 out dá parcelas novas de 34900; 5% → 31255; 8% do Rodrigo → 30268, sem `APR-01`; Entregador 27900 (desativado → 32900); Mensal fidelidade 3º e 4º meses de 98100.
- CA-015-28: Urbana, 5 diárias de 05 a 10 out 10:00. Em 07 out até 10:00 → devolve 13470; a partir de 10:01 → 8980. A simulação mostra 13470 com aviso.
- CA-015-29: NMax em 4 semanais. Encerrada em 25 set → cobra 26500; em 05 out → cobra 13250; em 07 out com as 4 pagas → devolve 28620.

**Onde:** `docs/regras-de-negocio.md` (`LOC-08`, `LOC-11`, `LOC-12`, `LOC-13`, nota de mudança em Locação, Decisões de 09 out 2026, Pontos em aberto), `docs/qa/criterios/T-015.md` (cabeçalho, CA-015-20, CA-015-23, CA-015-26 a CA-015-29), `tarefas/em-andamento.md`.

**Regras cobertas:** `LOC-08`, `LOC-10`, `LOC-11`, `LOC-12`, `LOC-13`, `LOC-15`, `LOC-02`, `LOC-03`, `DEV-02`.

**Check:** só documentação. Datas: 05 out 2026 é segunda, 07 out quarta, 09 out sexta, 10 out sábado. Contas: 4490 × 5 = 22450; 3 × 4490 = 13470; 2 × 4490 = 8980. 159000 ÷ 30 = 5300; 7 × 5300 = 37100; 20 dias → multa 21200, 74200 − 79500 = −5300, mais a multa → cobra 26500; 10 dias → multa 10600, 37100 − 39750 = −2650 → cobra 13250 (à vista: 159000 − 37100 + 10600 − 119250 = 13250). 32900 × 0,95 = 31255; 32900 × 0,92 = 30268. O ponto 1 confere com `backend/apps/locacoes/fim.py` (`prazo_da_devolucao` leva o fim para a abertura e soma a tolerância), então o código não muda.

**Leituras minhas, sem decisão nova (pode contestar):**
- CA-015-28: a tolerância de 1 h da `LOC-10` vale só para o atraso; nos dias usados da diária, 48 h 01 já é o 3º dia. É a letra da opção A ("fração conta como dia").
- CA-015-29: o encerramento cancela só as parcelas em aberto que vencem depois dele. Parcela já vencida e não paga no dia do encerramento não entrou em nenhum exemplo.

**O que ficou de fora:**
- O código: vem na T-111, com o backend (pontos 2 a 5).
- O backlog fica para o orquestrador (as linhas `[decisão]` da T-091 podem ser fechadas).
- O comentário velho em `test_t091_locacao_fim.py:409` (CA-015-23) continua lá; pode sair na T-111.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR e passar a T-111 ao backend com os CA-015-26 a CA-015-29.
- **Backend:** testes com o código da regra no nome (`test_loc_08_...`, `test_loc_12_...`, `test_loc_13_...`).
- **QA:** validar a T-111 pelos CA-015-20 e CA-015-26 a CA-015-29.

# T-103 · Fim previsto da LOC-2836 · produto → orquestrador, qa

**O que foi feito:**
- **Análise:** a divergência que a QA apontou na T-098 é real. Pela `LOC-05` a parcela de 07 out paga a semana de 07 a 14 out, e pela `LOC-01` duas semanas a partir de 30 set terminam em 14 out. As outras semanais do seed já seguem essa conta (LOC-2841: 23 set → 28 out, 5 semanas; LOC-2856: 07 → 21 out, 2 semanas). A própria tela `Locacao-Detalhe` diz "Período 2 semanas" e "30 set → hoje 18:00", e as duas coisas não fecham juntas.
- **Recomendação em "Pontos em aberto"** de `docs/regras-de-negocio.md`, item "Fim previsto da LOC-2836", com 3 opções e o que muda em cada uma:
  - **A) 1 semana até 07 out:** mantém o "devolve hoje"; total pago cai para R$ 629,00, o caixa de 07 out para R$ 782,90 em 4 entradas, e a carteira de outubro perde uma parcela paga (previsto R$ 51.673,10 em 127; recebido R$ 13.072,70 em 29).
  - **B) 2 semanas até 14 out 18:00 (padrão):** nenhum valor muda (R$ 958,00, caixa R$ 1.111,90, carteira, conciliação, acerto de R$ 183,00). Mudam só datas: o "devolve hoje" da LOC-2836 passa para 14 out.
  - **C) 2 semanas de 23 set a 07 out:** mantém R$ 958,00 e o "devolve hoje", mas tira o Pix de 07 out do caixa e faz a locação começar 8 dias antes da confirmação. Não recomendado.
- **Nenhuma opção que mantenha os três:** com início em 30 set e 2 parcelas semanais, o fim é 14 out. Manter o "devolve hoje" de 07 out obriga a mudar o total (A) ou o início (C).

**Onde:** `docs/regras-de-negocio.md` ("Pontos em aberto"), `tarefas/em-andamento.md`.

**Regras cobertas:** `LOC-01`, `LOC-05`, `LOC-06`.

**Check:** só documentação; nenhum código, critério, CSV ou teste mudou. Contas da carteira conferidas contra `docs/qa/carteira-outubro/README.md`.

**O que ficou de fora:** aplicar a decisão. Até o dono responder, o seed e os critérios ficam como estão (o teste da T-098 continua verde).

**Próximo passo para quem recebe:**
- **Orquestrador:** levar a pergunta ao dono do produto. Com a resposta, eu registro a decisão nas regras e nos critérios; a QA ajusta o seed.
- **QA, se for B:** em `backend/tests/aceitacao/carteira.py`, sai `FIM_DAS_CONFIRMADAS` e o ajuste de `fim_previsto`; o início da LOC-2836 passa a 30 set 18:00 (o `calcular` dá 14 out 18:00 com 2 períodos). Os testes de CA-015-16 (`devolve_hoje`), CA-015-19, CA-016-08, CA-016-09 e CA-016-12 passam a usar o relógio em 14 out para a LOC-2836. Em 07 out ela fica `ativa`, sem sinal, com ação "Abrir".
- **Código de produção:** não muda em nenhuma opção.

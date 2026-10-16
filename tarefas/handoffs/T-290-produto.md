# T-290 · Decisões abertas da T-275 e da T-286 · produto → orquestrador, arquiteto, backend, frontend, qa

**O que foi feito:** respondi as quatro `[decisão]` dos handoffs da T-275 e da T-286 e conferi os dois textos da T-185 (parte 1) que estavam fora do contrato. A branch `t-290-decisoes-ficha-movimentacoes` está empilhada sobre a `origin/t-286-contrato-movimentacoes` (249ab76).

**T-275, ficha do veículo:**
- **Uso médio da próxima manutenção:** fica o padrão. `dias_estimados` vem `null` no MVP, e a tela não mostra o trecho. A fórmula se decide com o app `manutencao`, na fase 2. Não muda regra.
- **Linha Pagamentos:**
  - Os textos e o alvo do "Cobrar" seguem o padrão do contrato: "2 contas atrasadas", e o Cobrar cobra a mais antiga, como na `CLI-07`. Cobrar todas fica no Receber.
  - **O valor muda:** passa a ser o valor do dia, com multa e juros (`FIN-03`), o mesmo do Receber e da mensagem do Cobrar; com mais de uma conta atrasada, a soma.
  - QXA-4B21 em 07 out: "Parcela 2 atrasada · R$ 306,09" (29.940 + 599 + 70), e não R$ 299,40.
  - Não muda regra.

**T-286, Movimentações:**
- **Como quem leva chega ao "Registrar chegada":** fica o padrão do contrato. Vendedor e vistoriador ganham o item Movimentações enquanto houver uma movimentação não concluída que levam, e a tela mostra só as deles (`MOV-02`, `USR-05`). Muda o menu, por isso está marcado para o dono conferir.
- **Junto, um acerto de texto:** a `MOV-02` dizia "qualquer perfil" para quem leva. Passou a dizer que o financeiro não leva, como o contrato e o CA-246-11 já diziam.
- **Coluna Concluídas:** só as concluídas hoje, no dia da filial de saída; as antigas ficam na lista, com o filtro. Não muda regra.
- **Leitura do arquiteto aceita:** o veículo `disponivel` com locação `aguardando_retirada` conta como reservado (`MOV-03`).

**T-185, textos:**
- **Cartão no anual:** fica "Cartão Visa final 4242 · cobrança automática todo ano".
- **409 `valor_mudou`:** troca para "O valor da diferença mudou. Confira o novo valor antes de confirmar.".
- **Desfazer no dia da virada:** fica como está ("A mudança para o plano Essencial já vale desde 22 nov.").

**Onde:**
- `docs/regras-de-negocio.md`:
  - Movimentações: o quadro, a `MOV-02`, a `MOV-03` e a nota de mudança;
  - `USR-05`, com a nota de mudança;
  - "Pontos em aberto": um item novo que junta as seis leituras das movimentações para o dono conferir.
- `docs/qa/criterios/T-246.md`: CA-246-17 a 19.
- `tarefas/backlog.md`: as quatro `[decisão]` respondidas, a leitura do arquiteto aceita, os textos da T-185 e a seção da T-290 retirada.
- `tarefas/feito.md`.

**Regras cobertas:** MOV-02, MOV-03, USR-05, FIN-03, CLI-07, PLT-13, PLT-04.

**O que ficou de fora:** a resposta do dono para as seis leituras das movimentações ("Pontos em aberto"). A fórmula do uso médio fica para a fase 2.

**Próximo passo para quem recebe:**
- **Arquiteto:**
  - em `veiculos.md` ("Blocos da ficha"), `valor_centavos` do pagamento passa ao valor do dia, e o exemplo vai a 30609;
  - em `assinatura.md`, a linha do cartão no anual e os dois textos do 409 e do desfazer;
  - em `movimentacoes.md`, nada muda: o padrão foi confirmado.
- **Backend:**
  - `test_vei_ficha_pagamento_da_locacao` com 30609;
  - o texto do 409 `valor_mudou` na T-185.
- **Frontend:** mostra o `rotulo` e o valor que a API mandar, sem calcular.
- **QA:** CA-246-17 a 19.
- **Orquestrador:** levar ao dono o item "Leituras do produto nas movimentações", com as seis leituras: as cinco da T-283 e o item de menu de quem leva.

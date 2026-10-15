# T-231 · `cancelamento.md` pela T-229 · arquiteto → orquestrador, backend (T-195, T-185, T-186), frontend (T-198), qa

**O que foi feito:** o contrato de cancelar e pausar acompanha as decisões do dono de 15 out 2026 (T-229, opção A nos 5 casos da T-194). As marcas `[decisão]` saíram. Branch `t-231-cancelamento-decisoes`, **empilhada sobre a `t-229-regras-cancelar-pausar`** (PR #230), porque cita as regras e os CA-ASS-54 a 58 que só existem nela. Mesclar o #230 antes; depois disso, o PR da T-231 mostra só o commit dela. Só documentos.

- `docs/api/cancelamento.md`:
  - **Cancelar em teste com a 1ª paga** (CA-ASS-54): `acesso_ate` = `periodo_fim` da 1ª fatura, sem estorno; `em_teste` até o fim do teste e `ativa` depois, pela transição de `assinatura.md`; a fatura seguinte não é gerada; o desfazer vale até `acesso_ate`. `datas_do_cancelamento` ganha o caso (d), e `o_que_acontece` ganha a linha da `em_teste` com a 1ª paga. Teste `test_plt_06_cancelar_no_teste_com_a_1a_paga`.
  - **Desistir da pausa** (CA-ASS-55): ação nova `acoes.desistir_pausa` (`ativa` com pausa agendada, até a véspera de `pausa_inicio`); `voltar_pausa` fica só para a `pausada`. As duas chamam `DELETE pausa/`. Serviço `desistir_da_pausa`: a fatura que a pausa cancelou nasce de novo como no desfazer (FAT-0003 de 22 nov, desistindo em 20 nov).
  - **Cancelamento marcado** (CA-ASS-56): os 409 de mudar de plano e pausar deixam de ser provisórios; `plano_proximo` fica e vale na fatura seguinte se o cancelamento for desfeito.
  - **Diferença em aberto na pausa** (CA-ASS-57): a régua segue para ela na `pausada`; a volta com a fatura atrasada põe a empresa em `inadimplente`, e o D+15 conta do vencimento dela (08 dez no exemplo).
  - **O que fica no `public`** (CA-ASS-58, `test_aud_08_o_que_fica_no_public`): confirmado; nenhuma tarefa apaga faturas até o prazo de guarda ser decidido; a T-230 pode mudar a limpeza da linha do MEI.
  - Nota "O que mudou na T-231" no topo; versão e critérios no cabeçalho; tabela de erros e "O que muda para as tarefas abertas".
- `docs/api/assinatura.md`: `desistir_pausa` no caso do seed e bloco "Da T-231".
- `docs/decisoes/0025-apagamento-da-empresa-cancelada.md`: o item 4 diz que o dono confirmou o padrão.
- `tarefas/backlog.md` (estado da T-231 na seção da T-229) e `tarefas/feito.md` (PR a abrir).

**Regras cobertas:** PLT-06, PLT-04, AUD-08, PLT-02.

**Para quem recebe:**
- **T-195 (backend):** `desistir_da_pausa`, o caso (d) em `datas_do_cancelamento`, a volta em `inadimplente` com a diferença atrasada, a limpeza do `public`; testes acima e CA-ASS-54 a 58.
- **T-185 e T-186 (backend):** `acoes.desistir_pausa`; a régua da diferença roda na `pausada`, e as transições de `assinatura.md` pulam a `pausada`.
- **T-198 (frontend):** "Desistir da pausa" por `acoes.desistir_pausa` e "Voltar da pausa" por `acoes.voltar_pausa`, na mesma rota. CA-ASS-54 a 56.
- **Qa (T-204, T-215):** CA-ASS-54 a 58 com o relógio de referência.

**Próximo passo:** o orquestrador abre o PR depois do #230.

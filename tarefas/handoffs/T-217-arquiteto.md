# T-217 · Contrato da reativação · arquiteto → orquestrador, backend (T-184, T-186, reativação), qa

**O que foi feito:** contrato da reativação da `cancelada` pela equipe ajustado à regra da T-216 (`PLT-06`). Branch `t-217-contrato-reativacao`, **empilhada sobre a `t-213-contrato-endereco-downgrade`**, porque as duas mexem no mesmo parágrafo da reativação. Mesclar a T-213 antes; depois disso, o PR da T-217 mostra só o commit dela. Só documentos.

- `docs/api/assinatura.md`, "Mudança de ciclo e reativação pela equipe": `reativar_empresa` volta a `ativa` na hora, e a fatura nova depende do último período pago:
  - **período pago ainda correndo** (fatura `mensalidade` `paga` com `periodo_fim >= hoje`): vence em `periodo_fim + 1`, cobre o período seguinte e `dia_vencimento` não muda (CA-ASS-49: reativada em 15 nov, R$ 899,00 vencendo em 22 nov, "Plano Completo · 22 nov a 21 dez"). A fatura de diferença do upgrade não conta como período pago;
  - **período já acabou**: vence no dia da volta e `dia_vencimento` passa a esse dia (CA-ASS-46: 01 dez);
  - fatura `mensalidade` não cancelada do mesmo período já existente é reaproveitada (não nasce outra); emissão pela `PLT-02` (na hora com vencimento até 5 dias à frente, senão pela `gerar_faturas` 5 dias antes, como a 1ª fatura);
  - função pura `plataforma.calendario.vencimento_da_reativacao(hoje, ultimo_periodo_pago_fim, dia_vencimento)`; teste `test_plt_06_reativar_no_periodo_pago`.
  - "Dia de vencimento" diz que ele só muda na reativação depois do fim do período pago; bloco "Da T-217" em "O que muda para as tarefas abertas".
- `docs/api/plataforma.md`: ação `reativar` com o vencimento novo.
- `docs/decisoes/modelo-de-dados.md`: `Empresa.dia_vencimento` com o caso da reativação no período pago.

**Regras cobertas:** PLT-06, PLT-01.

**Para quem recebe:**
- **T-184 (backend, faturas):** a fatura nova usa `proximo_periodo` a partir de `periodo_fim + 1`, sem mexer em `dia_vencimento`.
- **T-186 (backend, estados e régua):** a fatura da reativação com vencimento mais longe que 5 dias é emitida pela `gerar_faturas`; a régua volta a valer para ela.
- **Quem fizer `reativar_empresa`** (ainda sem número; Django Admin no MVP): os dois casos, `vencimento_da_reativacao`, testes `test_plt_06_reativar_no_periodo_pago` (CA-ASS-49) e `test_plt_06_reativar_so_com_atrasada_paga` (CA-ASS-46).
- **Qa (T-215):** CA-ASS-49 com o relógio de referência.

**Próximo passo:** o orquestrador abre o PR depois da T-213.

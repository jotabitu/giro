# T-351 · Janela efetiva de 5 minutos nos contratos · arquiteto → orquestrador

**O que foi feito:** os contratos agora dizem o que o `contas.md` ("Reconfirmar as 2 etapas") já dizia. Na prática, as 2 etapas recentes valem até o fim do primeiro access do login ou da reconfirmação, ou seja, 5 minutos, porque o `auth_time` não passa para o access novo na renovação do refresh. `DOIS_FATORES_RECENTE` (15 min) fica só como teto. A decisão foi do dono, na T-349. Os mesmos trechos dizem que a tela trata o 403 `2fa_recente` pela reconfirmação (ADR 0032), pelo diálogo `useReconfirmar2fa` da T-348.
- `docs/api/cancelamento.md`: o item "2 etapas recentes para cancelar" e a linha do 403 na tabela de erros.
- `docs/api/auditoria.md`: o `zip` sem 2 etapas, o backup completo da fase 2 em `POST /api/exportacoes/` e, também, o download em `GET /api/exportacoes/{id}/baixar/`. O contrato já exigia 2 etapas recentes no download do `zip`; por isso ele também usa o mesmo diálogo.

**Regras cobertas:** `PLT-06`, `S-15`, `USR-02` (nenhuma muda; `regras-de-negocio.md` não foi tocado).
**O que ficou de fora:** código, ADR 0032 e `contas.md`, que já estava certo.
**Próximo passo para quem recebe:** o orquestrador abre o PR. Branch `t-351-janela-5-min-contratos`.

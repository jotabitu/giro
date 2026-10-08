# T-043 · Contratos da API de financeiro e auditoria · arquiteto → backend, frontend, qa, devops, orquestrador

**O que foi feito:**
- `docs/api/financeiro.md`: valor do dia com multa e juros (`FIN-03`, juros pro rata de 30 dias arredondados uma vez); contas a receber com status calculado, faixas, indicadores e lote de cobrança; baixa no caixa sem pagamento parcial; geração de Pix e boleto (`CobrancaExterna`, valor esperado do dia); cancelar, renegociar e estornar; cobrança recorrente (`AUT-04`); devoluções ao cliente (`Reembolso`); caixa do dia com abertura única, sangria, estorno de movimento, fechamento com diferença (`APR-04`) e automático (`AUT-08`); despesas com limite de R$ 500 e pagamento no caixa; interface `ProvedorPagamentos` para a T-029; webhooks com S-14 (token por `compare_digest`, `WebhookRecebido` idempotente, 200 na hora, task que consulta o parceiro e compara o valor, pendência quando difere).
- `docs/api/auditoria.md`: consulta da empresa (só administrador) e da plataforma (só dono), filtros combináveis, textos prontos por ação, detalhe com antes e depois classificados (ADR 0014), exportação com link de 7 dias que redireciona para URL de 15 minutos e grava download (S-15), 2 etapas recentes para o backup completo, backup automático (`AUT-11`).
- `docs/api/aprovacoes.md` (mínimo da fase 1): lista, aprovar, recusar com motivo, cancelar; `APR-09` checado na decisão.
- ADR 0016 (S-10): papéis `giro_migracao`, `giro_app` (só `SELECT, INSERT` na auditoria) e `giro_expurgo` com função `SECURITY DEFINER`; triggers de linha e de `TRUNCATE`.
- Modelo de dados: `CobrancaExterna`, `AutorizacaoRecorrente`, `Reembolso`, `PendenciaPagamento`, `WebhookRecebido`; `ContaReceber` sem `cobranca_externa_id` e com `estornada_em`; `Despesa` com `data`, `forma` e movimento de caixa.
- Também nesta branch: as decisões do dono sobre a T-038 (combustível calculado com `capacidade_tanque_litros` e `preco_litro_centavos`, um acerto só por locação na troca, renovação, comissão de locação, juros).

**Casos do seed nos contratos:** caixa de 07 out com entradas 118260 e gaveta **28100** (R$ 281,00); em aberto 164640 em 2 clientes; Carlos 30609 e Rafael 138517 com multa e juros; despesas de outubro 706670, aguardando 120000; LOC-2836 com combustível 3200 (16 L × 1/4 × 550 + 1000).

**Onde:** `docs/api/financeiro.md`, `docs/api/auditoria.md`, `docs/api/aprovacoes.md`, `docs/decisoes/0016-papeis-de-banco-e-expurgo-da-auditoria.md`, `docs/decisoes/modelo-de-dados.md`, `docs/decisoes/README.md`, `tarefas/backlog.md`.

**Regras cobertas:** FIN-01 a FIN-08, APR-01 a APR-10 (decisão), AUD-01 a AUD-03, AUD-07, AUD-09, AUT-03 a AUT-05, AUT-08, AUT-11, PLT-07, PLT-08, PLT-09; segurança S-05, S-10, S-14, S-15.

**O que ficou de fora:** comissões, conciliação, DRE, saldo e fluxo previsto (fase 2); tela `Gerente` e lembrete `APR-08` (fase 2); `FaturaAssinatura` e o webhook da conta principal seguem o mesmo fluxo, mas a cobrança da assinatura é fase 2.

**Pontos para quem recebe:**
- Backend (T-017, T-018, T-029): a idempotência sai de `ContaReceber` e vai para `WebhookRecebido` e `CobrancaExterna`. O backup completo exige a claim `auth_time` (momento da última confirmação do código) nos tokens com `otp`.
- QA e produto: os critérios CA-017-18 e CA-012-16 citam o código `filial_com_caixa_aberto`; o contrato de filiais devolve `FIL-06` com `detalhes.operacao.caixas` (T-037).
- DevOps: ADR 0016 pede os três papéis de banco e `DATABASE_URL_MIGRACAO` antes da homologação.
- Dúvida para o produto: reembolso por Pix manual no MVP (backlog).

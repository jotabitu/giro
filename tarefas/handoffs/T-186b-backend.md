# T-186 (parte 2) · Geração, emissão e cartão guardado · backend → orquestrador, qa (T-204, T-215), frontend (T-187), segurança, arquiteto, backend (T-195, T-196)

Corte aprovado pelo orquestrador em 16 out 2026: a T-186 sai em 3 PRs. Esta é a parte 2 (branch `t-186b-faturas-cobranca`, sobre a main depois do PR #298).

**O que foi feito:**

- **Tarefa `plataforma_gerar_faturas`** (Beat, 06:00, `services.gerar_faturas`), idempotente no mesmo dia, cada empresa ou fatura na sua transação; o parceiro fora do ar numa delas fica no log e entra na rodada seguinte:
  1. **Geração 5 dias antes** (`gerar_fatura_do_periodo`, `PLT-02`): a mensalidade do período seguinte para `em_teste`, `ativa`, `inadimplente` e `suspensa` (nunca `pausada` nem `cancelada`, nem período que começa depois do `acesso_ate`), pelo que vale na virada (`_o_que_vale_na_virada`). Moto Rápida: FAT-0002 de 22 nov a 21 dez nasce em 17 nov.
  2. **Conferência do downgrade agendado** (`PLT-04`), com `Empresa` e `UsoEmpresa` travados e a conta da 422 (`excede_no_plano`). Não cabe (CA-ASS-40): `plano_proximo` cai, a fatura sai pelo plano atual (R$ 899,00), auditoria `empresa.mudar_plano_recusado` nos dois lugares (ator `sistema`, `detalhes` da 422) e e-mail com o motivo ("11 de 10 usuários") para o `email_cobranca` e os administradores. Cabe (CA-ASS-41): a fatura sai pelo plano menor, e a virada de 22 nov (parte 1) muda o plano.
  3. **Emissão no parceiro** (`emitir_cobranca_da_fatura`) das faturas `aberta` sem cobrança que vencem em até 5 dias (as novas, a 1ª e a diferença do upgrade): boleto com Pix e o e-mail nesse dia (CA-ASS-10); Pix automático pela autorização ativa (`cobrar_com_autorizacao`, `cobranca_tipo = pix_auto`); cartão ainda não digitado → página do parceiro (CA-ASS-11). Sem forma ou com a autorização pendente, nada sai.
  4. **Cartão guardado no vencimento** (`cobrar_cartao_da_fatura`, ADR 0023): o token só é decifrado em `integracoes.pagamentos.cobrar_cartao_guardado`. Recusado: `cartao_recusado_em`, `tentativas_cartao + 1`, auditoria `fatura_assinatura.cartao_recusado`; a 2ª tentativa é no dia seguinte, e com 2 (`TENTATIVAS_DO_CARTAO`) não há terceira (CA-ASS-12). A baixa segue pelo webhook.
- **Diferença do upgrade no cartão guardado, na hora:** `mudar_plano` agenda `plataforma_cobrar_cartao` depois do commit (com nova tentativa se o parceiro estiver fora). Nas outras formas, a diferença sai na emissão das 06:00 seguintes.
- **Aviso do Pix automático autorizado:** `validar_webhook` (Asaas e falso) lê o aviso da autorização (objeto `pixAutomaticAuthorization`, sem `payment`) em `EventoWebhook.autorizacao_id`; a baixa da conta principal consulta a autorização no parceiro (`consultar_autorizacao`, novo na interface, S-14) e, ativa, leva a forma a `ativa` (`assinatura.forma_ativa`, "Pix automático autorizado"). Recusada, expirada ou cancelada não muda a forma: fica no resultado do aviso.
- `selectors.cobranca_da_fatura` mostra `pix_auto` como `pix` e `cartao` (cartão guardado) como `cartao`.

**Onde:** `backend/apps/plataforma/{services,tasks,selectors}.py`, `README.md` do app, `backend/config/settings/base.py` (Beat), `backend/integracoes/pagamentos/{__init__,base,asaas,falso}.py`. Testes: `backend/tests/aceitacao/test_t186b_faturas_cobranca.py` (15) e `backend/tests/integracoes/test_t184_asaas_conta_principal.py` (+3, com 2 gravações novas em `gravacoes/asaas.json`).
**Contrato:** nenhuma rota nova; OpenAPI sem mudança.
**Regras cobertas:** PLT-02 (`test_plt_02_ca_ass_10_boleto_cinco_dias_antes`, `test_plt_02_cartao_uma_tentativa_a_mais`, `test_plt_02_gera_a_fatura_do_periodo_seguinte_cinco_dias_antes` e outros), PLT-04 (`test_plt_04_downgrade_agendado_deixa_de_caber`, `test_plt_04_downgrade_cabia_na_geracao`, `test_plt_04_diferenca_do_upgrade_no_cartao_guardado_na_hora`), PLT-13 (`test_plt_13_pix_automatico_autorizado_e_cobrado_pela_autorizacao`, `test_plt_13_aviso_de_autorizacao_confere_no_parceiro`). Isolamento: `test_plt_02_geracao_isolada_por_empresa`.
**Testes rodados:** ruff, ruff format e mypy no backend inteiro; `test_t186b_faturas_cobranca` (15), `tests/integracoes` (com o contrato do Asaas, +3), `test_t029_asaas`, `test_t184_faturas`, `test_t185_assinatura`, `test_t185b_forma_faturas`, `test_t186_estados`, `test_t189_seguranca_cartao`, `apps/plataforma/tests` e `comum/tests`: 323 passaram, 6 skipped (sandbox), 3 xfailed (NFS-e, T-197). OpenAPI gerado sem diferença. Suíte toda não rodada (pouca memória).

**Pontos em aberto:**

- **Sandbox do Asaas:** o nome do evento e do objeto do aviso da autorização (`PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED`, `pixAutomaticAuthorization`) seguem a documentação e não foram conferidos; a antecedência de 5 dias corridos para a cobrança pela autorização (o parceiro pede de 2 a 10 dias úteis) também.
- **Pix automático sem autorização no vencimento:** a regra não diz o que sai se a empresa escolheu Pix automático e não autorizou. Hoje nada é emitido, e ela paga pelo "Pagar" (Pix avulso). Vale uma leitura do produto.
- **Arquiteto:** o contrato (`assinatura.md`, "Faturas, cobrança e régua") pode citar o aviso da autorização e `consultar_autorizacao` na interface (`financeiro.md`, "Interface de pagamentos").
- **T-196:** a conferência na geração usa `excede_no_plano`, que já chama `pendencias_dos_modulos`; a atividade aceita no plano (ADR 0024, item 10) entra com ela, no mesmo lugar.
- **T-195:** pausa agendada (`pausa_inicio`) ainda não existe no model; quando existir, `gerar_fatura_do_periodo` pula o período a partir dela, ao lado do `acesso_ate`.
- **Parte 3 (`t-186c`):** as mensagens da régua `aut_13_regua_assinatura` (D-3 com o link da página do cartão, D0, D+3, D+7 e a tarefa de ligação).

**Próximo passo para quem recebe:**

- **QA (T-204, T-215):** CA-ASS-10, 11, 12, 26 (Pix automático), 40 e 41 com o relógio de referência.
- **Frontend (T-187):** nada muda na API; `cobranca.forma` continua `cartao`, `pix` ou `boleto`, e a situação da forma passa a sair de `aguardando_autorizacao` sozinha.
- **Segurança:** conferir que o token do cartão só é decifrado em `integracoes/pagamentos` e que a auditoria da cobrança no cartão não leva token.

# T-184 · Faturas da assinatura e conta principal no parceiro · backend → orquestrador, backend (T-185, T-186, T-195, T-197), arquiteto, segurança (T-189), qa (T-204, T-215)

**O que foi feito:** o que precisa existir no `public` para a assinatura ter faturas e cobrança reais (`docs/api/assinatura.md`, "Faturas, cobrança e régua", "De onde vem o endereço" e "Tomador da fatura"; ADR 0023). Branch `t-184-faturas-assinatura`, a partir da `origin/main`. Inclui o pedido da T-236 (PR #237): campos do tomador, `email_cobranca` da fatura e `gravar_tomador` na baixa.

- **Modelos** (migração `plataforma.0009`, que também preenche as empresas que já existem):
  - `Empresa`: `email_cobranca` (nasce = e-mail do administrador), `endereco_*`, `ciclo_proximo`, `dia_vencimento` (dia de `teste_fim + 1`).
  - `FaturaAssinatura`: máquina `aberta` → `paga`, `atrasada`, `cancelada` (regra `PLT-14`); código `FAT-0001` por empresa; uma mensalidade viva por competência; campos da cobrança, do cartão, da nota, do tomador (`tomador_*`, `tomador_gravado_em`), do cancelamento e `email_cobranca`.
  - `FormaPagamentoAssinatura` (1:1, nasce vazia): forma, status, pagador e autorização no parceiro, token do cartão cifrado com a chave dos segredos, bandeira e final.
- **1ª fatura** em `criar_empresa` (vale também para o seed e o Django Admin): Moto Rápida, FAT-0001, R$ 449,00, vence 22 out, "Plano Profissional · 22 out a 21 nov".
- **Calendário** (`plataforma/calendario.py`, puro): `proximo_periodo`, `vencimento_seguinte` (31 jan, 28 fev, 31 mar), `descricao_da_fatura` (mensal, anual e diferença).
- **Endereço da nota** (`PLT-15`, T-213): `copiar_endereco_da_matriz`, chamado por `filiais.criar_filial` quando a filial nasce matriz; copia uma vez e depois não segue a filial. Seed com o endereço da Filial Centro. `pedir_notas_pendentes` só é agendada com `GIRO_NFSE_ASSINATURA_ATIVA`.
- **Interface de pagamentos** (falso e Asaas):
  - `criar_ou_atualizar_pagador` (empresa com razão social, CNPJ, endereço e e-mail de cobrança, notificações do parceiro desligadas);
  - `cobrar_cartao_salvo` (recusa → `CartaoRecusado`);
  - `cartao_link` com `url_pagina` (a `invoiceUrl`);
  - `SituacaoCobranca.cartao` (token, bandeira, final);
  - `conta_principal()` (chave do ambiente);
  - no falso: `pagadores`, `recusar_cartao`, cartão `visa 4242`.
- **Webhook da conta principal:** a view procura a `ContaPagamento` pelo token. Sem ela, confere o hash de `GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH` (setting nova; vazio = nunca confere). O aviso é gravado no `public` (`evento_id` único) e a tarefa `plataforma_processar_webhook_fatura` faz a baixa. A tarefa:
  - consulta o parceiro, não confia no corpo, e tenta de novo com o parceiro fora;
  - paga com o valor certo: `paga`, `pago_em`, `forma`, auditoria `fatura_assinatura.pagar` (sistema, `PLT-14`), e o tomador gravado (`gravar_tomador`, enquanto a NFS-e está desligada);
  - pago na página do parceiro com a forma `cartao`: o cartão fica guardado e a forma vai a `ativa`; com outra forma, nenhum token é guardado;
  - valor diferente, estorno, fatura não aberta e situação desconhecida não baixam: ficam no `resultado` do aviso e no log.
- **Painel da plataforma:** `faturas_recentes` com dados reais ("1ª cobrança após o teste"); "Fatura N dias atrasada" pela atrasada mais antiga.
- **Django Admin:** faturas de todas as empresas, só leitura, com o tomador e o filtro "nota pendente".
- Corrigido no caminho: o `preco_contratado_centavos` da empresa anual nascia com o preço mensal. Agora nasce com o anual (`preco_no_ciclo`, `PLT-05`).

**Testes:** `make backend-check` equivalente no container avulso: ruff, mypy e a suíte inteira passam (954 passaram, 6 pulados, 6 `xfail`). Os da tarefa:
- `tests/aceitacao/test_t184_faturas.py`:
  - `test_plt_01_primeira_fatura_dia_seguinte_ao_teste` e o anual;
  - código por empresa, uma mensalidade por período, faturas recentes só da empresa;
  - `test_plt_15_endereco_nasce_da_matriz` e `test_plt_15_endereco_da_nota_e_da_filial_separados`;
  - pagador;
  - `test_plt_14_webhook_da_fatura_baixa_uma_vez` (idempotente), valor diferente, token errado, sem hash;
  - cartão guardado e cartão sem a forma;
  - `test_plt_14_fatura_guarda_tomador` (CA-ASS-59 pela baixa; a parte da nota em `xfail` até a T-197).
- `apps/plataforma/tests/test_calendario.py` (CA-ASS-08, CA-ASS-09, descrições).
- `tests/integracoes/test_t184_asaas_conta_principal.py`, com as gravações novas em `gravacoes/asaas.json`.
- `test_t127_seed.py` com a FAT-0001 e os dados fiscais do seed.
- `test_t010_plataforma.py`: `faturas_recentes` deixa de ser vazio.

OpenAPI regenerado (`FaturaRecente` tipado no detalhe da empresa).

**Para quem recebe:**
- **T-185 (rotas):**
  - a forma de pagamento é `forma_pagamento_da_empresa(empresa)`; ela é gravada pela rota (aqui só o model);
  - use `atualizar_pagador` antes de cobrar e no `PATCH dados-fiscais/`;
  - `fatura.descricao` já monta o texto;
  - `forma` vazia vem como `""` no banco (convenção do ruff DJ001): a API devolve `null`;
  - o mesmo para `complemento`: `Empresa.endereco` já devolve `None`.
- **T-186 (régua e estados):**
  - `criar_fatura` é a única porta;
  - a emissão no parceiro grava `cobranca_externa_id` e `cobranca_emitida_em`, e o cartão guardado é cobrado com `cobrar_cartao_salvo` e `CartaoRecusado`;
  - a mudança de estado da empresa na baixa (ativa na hora) entra em `processar_webhook_fatura`, depois da transição da fatura.
- **T-195 (apagamento):**
  - a baixa já não depende do schema da empresa;
  - falta `omitir_no_public` em `comum.auditoria`. Por ora, `endereco_*` da `Empresa` está em `omitir`, então o evento da cópia do endereço sai sem o valor também no `public` e só é gravado lá; o evento com o valor no schema da empresa vem com o `omitir_no_public`;
  - `email_cobranca` da fatura existe e não é usado ainda.
- **T-197 (NFS-e):** `plataforma_pedir_notas_pendentes` hoje só conta; `emitir_nota_fatura` deve chamar `gravar_tomador` antes do pedido. O `xfail` espera `plataforma_emitir_nota_fatura` em `tasks.py`.
- **Arquiteto:** dois acréscimos ao modelo, que valem registrar em `modelo-de-dados.md`:
  - `FaturaAssinatura.ciclo`, porque a descrição do anual depende dele e o plano ou o ciclo da empresa podem mudar depois;
  - `FaturaAssinatura.numero`, porque o código é por empresa. A sequência fica no public com a chave `FAT-<empresa_id>`.
  Os textos e os enums do contrato marcados "nulos" ficaram vazios (`""`) no banco, pela regra DJ001 do ruff; os nulos de verdade continuam nulos (datas, JSON e o `cobranca_externa_id` único).
- **Segurança (T-189):**
  - o token do cartão é `CampoCifrado` (segredos), omitido na auditoria e fora do `repr`;
  - o webhook da conta principal só aceita com o hash configurado;
  - o tomador e o e-mail da fatura estão em `omitir`.
- **Qa (T-204, T-215):** CA-ASS-01 (1ª fatura), CA-ASS-47, 48 e 59 com os nomes de teste acima.

**Pendente (sem chave do sandbox aqui):** conferir no sandbox do Asaas:
- se o pagamento na página devolve `creditCard.creditCardToken` na consulta da cobrança (ADR 0023, item 4). As gravações seguem a documentação; se não devolver, o cartão passa à assinatura recorrente do parceiro e a ADR ganha nota;
- se a atualização do cliente aceita e-mail e telefones vazios com `notificationDisabled` (`anonimizar_pagador`, T-236).

**Próximo passo:** o orquestrador abre o PR. Fico parado, como pedido.

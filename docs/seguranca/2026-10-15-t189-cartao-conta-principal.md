# T-189 · Cartão e conta principal da assinatura

**Data:** 15 out 2026 · **Agente:** segurança · **Regras:** PLT-07, PLT-13, PLT-14, AUD-01, AUD-03 · **ADR:** 0007, 0014, 0023
**Base:** `main` em `f740426` (T-184, PR #238). Código: `backend/apps/plataforma/services.py` (faturas, pagador, webhook da conta principal, `_guardar_cartao`), `apps/plataforma/models.py` (`FormaPagamentoAssinatura`), `apps/financeiro/api/views.py` (`WebhookAsaasView`), `integracoes/pagamentos/` (`asaas.py`, `base.py`, `falso.py`), `comum/permissoes.py` e `comum/autenticacao.py` (somente leitura e suporte). Contrato: `docs/api/assinatura.md`.
**Método:** leitura do código e do contrato, e testes em `backend/tests/aceitacao/test_t189_seguranca_cartao.py`. As rotas da assinatura (T-185) ainda não existem: a exceção da `suspensa` e a escrita barrada ao suporte foram revisadas no contrato e nas travas comuns que a T-185 vai usar, e viraram requisitos com teste (seção "Para a T-185").

## Resumo

A ADR 0023 está de pé no que já existe: nenhuma rota nem tela recebe número, validade ou código do cartão; o token é `CampoCifrado` com a chave dos segredos, omitido na auditoria e fora do `repr`; o webhook da conta principal só aceita com o hash configurado (vazio nunca confere), consulta o parceiro antes de baixar, confere o valor e é idempotente pelo `evento_id`; o token só é guardado quando a forma escolhida é o cartão.

Dois achados médios, nenhum alto:

| Código | Achado | Severidade | Teste |
| --- | --- | --- | --- |
| M-01 | O corpo bruto do aviso guarda o token do cartão em claro | média | `test_adr_0023_aviso_guardado_sem_o_token_do_cartao` (`xfail` estrito) |
| M-02 | Subconta sem chave cai na chave da conta principal | média | `test_adr_0007_subconta_sem_chave_nunca_usa_a_chave_principal` (`xfail` estrito) |
| B-01 | Sentry pode receber o token do webhook e o corpo do aviso | baixa | a conferir com o devops |
| B-02 | Recusa do parceiro na consulta deixa o aviso parado, sem resultado | baixa | — |

Guardas novas, passando: `test_adr_0023_nenhuma_rota_recebe_dado_do_cartao` (nenhum arquivo `apps/*/api/*.py` cita número, validade, código ou `cartao_token`) e `test_adr_0023_cartao_guardado_sem_token_no_repr`.

## Achados

### M-01 · O corpo bruto do aviso guarda o token do cartão · média

**Onde:** `plataforma.services.registrar_webhook_principal` grava `corpo["bruto"]` com o aviso inteiro em `WebhookRecebido` no `public`; `financeiro.services.registrar_webhook` faz o mesmo no schema da empresa.
**Problema:** o aviso de pagamento do Asaas traz o objeto da cobrança, e a cobrança paga no cartão traz `creditCard.creditCardToken` (é o mesmo formato da consulta, `gravacoes/asaas.json`). O token fica em claro no banco, sem prazo, ao lado da cópia cifrada da `FormaPagamentoAssinatura`. Isso fere o item 2 da ADR 0023 (token só cifrado, nunca no log nem fora de `integracoes/pagamentos/`). Com a chave da API da conta principal, o token cobra o cartão da locadora. O `bruto` não é lido por nenhum código: a baixa usa o evento extraído e consulta o parceiro.
**Reprodução:** o teste manda o aviso da FAT-0001 com `payment.creditCard.creditCardToken` e confere `WebhookRecebido.corpo`: o token está lá.
**Sugestão:** gravar o aviso sem `payment.creditCard` (ou sem o `bruto`), num ponto só, usado pelas duas funções; uma migração de dados limpa o `creditCard` dos avisos já gravados no `public` e nos schemas. Vale também para o cartão do cliente da locadora no futuro (subconta, mesma interface).

### M-02 · Subconta sem chave cai na chave da conta principal · média

**Onde:** `integracoes/pagamentos/asaas.py`, `Asaas._chave`: `chave = conta.decifrar_chave() or self._chave_principal`.
**Problema:** a conta principal é a `ContaPagamentoRef` sem chave (`conta_principal()`), e a escolha é "chave vazia, usa a do Giro". Uma subconta cuja chave volta vazia (conta criada sem a chave gravada, cifra perdida, bug futuro em `referencia`) passa a falar com o parceiro como a conta do Giro, sem erro: a cobrança do cliente da locadora nasce na conta principal e o dinheiro cai no Giro; a consulta e o cancelamento mexem na conta errada. Até a T-184 isso era teórico; agora a conta principal tem cobranças reais.
**Reprodução:** o teste consulta uma cobrança com `ContaPagamentoRef("acc_subconta", lambda: "")` e vê a chave da conta principal no cabeçalho.
**Sugestão:** a chave do ambiente só vale quando `conta.conta_externa_id == CONTA_PRINCIPAL`; subconta sem chave levanta `ParceiroIndisponivel` (ou um erro próprio) antes de qualquer chamada, com log da conta (sem a chave).

### B-01 · Sentry pode receber o token do webhook e o corpo do aviso · baixa

**Onde:** `config/settings/base.py`, `sentry_sdk.init(send_default_pii=False)` sem filtro próprio.
**Problema:** num erro 500 na view do webhook, a integração Django do Sentry anexa o corpo da requisição (o padrão do `max_request_body_size` é `medium`) e os cabeçalhos. `send_default_pii=False` tira cookies e `Authorization`, mas não o `asaas-access-token`, e a lista padrão do `EventScrubber` não tem `creditCardToken`. Assim, o token do webhook da conta principal (ou da subconta) e o token do cartão podem ir para o Sentry. A falsificação do aviso tem impacto baixo (a baixa consulta o parceiro), por isso a severidade.
**Sugestão (devops):** `before_send` que descarta o `request.data` e o cabeçalho `asaas-access-token` nas rotas `/api/webhooks/`, ou `EventScrubber` com a lista padrão mais `asaas-access-token` e `creditcardtoken`, recursivo. Conferir com um erro provocado no sandbox do Sentry.

### B-02 · Recusa do parceiro na consulta deixa o aviso parado · baixa

**Onde:** `processar_webhook_fatura`: `ParceiroIndisponivel` volta à fila (certo), mas `ParceiroRecusou` (4xx que não é 404, como chave errada) sobe da tarefa sem `processado_em` nem `resultado`.
**Problema:** o aviso fica sem marca e a equipe só vê no log do worker. Não vaza nada; a fatura não é baixada, o que é o lado seguro.
**Sugestão:** tratar `ParceiroRecusou` como resultado (`parceiro_recusou`) e logar como os outros.

## Para a T-185 (rotas da assinatura)

A escrita barrada ao suporte e a exceção da `suspensa` ainda não têm código. Hoje as travas comuns se comportam assim, e é por isso que cada item abaixo precisa de teste:

- O suporte com "ver e editar" escreve em toda view que não tenha `suporte_proibido` (`comum.autenticacao.conferir_rota_do_suporte`).
- A única saída de `EmpresaOperando` é a lista `EXCECOES` de `tests/test_permissoes_das_rotas.py`, que tira a trava inteira: uma view ali aceita escrita também na `pausada` e na `cancelada`.

1. **Suporte (`PLT-07`, CA-ASS-19).** Toda view de escrita da assinatura com `suporte_proibido` nos métodos de escrita. A mensagem do contrato é "O suporte não mexe na assinatura da empresa", e a de `SUPORTE_PROIBIDO` é outra: a view passa a dela. Teste com token de suporte nos dois modos, em cada rota de escrita, e conferindo que nada mudou no banco nem no parceiro falso.
2. **Exceção da `suspensa` (`PLT-13`, CA-ASS-27).** Não usar `EXCECOES`. `EmpresaOperando` passa a aceitar escrita só quando `status == "suspensa"` e a view declara a exceção (por exemplo `escreve_na_suspensa = True`). Teste que a lista de views com o atributo é exatamente `PUT forma-pagamento/`, `POST faturas/{codigo}/pagar/` e `PATCH dados-fiscais/`, e que nelas `pausada` e `cancelada` seguem com 403 `empresa_sem_operacao`.
3. **Só o administrador.** Todas as rotas novas com `exige_perfil("administrador")` dentro de `com_padrao`; no `GET /api/assinatura/`, os blocos `forma_pagamento`, `dados_fiscais`, `oferta` e `acoes` ausentes para os outros perfis, com teste por perfil.
4. **Token fora da API.** O serializer da forma devolve só `bandeira` e `final`, com campos listados (nunca `__all__`). A guarda `test_adr_0023_nenhuma_rota_recebe_dado_do_cartao` pega `cartao_token` em `api/`.
5. **Trocar de forma apaga o token** (ADR 0023, item 3): `definir_cartao_token_cifrado(None)`, bandeira e final vazios, na mesma linha travada (`select_for_update`) que `_guardar_cartao` usa, para um aviso atrasado não regravar o cartão depois da troca. Auditoria `assinatura.forma_pagamento` só com a forma antiga e a nova.
6. **`pagar/` com `meio`** não troca a forma (já garantido na baixa: `test_plt_13_cartao_com_outra_forma_nao_guarda_token`); a rota não grava `forma`.
7. **Faturas por `codigo`** sempre filtradas pela empresa da requisição: `FAT-0001` existe em todas, e o teste usa duas empresas com o mesmo código (404 na de fora).
8. **`url_pagina`, `pix_copia_e_cola` e boleto** só na resposta ao administrador e nunca na auditoria.

O que fica para a T-199: 2 etapas recentes para trocar a forma de pagamento e para cancelar.

## Pendente fora desta revisão

- Sandbox do Asaas (handoff da T-184): se a cobrança paga na página devolve `creditCard.creditCardToken`. Se não devolver, o cartão passa à assinatura recorrente do parceiro e esta revisão vale de novo para o fluxo novo.
- O token cobra o cartão só junto com a chave da conta principal (`GIRO_ASAAS_CHAVE_API`). Essa chave é o segredo que mais pesa depois desta tarefa: só no gerenciador de segredos de produção, nunca no `.env` de homologação com a mesma conta (devops).

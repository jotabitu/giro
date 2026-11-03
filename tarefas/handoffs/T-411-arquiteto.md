# T-411 · Contrato do copiar link nas quatro ações · arquiteto → seguranca, depois backend e frontend

**O que foi feito:** o contrato do "Copiar link" nas quatro ações que enviam ao cliente (decisão do dono de 29 out 2026). Visão geral em `docs/api/copiar-link.md`; o detalhe de cada rota está no contrato do módulo.

| Ação | Como | Contrato |
| --- | --- | --- |
| Contrato para assinar | rota nova `POST /api/locacoes/{id}/contrato/link/`: gera token novo na hora e devolve o link uma vez (`no-store`), como o `link-convite` | `locacoes.md`, `contratos.md` |
| Cobrança da parcela | nada novo além de `acoes.copiar_cobranca`; copia `pix_copia_e_cola`, `linha_digitavel` e `boleto_url` da `cobranca_aberta` do dia | `financeiro.md` |
| Recibo da devolução | rota nova `POST /api/devolucoes/{id}/recibo/link/` (token de 7 dias, só o hash na `Devolucao`) e página pública `/recibo` com `POST /api/publico/recibos/consultar/` | `vistorias.md`, modelo de dados |
| Fatura da assinatura | nada novo na API; o pop-up "Pagar" mostra os campos do `cobranca` com "Copiar", e o aviso do cartão | `assinatura.md` |

**Por que duas formas:** o link do contrato e o do recibo abrem documento com dado pessoal e carregam token cujo banco guarda só o hash (`S-15`), então só aparecem na hora em que são gerados. A cobrança e a fatura copiam dados do parceiro que a API já devolve.

**Decisões técnicas tomadas (para a Segurança conferir):**
1. Um link vivo por objeto: copiar invalida o enviado e reenviar invalida o copiado (um hash só).
2. 7 dias de validade; o recibo não é de uso único (o cliente abre quantas vezes quiser), o contrato continua de uso único.
3. Suporte Giro: 403 `PLT-07` nas duas rotas novas (`AUD-09`).
4. Limite: 5 por hora por objeto e 20 por hora por pessoa; a página pública do recibo com o limite da assinatura pública (10/min por IP, 20 por token).
5. Eventos `contrato.copiar_link` e `devolucao.copiar_link_recibo`, categoria `seguranca`, sem link nem token.
6. A anonimização do titular (`AUD-06`) anula os tokens vivos do contrato e do recibo; copiar depois responde 409 `titular_anonimizado`.
7. O contrato em preparo (sem PDF) recusa com 409 `contrato_em_preparo`, para a tarefa de envio não trocar o token copiado logo depois.

**Pontos para a Segurança olhar:**
- A página pública nova do recibo (fotos, valores e primeiro nome do cliente atrás de um token de 7 dias).
- O `boleto_url` da cobrança (PDF do parceiro com nome e CPF do pagador) já sai para o token de suporte na representação da conta; não mudei, mas vale conferir contra a `AUD-09`.
- O aviso do cartão na fatura: quem abre o link de pagamento e digita o cartão o deixa guardado como forma da empresa (ADR 0023).

## Revisão da Segurança (PR #462) incorporada em 03 nov 2026

Nenhum achado alto. Aceitei os cinco; nenhuma discordância.

| Achado | O que entrou no contrato |
| --- | --- |
| M-01 (`AUD-09`) | Suporte recebe `boleto_url` `null` na cobrança (`financeiro.selectors.representacao_cobranca`, um lugar só) e `acoes.copiar_cobranca` `false`; na fatura, `url_boleto` e `url_pagina` sempre `null` para o suporte, de qualquer empresa (a recomendação da Segurança, sem olhar se é MEI). |
| M-02 (`LOC-15`) | Contrato ganha `token_assinatura_canal` (`whatsapp_email` ou `copiado`), `token_assinatura_gerado_por` e `token_assinatura_gerado_ip`, mantidos depois de assinar; a página de registro do PDF e o evento `contratos.contrato_assinado` dizem como o link chegou; `mesmo_ip_de_quem_copiou` só no evento. Aviso na tela "Mande o link ao cliente. Só ele pode assinar." (texto com o produto). |
| B-01 | E-mail aos administradores quando o cartão guardado muda pelo pagamento na página do parceiro (o primeiro cartão não avisa); evento com bandeira, final e titular. Texto com o produto. |
| B-02 | As tarefas de envio não geram token se já há um mais novo que a entrada delas na fila. |
| B-03 | `/recibo` com `no-store` e `noindex`; escopos próprios `recibo_publico_ip` e `recibo_publico_token`; teste entre empresas; e adotei o opcional: `devolucao.recibo_aberto`, no máximo um por token por dia. |

Também entraram: ordem da view (permissão, limite, serviço) e a cópia por `copiarQuandoChegar` no frontend.

Uma diferença pequena em relação à sugestão: o canal tem `whatsapp_email` num valor só, e não `whatsapp` e `email` separados, porque a tarefa de envio manda pelos dois canais de uma vez com o mesmo token.

**Fica para depois** (em `copiar-link.md`): o aditivo da renovação; trocar a URL de 15 minutos do WhatsApp do recibo (modelo 10, texto aprovado pela Meta) pelo link novo, que é do produto; uma página de pagamento do cliente final com a marca da locadora.

## Backend (depois da revisão da Segurança)

- `contratos.services.gerar_link(contrato, por)` e `locacoes.contrato.copiar_link`; view `contrato/link/`; `acoes.copiar_link_contrato`.
- `Devolucao.token_recibo_hash` (único, nulo) e `token_recibo_expira_em` (migração); `vistorias.services.gerar_link_recibo`; views `recibo/link/` e `publico/recibos/consultar/`; bloco `acoes` na devolução com `copiar_link_recibo`.
- Escopos novos em `comum.limites` (`link_contrato_*`, `link_recibo_*`, e o público do recibo).
- `clientes/titular.py`: anular os tokens vivos do contrato e do recibo.
- `financeiro.selectors.acoes_da_conta`: `copiar_cobranca`; `representacao_cobranca` sem `boleto_url` para o suporte; `url_boleto` e `url_pagina` da fatura `null` para o suporte.
- Contrato: os três campos do canal (migração), a página de registro e o evento da assinatura, o retry das tarefas de envio sem matar o link copiado.
- Plataforma: e-mail de cartão guardado trocado.
- Recibo público: escopos próprios, `no-store`/`noindex`, `devolucao.recibo_aberto`.
- Testes com o código no nome listados em cada contrato (`test_s_15_copiar_link_contrato_*`, `test_dev_02_copiar_link_recibo_*`, `test_dev_02_recibo_publico_*`, `test_aut_03_copiar_cobranca_*`). OpenAPI e `api:gerar`.

## Frontend (depois do backend)

- Reaproveitar o copiar do convite (`PainelDoUsuario.tsx`): campo só leitura, "Copiar", validade e aviso; o link só no estado do componente.
- Locacao-Detalhe: "Copiar link para assinar" por `acoes.copiar_link_contrato`.
- Receber e Caixa: "Copiar Pix" e "Copiar boleto" por `acoes.copiar_cobranca`; com `false` e `acoes.gerar_pix`, gerar e copiar da resposta.
- Devolução concluída: "Copiar link do recibo" por `acoes.copiar_link_recibo`; página pública `/recibo` como a `/assinar`.
- Admin-Assinatura: "Copiar link de pagamento" por `acoes.pagar`, com os campos do `cobranca` e o aviso do cartão.
- Teste de cada botão (aparece pela ação, copia o que veio, não guarda o link).

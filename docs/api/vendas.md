# Vendas

**Dono:** backend (a partir da T-502, ADR 0042, item 14) · **Versão:** 24 nov 2026 (T-502, fase 1c: envio da proposta, link público, metas e resumo; a 1b, do mesmo dia, trouxe a assinatura e `vendida`, com as lacunas das telas do #655; a 1a, de 22 nov, estados, proposta e aprovação) · **App:** `vendas` (schema da empresa) · **Regras:** VEN-01 a VEN-19, APR-01, AUT-19, FIN-09, IMP-04, CLI-03, CLI-05, DEV-02, LOC-16, FIL-02, PLT-12 · **ADRs:** 0011, 0015, 0019, 0024, 0037, 0042 · **Telas:** Vendas, Venda (Negócio → Documentos → Assinatura), Vendedor, Gerente, Locacao-Detalhe, Veiculo · **Critérios:** `docs/qa/criterios/T-420.md` (CA-420-11, 12, 16)

Convenções gerais em `docs/api/README.md`. Modelo: item 17 (`Venda`) em `docs/decisoes/modelo-de-dados.md` e item 3 da ADR 0042.

Duas origens de venda: a **de balcão** (o fluxo da `VEN-01` à `VEN-19`) e a **da quitação** da locação com intenção de compra (`VEN-11`, abaixo). As rotas marcadas **a seguir** estão no desenho (ADR 0042) e entram na fase 2 da T-502; até lá não existem.

| Fase | O que entra |
| --- | --- |
| 1a | estados, simular, criar, editar, enviar (só o estado e a data), resposta, pedir aprovação, decisão do desconto, perder, vencimento (`AUT-19`), comissão pendente, trava do estoque (`VEN-10`) |
| 1b | assinatura (contrato e conta da entrada), conclusão em `vendida`, perder com a entrada paga, o contrato assinado da venda perdida (item 6a), transferência da venda de balcão (`VEN-17`), a volta da aprovação que recomeça o prazo |
| **1c (esta)** | PDF e e-mail da proposta, link público, metas e resumo (funil, conversão, meta, ticket médio), propostas para retornar |
| 2 | troca e cancelamento |

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver a lista e o detalhe | sim | sim (filiais dele) | só as dele (`USR-08`) | — | sim |
| Simular, criar, editar, enviar, registrar resposta, pedir aprovação | sim | sim (filiais dele) | só as dele | — | — |
| Preparar e cancelar a assinatura, copiar o link e reenviar o contrato | sim | sim (filiais dele) | só as dele | — | — |
| Marcar como perdida | sim | sim (filiais dele) | só as dele (decisão do dono de 18 nov 2026); com a entrada paga, não (`VEN-19`) | — | — |
| Ver o PDF do contrato | sim | sim (filiais dele) | só as dele | — | sim |
| Decidir o desconto (`APR-01`, rotas de `aprovacoes`) | sim | sim (filiais dele) | — | — | — |
| Registrar a transferência no Detran | sim | sim (filiais dele) | — | — | — |

- As rotas `/api/vendas/...` só abrem com o recurso `vendas_comissoes` (403 `PLT-12`). A venda da quitação nasce em qualquer plano; sem o recurso, ela aparece pela locação e pelo veículo, e a transferência se registra pela rota da locação.
- Vistoriador: 403 em todas. Financeiro: só leitura (403 nas ações).
- Suporte Giro (`PLT-07`): em "ver e editar", edita, envia, registra resposta e marca perdida (a auditoria grava o suporte); **não cria venda nem pede desconto** (403 `PLT-07` "No modo suporte você não cria venda nem pede desconto."), porque a venda tem o vendedor da comissão e o pedido tem quem pede ao gerente. Também não copia o link do contrato para o cliente (403 `PLT-07` "No modo suporte você não gera link para o cliente.", como na locação). O interessado sem cadastro aparece mascarado para o suporte (`AUD-09`).

## A venda de balcão

### Estados (`VEN-13`, ADR 0042, item 2)

| De | Para | Rota (serviço) |
| --- | --- | --- |
| (nova) | `interessado`, `proposta` ou `aguardando_aprovacao` | `POST /api/vendas/` com `acao` = `interessado`, `enviar` ou `pedir_aprovacao` (`criar`) |
| `interessado` | `proposta` | `POST /enviar/` (`enviar_proposta`) |
| `interessado`, `proposta`, `negociacao` | `aguardando_aprovacao` | `POST /pedir-aprovacao/` (`pedir_desconto`) |
| `proposta` | `negociacao` | `POST /resposta/` (`registrar_resposta`) |
| `aguardando_aprovacao` | o estado de antes (o `interessado` aprovado vira `proposta` e é enviado) | decisão em `/api/aprovacoes/{id}/aprovar/` ou `/recusar/`, ou quem pediu cancela o pedido (`aplicar_decisao_desconto`, assinante de `aprovacoes.pedido_decidido`) |
| `interessado`, `proposta`, `negociacao`, `aguardando_aprovacao` | `perdida` | `POST /perder/` (`perder`), a rotina `AUT-19` ("proposta vencida") e o veículo vendido (`VEN-10`, "veículo vendido") |
| `proposta`, `negociacao` | `vendida` | `concluir_se_pronto`, com o contrato assinado e a entrada paga, em qualquer ordem (assinantes de `contratos.contrato_assinado` e `financeiro.parcela_paga`) |
| `vendida` | `cancelada` | **a seguir (2)** |

- Reenviar a proposta em `proposta` ou `negociacao` não muda o estado: só `proposta_enviada_em` (o vencimento conta dele).
- **A volta da aprovação recomeça o prazo** (decisão do dono de 23 nov 2026, `VEN-13`): a venda que volta de `aguardando_aprovacao` para `proposta`, aprovada ou recusada, grava a data da volta em `proposta_enviada_em`, sem reenviar nada ao cliente. Enviada em 01 out, aprovação pedida em 02 out e aprovada em 06 out: vence em 13 out. A que vinha de `negociacao` volta para ela e não vence. O pedido cancelado por quem pediu não mexe na data.
- A etapa "Assinatura" não é estado: a venda continua em `proposta` ou `negociacao`, com `situacao_texto` "Aguardando assinatura" ou "Aguardando entrada". A `AUT-19` vale também nela (ADR 0042, item 6a, opção A): a `proposta` assinada e sem a entrada vence no 7º dia depois do envio; a `negociacao` não vence.
- Erro de passagem: 409 `transicao_venda` (`{ "de", "para", "permitidos" }` em `detalhes`).
- Toda mudança de estado grava auditoria com a regra e atualiza `ultimo_contato_em` (`VEN-16`), como toda edição e todo envio.

### Contas (`VEN-02`, `VEN-04`, `FIN-09`, ADR 0042, item 4)

A API calcula; a tela só mostra. `Decimal` nas contas intermediárias, `ROUND_HALF_UP` no centavo.

- `desconto_centavos = preco_tabela × desconto_pct ÷ 100`; `preco_final = preco_tabela − desconto`. O preço de tabela é copiado do valor de venda do veículo na criação (`VEN-01`) e não muda depois.
- Formas (`VEN-03`, `VEN-18`): `a_vista` (a entrada é o preço final) e `entrada_parcelas` (2 a 24 parcelas). `financiamento` é recusado no campo `forma`: "O financiamento ainda não está disponível.". Não há cartão.
- Parcelas: sem juros, `saldo // n`, e a última leva a diferença; com juros (`ConfiguracaoEmpresa.juros_venda_mes_pct`, começa em 0%, copiado na criação e a cada edição), a parcela da tabela Price (`veiculos.precos.pmt`, a mesma conta da `VEI-16`), igual nas `n`.
- Comissão (`FIN-09`): `preco_final × ConfiguracaoEmpresa.comissao_venda_pct ÷ 100` (padrão 3%).
- Limite do desconto (`VEN-02`): 5% fixo (`vendas.calculo.LIMITE_DESCONTO_PCT`); até o maior desconto já aprovado da venda não se pede de novo.

VEN-0177: tabela R$ 22.900,00, 8% → desconto R$ 1.832,00, final R$ 21.068,00; entrada R$ 5.000,00, 12 × R$ 1.339,00; comissão R$ 632,04.

### Item da lista

```json
{
  "id": 177, "codigo": "VEN-0177", "status": "aguardando_aprovacao", "origem": "balcao",
  "origem_rotulo": "Balcão", "descricao": "",
  "cliente": { "id": 1312, "nome": "Diego Martins" },
  "interessado": null,
  "comprador_nome": "Diego Martins",
  "comprador_celular": "85983332211",
  "veiculo": { "id": 702, "placa": "RTA2C55", "modelo": "Honda CB 300F" },
  "filial": { "id": 1, "nome": "Filial Centro" },
  "vendedor": { "id": 3, "nome": "Bruna Alves" },
  "locacao": null,
  "valor": 2106800, "preco_final_centavos": 2106800,
  "forma": "entrada_parcelas", "forma_texto": "entrada + 12×",
  "situacao_texto": "Aguardando gerente",
  "motivo_perda": null,
  "proposta_enviada_em": null, "proposta_vence_em": null,
  "ultimo_contato_em": "2026-10-07T12:00:00Z",
  "perdida_em": null, "vendida_em": null,
  "comissao_centavos": 63204,
  "transferencia": { "feita_em": null, "registrada_por": null, "pendente": false },
  "contrato_pdf_disponivel": false,
  "acoes": {
    "editar": false, "enviar": false, "registrar_resposta": false, "pedir_aprovacao": false,
    "perder": true, "cancelar": false, "registrar_transferencia": false,
    "preparar_assinatura": false, "cancelar_assinatura": false,
    "copiar_link_contrato": false, "reenviar_contrato": false
  }
}
```

- `cliente` é nulo no interessado sem cadastro (`VEN-14`); aí vem `interessado: { "nome", "celular" }` (celular só dígitos). `comprador_nome` é um ou outro, para a lista.
- `comprador_celular` (fase 1c, `VEN-16`): o celular do "Chamar no WhatsApp", só dígitos, do cliente com cadastro ou do interessado; vazio sem celular. O suporte vê mascarado (`AUD-09`).
- `forma_texto`: "Pix à vista", "entrada + 12×" ou vazio. `situacao_texto` (`VEN-19`): "Interessado", "Proposta enviada", "Em negociação", "Aguardando gerente", "Aguardando assinatura" e "Aguardando entrada" (na etapa "Assinatura"), "Vendida 06 out", "Perdida · proposta vencida" (com o motivo da perda); na quitação, "Quitação de locação".
- `proposta_vence_em`: na `proposta`, a data em que ela vence sem resposta (último envio + 7 dias corridos, no fuso da filial, `VEN-13`); nos outros estados, nula.
- `comissao_centavos`: a comissão viva da venda (não estornada), ou nula.
- `contrato_pdf_disponivel` (`VEN-15`): o contrato da venda tem PDF (o assinado ou o gerado), o mesmo `contrato.pdf_disponivel` do detalhe. Na lista, o botão "Contrato" da vendida aparece só com ele; sem contrato, `false`.
- `acoes`: o que a pessoa pode fazer agora. `editar`, `enviar` e `pedir_aprovacao` só em `interessado`, `proposta` e `negociacao`, sem contrato; `registrar_resposta` só em `proposta`; `perder` nos estados em andamento (com a entrada paga, só gerente e administrador); `preparar_assinatura` em `proposta` e `negociacao` sem contrato; `cancelar_assinatura` com o contrato não assinado e a entrada não paga; `copiar_link_contrato` com o contrato enviado (ou gerado com o PDF pronto) e não assinado; `reenviar_contrato` com contrato; `registrar_transferencia` na `vendida` sem transferência, para administrador e gerente.

### Detalhe

O item da lista mais:

```json
{
  "calculo": {
    "preco_tabela_centavos": 2290000, "desconto_pct": "8.00", "desconto_centavos": 183200,
    "preco_final_centavos": 2106800, "forma": "entrada_parcelas", "entrada_centavos": 500000,
    "saldo_centavos": 1606800, "num_parcelas": 12, "juros_pct": "0.00",
    "parcela_centavos": 133900, "ultima_parcela_centavos": 133900,
    "total_parcelas_centavos": 1606800, "comissao_centavos": 63204, "comissao_pct": "3.00",
    "precisa_aprovacao": true, "limite_desconto_pct": "5.00"
  },
  "aprovacao": {
    "situacao": "pendente", "pedido_id": 41, "desconto_pedido_pct": "8.00",
    "desconto_aprovado_pct": null, "motivo_recusa": null,
    "texto": "Pedido de 8% enviado para Rodrigo Pinheiro. Você não edita a proposta até ele decidir."
  },
  "contrato": {
    "id": 88, "status": "enviado", "modelo": "Compra e venda", "versao": 1,
    "enviado_em": "2026-10-07T13:05:00Z", "assinado_em": null, "pdf_disponivel": true,
    "situacao_texto": "Aguardando assinatura. O cliente assina pelo celular.",
    "enviado_para": "diego.martins@exemplo.com.br",
    "enviado_texto": "Contrato enviado · 07 out, 10:05 · diego.martins@exemplo.com.br"
  },
  "conta_entrada": {
    "id": 5120, "status": "aberta", "valor_centavos": 500000, "vencimento": "2026-10-07",
    "rotulo": "Entrada de R$ 5.000,00", "texto": "Aguardando pagamento · vence hoje",
    "pago_em": null, "forma_texto": null
  },
  "documentos": null,
  "perder_texto": "A venda sai das abertas e o veículo fica livre para outra proposta.",
  "conclusao_texto": null
}
```

- `calculo` é nulo na venda da quitação. `comissao_pct` (fase 1c, `FIN-09`): o percentual da comissão da empresa, para "Comissão Bruna (3%)"; vem também no `simular`.
- `aprovacao` é nula sem pedido; `situacao`: `pendente`, `aprovado`, `recusado` ou `cancelado` (o último pedido). `texto` (`VEN-19`): pendente, "Pedido de 8% enviado para Rodrigo Pinheiro. Você não edita a proposta até ele decidir." (com mais de um gerente na filial, "para o gerente"); recusado, "Desconto de 8% recusado por Rodrigo Pinheiro: margem baixa neste mês. Dê até 5% ou peça uma nova aprovação."; nos outros, nulo.
- `contrato` (`VEN-15`): o contrato ligado à venda, com o resumo de `contratos` e a `situacao_texto`: "Contrato gerado", "Aguardando assinatura. O cliente assina pelo celular.", "Contrato assinado", "Contrato cancelado" e, na venda perdida, "Cancelado · venda perdida". Nulo antes de preparar a assinatura e depois de cancelá-la.
  - `enviado_para`: o e-mail do cliente para onde o link foi (o envio sai por e-mail quando o cliente tem e-mail, ADR 0034). Nulo antes do envio e sem e-mail no cadastro; o suporte vê mascarado (`AUD-09`).
  - `enviado_texto` (`VEN-19`): "Contrato enviado · 07 out, 10:20 · diego.martins@exemplo.com.br", no fuso da filial; sem e-mail, "Contrato enviado · 07 out, 10:20". Nulo antes do envio.
- `conta_entrada` (`VEN-15`): a entrada (ou o total à vista) em Contas a receber. `texto`: "Aguardando pagamento · vence hoje", "Aguardando pagamento · venceu em 07/10/2026", "Paga em 07 out, 11:02 · Pix" (no fuso da filial; sem a forma, "Paga em 07 out, 11:02") ou "Cobrança cancelada". `pago_em` e `forma_texto` ("Pix", "Dinheiro", "Cartão de débito"...) só na paga; nulos nos outros. Nula sem assinatura.
- `documentos` (etapa "Documentos", `VEN-14`, `VEN-19`): só em `proposta` ou `negociacao` com cliente e sem contrato. `pendencias`: os códigos de `clientes` (`CLI-03`, os mesmos do cadastro: `cnh_frente`, `consentimento`, `endereco`…); `gravidade` `alerta` ou `critica`; `texto`: "Falta completar o cadastro de Diego Martins para preparar a assinatura."; bloqueado, "Diego Martins está bloqueado e não pode comprar. A assinatura fica liberada depois do desbloqueio." (mais "Peça o desbloqueio ao gerente." para o vendedor); inativo, "Diego Martins está inativo e não pode comprar. O gerente ou o administrador reativa o cadastro."; `pode_preparar` falso em todos esses.
- `perder_texto` (`VEN-19`): o texto do diálogo "Marcar como perdida": "A venda sai das abertas e o veículo fica livre para outra proposta."; com a entrada paga, "A entrada de R$ 5.000,00 já foi paga. O valor vira um reembolso a fazer para o cliente." (gerente e administrador) ou "Só o gerente ou o administrador marca como perdida uma venda com a entrada paga." (vendedor). Nulo quando a pessoa não marca.
- `conclusao_texto` (`VEN-19`), na venda de balcão `vendida`: "Venda concluída. As 12 parcelas estão em Contas a receber, a comissão de R$ 632,04 foi lançada e o veículo saiu da frota de locação." (sem parcelas na venda à vista; sem a comissão sem o recurso `vendas_comissoes`).

### GET /api/vendas/ · GET /api/vendas/{id}/

Lista paginada (cursor) das vendas das filiais da pessoa, filtrada pela filial do `X-Filial` (`USR-07`), mais nova primeiro (com `?ordem=ultimo_contato`, da mais antiga para a mais recente pelo último contato, só as de balcão: as "Propostas para retornar" da `VEN-16`, fase 1c). Query: `?status=`, `?aba=abertas|minhas|aguardando|vendidas` (abertas = `interessado`, `proposta`, `negociacao` e `aguardando_aprovacao`), `?mes=AAAA-MM` (nas vendidas, pelo mês da venda; nas outras, pelo da criação, no fuso `America/Sao_Paulo`), `?filial=<id>`, `?origem=`, `?transferencia_pendente=true`, `?veiculo=<id>`, `?cliente=<id>`. Detalhe de outra filial ou de outro vendedor (para o vendedor): 404.

### POST /api/vendas/simular/

A tela chama a cada mudança (ADR 0005); não grava.
Corpo: `{ "veiculo_id" | "venda_id", "forma", "desconto_pct", "entrada_centavos", "num_parcelas" }`. Com `venda_id`, parte da venda (preço de tabela copiado, desconto já aprovado).
200: o `calculo` acima mais `erros` (`{ "campo": ["mensagem"] }`, vazio quando tudo fecha). 409 `VEN-01` com o veículo fora de `a_venda` ou sem valor de venda.

### POST /api/vendas/

A Nova venda.
```json
{
  "veiculo_id": 702,
  "cliente_id": 1312,
  "interessado": { "nome": "Carla Mendes", "celular": "85988771100" },
  "forma": "entrada_parcelas", "desconto_pct": "8.00",
  "entrada_centavos": 500000, "num_parcelas": 12,
  "acao": "interessado | enviar | pedir_aprovacao",
  "motivo": "Cliente fiel"
}
```
- `cliente_id` ou `interessado` (um dos dois). Só a ação `interessado` aceita o interessado sem cadastro (`VEN-14`).
- `interessado`: forma e desconto opcionais; desconto acima de 5% recusado.
- `enviar`: cliente com CPF (400 em `cliente_id`, "Cadastre o cliente com o CPF para enviar a proposta." ou "Complete o CPF do cliente para enviar a proposta."), forma completa, desconto até o limite (400 em `desconto_pct`, "Acima de 5% precisa do gerente. Use Pedir aprovação."). Nasce em `proposta`, e o PDF e o e-mail saem como no `POST /enviar/`.
- `pedir_aprovacao`: como `enviar`, com o desconto acima do limite (400 se não passar: "Até 5% você dá sem o gerente. Use Salvar proposta."); nasce em `aguardando_aprovacao` com o estado de antes `interessado`, abre o pedido `APR-01` e lança a comissão `pendente` (`FIN-09`). `motivo` vai para o pedido.
- O vendedor é quem cria (`FIN-09`); a filial é a do veículo.
- 201: o detalhe. 409 `VEN-01` (veículo fora de `a_venda` ou sem valor de venda); 409 `VEN-10` "Este veículo tem uma venda em andamento (VEN-0177)." (com `detalhes.venda_id` da venda aberta) quando a ação abre a venda (`proposta` ou `aguardando_aprovacao`) e já há outra aberta; o `interessado` não conta.

### PATCH /api/vendas/{id}/

Campos da proposta: `cliente_id`, `interessado` (só sem cliente), `forma`, `desconto_pct`, `entrada_centavos`, `num_parcelas`. Os juros são copiados da empresa de novo; a comissão pendente acompanha o preço (`FIN-09`); o motivo da recusa sai. O link público e o PDF da proposta de antes deixam de valer (S-15, revisão da Segurança no #650): o token é anulado e a venda deixa de apontar para o PDF (o arquivo fica guardado, ADR 0009); o próximo "Enviar" ou "Copiar link" grava o PDF de agora.
- 400 em `desconto_pct` acima do limite (até o desconto aprovado, passa). Em `proposta` e `negociacao`, o cliente com CPF e a forma completa continuam obrigatórios.
- 409 `APR-01` "A venda está esperando o gerente. Espere a decisão ou cancele o pedido." em `aguardando_aprovacao`; 409 `VEN-06` "Cancele a assinatura para mudar a proposta." com contrato; 409 `transicao_venda` "Esta venda não se edita mais." em `vendida`, `perdida` e `cancelada`.

### POST /api/vendas/{id}/enviar/

Sem corpo. `interessado` → `proposta` (pede o cliente com CPF, a forma e o desconto até o limite; 409 `VEN-10` se o veículo já tem venda aberta), ou reenvio em `proposta`/`negociacao` sem mudar o estado. Grava `proposta_enviada_em` (e `entrou_proposta_em` na primeira vez).
200: `{ "email_enviado": true, "texto": "Proposta enviada para diego@exemplo.com em 07 out. Sem resposta do cliente, ela vence em 14 out.", "venda": { ...detalhe } }`. 409 `APR-01` em `aguardando_aprovacao`.

**PDF e e-mail (fase 1c, `VEN-15`, ADR 0042, item 8).** Depois do commit, a tarefa `vendas_enviar_proposta` grava o PDF da proposta (texto fixo do sistema, com a marca da locadora: veículo, preço de tabela, desconto, preço final, forma, entrada, parcelas, até quando vale e quem atende; a troca entra na fase 2) no armazenamento privado e o manda por e-mail ao cliente, anexo (`proposta-VEN-0177.pdf`; assunto "Moto Rápida: proposta da VEN-0177"). Nada vai pelo WhatsApp do sistema. Cada envio grava o PDF de novo (o arquivo antigo fica guardado); a tarefa de um envio mais antigo não manda nada.
- `email_enviado`: `true` quando o cliente tem e-mail no cadastro. Sem e-mail, a venda muda de estado do mesmo jeito (conta como enviada, e o vencimento corre dali), o PDF é gravado e `email_enviado` vem `false`.
- `texto` (`VEN-19`), pronto para a tela: com e-mail, "Proposta enviada para diego@exemplo.com em 07 out. Sem resposta do cliente, ela vence em 14 out." (em `negociacao`, só a primeira frase, porque a proposta não vence); sem e-mail, "A proposta foi salva, mas este cliente não tem e-mail cadastrado. Copie o link e envie para ele."
- A volta da aprovação (`VEN-13`, 23 nov 2026) não manda o e-mail sozinha: o envio é o do botão.

### POST /api/vendas/{id}/resposta/

`{ "nota": "Quer pensar até sexta" }` (até 300, opcional; vai só para a auditoria). `proposta` → `negociacao`. 200: o detalhe. Fora de `proposta`: 409 `transicao_venda`.

### POST /api/vendas/{id}/pedir-aprovacao/

`{ "desconto_pct": "8.00", "motivo": "Cliente fiel" }`. De `interessado`, `proposta` ou `negociacao` para `aguardando_aprovacao`, guardando o estado de antes; abre o pedido `APR-01` (`valor_centavos` = o desconto em reais, que os "Descontos aprovados" da `APR-12` somam; o `resumo` traz veículo, tabela, com desconto, desconto e forma) e lança ou recalcula a comissão `pendente`.
- 400 em `desconto_pct` até o limite (ou até o já aprovado); 400 sem cliente com CPF ou sem forma.
- 409 `pedido_pendente` se já há pedido pendente; 409 `VEN-10` vindo de `interessado` com outra venda aberta do veículo.

**A decisão** sai nas rotas de `aprovacoes` (`APR-07`, `APR-09`) e volta pelo evento `aprovacoes.pedido_decidido`:
- aprovado: `aprovacao = aprovado`, `desconto_aprovado_pct` = o pedido, volta ao estado de antes; a que vinha de `interessado` vira `proposta` e é enviada sozinha na aprovação (`VEN-13`, decisão do dono de 18 nov 2026, #665): a tarefa `vendas_enviar_proposta` grava o PDF e manda o e-mail depois do commit, como no "Enviar", e a data da aprovação é a do envio; sem e-mail no cadastro, vale o "Cliente sem e-mail" da `VEN-19` (só o PDF, para o "Copiar link"). A que vinha de `proposta` ou `negociacao` não é reenviada: o vendedor usa "Enviar". A que volta para `proposta` recomeça o prazo (`proposta_enviada_em` = agora);
- recusado: desconto 0, preço e comissão pendente refeitos, `motivo_recusa` gravado, volta ao estado de antes (a `proposta` recomeça o prazo) e o vendedor é avisado no sino ("Desconto da VEN-0177 recusado: Margem baixa", `tipo = "desconto_recusado"`, link `/vendas/{id}`);
- cancelado (quem pediu desistiu): como recusado, sem motivo nem aviso.

### POST /api/vendas/{id}/perder/

`{ "motivo": "Comprou em outra loja" }` (obrigatório, até 200; 400 "Informe o motivo."). De qualquer estado em andamento para `perdida`; cancela o pedido de desconto pendente (o pedido vai para `cancelado`) e estorna a comissão pendente (`FIN-09`). O vendedor perde as próprias vendas; gerente e administrador, as da filial. 200: o detalhe. Fora dos estados em andamento: 409 `transicao_venda`.

Na etapa "Assinatura" (ADR 0042, item 6a, padrão A), a perda (marcada, vencida pela `AUT-19` ou pela `VEN-10`) também:
- cancela o contrato: o não assinado e o **assinado** (`contratos.services.cancelar_assinado`; o PDF assinado e a prova da assinatura ficam guardados), com o motivo "Venda perdida: <motivo>". O contrato continua ligado à venda e aparece como "Cancelado · venda perdida";
- cancela a conta da entrada em aberto (sem reembolso). Se o cliente pagar depois um Pix ou boleto já gerado, o pagamento vira a pendência "sem conta" do financeiro;
- com a entrada **paga**: só gerente ou administrador (403 `VEN-19` "Só o gerente ou o administrador marca como perdida uma venda com a entrada paga." para o vendedor), e o valor vira um `Reembolso` "a fazer" por Pix, com o motivo "Venda perdida com a entrada paga" (`DEV-02`; aviso aos gerentes da filial pelo financeiro).

### POST /api/vendas/{id}/assinatura/ (preparar)

Sem corpo. "Preparar assinatura", da etapa "Documentos" para a "Assinatura" (`VEN-15`; ADR 0042, item 6). A venda continua em `proposta` ou `negociacao`. Na mesma transação:
1. o contrato com o modelo publicado de compra e venda (finalidade `venda`), com os marcadores `venda.*`; o PDF e o envio do link saem depois do commit, como na retirada (`contratos`);
2. a conta da entrada (tipo `entrada`; observação "Pagamento à vista" na forma à vista), valor = `entrada_centavos`, vencimento hoje no fuso da filial, com `aguarda_retirada = true`: não fica `vence_hoje` nem `atrasada`, não entra na régua (`AUT-03`) nem no bloqueio (`CLI-05`) e não tem multa nem juros. Paga-se por Pix ou boleto do parceiro ou no caixa, pelas rotas do financeiro.

200: o detalhe, com `contrato` e `conta_entrada`. Erros:
- 409 `APR-01` em `aguardando_aprovacao`; 409 `transicao_venda` "A assinatura sai de uma proposta enviada." fora de `proposta` e `negociacao`; 409 `VEN-06` "A assinatura desta venda já foi preparada.";
- 409 `VEN-02` com o desconto acima do limite e não aprovado; 400 sem cliente com CPF ou sem forma;
- 409 `CLI-05` "O cliente está bloqueado e não pode comprar." ou "O cliente está inativo e não pode comprar."; 422 `CLI-03` "Complete o cadastro do cliente antes da assinatura." (com `detalhes.pendencias`);
- 409 `VEN-01` "Este veículo não está mais à venda.";
- 422 `IMP-04` "Publique um modelo de contrato de compra e venda antes de concluir a venda." com `detalhes.link = "/admin/contratos"`.

### DELETE /api/vendas/{id}/assinatura/ (cancelar)

"Cancelar a assinatura" (`VEN-19`): o contrato não assinado vai para `cancelado` e a conta da entrada em aberto para `cancelada`; nada se apaga, a venda fica no estado em que estava e volta a se editar. 200: o detalhe (com `contrato` e `conta_entrada` nulos).
- 409 `VEN-06` "A entrada já foi paga. Para desfazer, marque a venda como perdida.";
- 409 `VEN-06` "O cliente já assinou o contrato. Para mudar a proposta, marque esta venda como perdida e faça uma nova." (ADR 0042, item 6a);
- 409 `transicao_venda` "Esta venda não tem assinatura para cancelar.".

### O contrato da venda

| Rota | O que faz |
| --- | --- |
| `POST /api/vendas/{id}/contrato/link/` | "Copiar link para assinar" (T-411, S-15): token novo agora, o anterior deixa de valer. 200 `{ link, expira_em, aviso, contrato }` com `Cache-Control: no-store`; o limite de chamadas é o da locação. 409 `sem_contrato`, `contrato_em_preparo`, `contrato_assinado`; 403 `PLT-07` para o suporte |
| `POST /api/vendas/{id}/contrato/reenviar/` | novo link e novo envio (o anterior deixa de valer). 202 `{ contrato_id, status }`; 409 `sem_contrato` |
| `GET /api/vendas/{id}/contrato/pdf/` | URL de 15 minutos do PDF (o assinado, se houver; AUD-05). Também na venda `vendida` (o "Recibo" vira "Contrato", `VEN-15`) e no cancelado da perdida. 404 sem PDF |

A assinatura é a da locação (`/api/publico/assinaturas/...`): o nome confere com o cadastro, grava IP, data e hora e aparelho, e publica `contratos.contrato_assinado`.

### Conclusão: `vendida` (`VEN-06`, `VEN-15`; ADR 0042, item 7)

Com o contrato assinado e a entrada paga (ou sem conta de entrada), em qualquer ordem, na transação do evento que completou a segunda condição (assinantes de `contratos.contrato_assinado` e `financeiro.parcela_paga` com `tipo = "entrada"`). Ator Sistema; idempotente.
1. `vendida_em` = agora; `proposta`/`negociacao` → `vendida` (auditoria `venda.concluir`, `VEN-06`);
2. o veículo `a_venda` → `vendido` (origem na venda) e os outros `interessado` dele → `perdida` "veículo vendido" (`VEN-10`);
3. forma `entrada_parcelas`: as parcelas em Contas a receber (tipo `parcela`, 1..n), a 1ª um mês depois do dia da venda e as outras no mesmo dia dos meses seguintes (no mês sem o dia, o último), a diferença de centavos na última; nascem normais (régua, multa e juros da `FIN-03`, pela cláusula do contrato). VEN-0177 vendida em 07 out: 12 × R$ 1.339,00, de 07/11/2026 a 07/10/2027;
4. a comissão pendente é recalculada sobre o preço final e confirmada (paga no dia 5 do mês seguinte); sem pendente, nasce e é confirmada (`FIN-09`). VEN-0177: R$ 632,04;
5. a transferência no Detran vira tarefa (`VEN-17`, abaixo).

Se o veículo não estiver mais `a_venda` (a trava da `VEN-10` impede), a venda não conclui, a baixa e a assinatura gravam, o erro vai para o Sentry e os gerentes e administradores recebem o aviso `venda_nao_concluida`.

### POST /api/vendas/{id}/transferencia/

Perfis: administrador e gerente da filial (recurso `vendas_comissoes`). `{ "feita_em": "2026-10-15" }` (não depois de hoje, não antes da venda). Para as duas origens; a da quitação também continua pela rota da locação.
- 200: o detalhe, com `transferencia.pendente = false`.
- 409 `VEN-17` (`VEN-11` na quitação) "A transferência desta venda já foi registrada."; 409 "A transferência sai depois de a venda ser concluída." fora de `vendida`; 400 em `feita_em`; 403 para os outros perfis.

### Rotas a seguir

| Rota | Fase | O que faz |
| --- | --- | --- |
| `POST /api/vendas/{id}/cancelar/` | 2 | cancelamento (`VEN-07`); até lá não há rota, e `vendas.services.cancelar` responde 409 `VEN-07` "O cancelamento de venda ainda não está disponível." |

### POST /api/vendas/{id}/proposta/link/ (fase 1c)

"Copiar link" (`VEN-15`, `VEN-19`), como o link do recibo da devolução (T-411, S-15). Quem mexe na venda (o vendedor nas dele, gerente e administrador nas da filial); o suporte não gera link (403 `PLT-07` "No modo suporte você não gera link para o cliente."). Sem corpo.
- Só com a proposta enviada e aberta (`proposta` ou `negociacao`); fora disso, 409 `transicao_venda` "O link existe só para a proposta enviada e ainda aberta.". Cliente anonimizado: 409 `titular_anonimizado`.
- Anonimização do titular (`AUD-06`, padrão A do dono, #665): `clientes.titular` apaga o PDF da proposta de todas as vendas do cliente (a pasta `<schema>/vendas/venda/<id>/`, com as versões antigas) e anula o link; a venda continua, com o cliente anonimizado.
- Grava o PDF de novo a cada link (o do link é sempre o da proposta de agora); cria um token de 32 bytes (`secrets.token_urlsafe`), guarda só o hash SHA-256 e o vencimento (7 dias); o token anterior deixa de valer (um vivo por venda). Não envia nada e não muda o estado nem o vencimento da proposta.
- 200, com `Cache-Control: no-store`: `{ "link": "https://motorapida.giro.ceo/proposta#<token>", "expira_em": "2026-10-14T13:00:00Z", "aviso": "O link anterior deixa de valer." }`. O token vai no fragmento do link: não chega a log de servidor nem ao `Referer`, e aparece só nesta resposta.
- Limites: 5 por hora por venda e 20 por hora por pessoa (429).
- Auditoria `venda.copiar_link_proposta` (segurança, regra `S-15`), com o vencimento e sem o token.
- Desligado por `GIRO_PROPOSTA_PUBLICA` (padrão: desligado, até a revisão da Segurança e a página `/proposta` do frontend): 409 `proposta_publica_desligada` "O link da proposta ainda não está disponível. Use Enviar para mandar a proposta.", sem gerar nada.

### POST /api/publico/propostas/consultar/ (fase 1c)

A página pública `/proposta` lê o token do fragmento e o manda no corpo: `{ "token": "<token>" }`. Sem login, no host da empresa (o schema vem do host), com o recurso `vendas_comissoes`. **Diferença do desenho:** a ADR 0042 (item 14) escreveu `GET /api/publico/propostas/{token}/`; a rota segue o padrão do recibo e da assinatura (S-15), com o token no corpo de um POST e não na URL, para não ir a log de servidor, de proxy nem ao histórico do navegador.
- 200, com `Cache-Control: no-store` e `X-Robots-Tag: noindex`:
```json
{
  "empresa": { "nome_exibicao": "Moto Rápida", "logo_url": null, "cor_marca": null },
  "proposta": {
    "codigo": "VEN-0177", "cliente_primeiro_nome": "Diego", "veiculo": "Honda CB 300F",
    "vence_em": "2026-10-14", "pdf_url": "https://...", "pdf_url_expira_em": "2026-10-07T13:15:00Z"
  }
}
```
  Só o primeiro nome do cliente e o veículo sem a placa; o resto está no PDF, por URL assinada de 15 minutos (`AUD-05`).
- 404 para token desconhecido ou anulado (sem dizer qual: o link novo, a edição da proposta e a anonimização do titular anulam), com o link desligado e com o cliente anonimizado; 410 `link_expirado` depois dos 7 dias ou com a venda fora de `proposta`/`negociacao` (vendida, perdida). Não é de uso único.
- Limites: 10 por minuto por IP e 20 por minuto por token (429).
- Cada abertura grava `venda.proposta_aberta` (segurança, ator Sistema, regra `VEN-15`, IP truncado na rede e aparelho), no máximo uma por token por dia.

### GET /api/vendas/resumo/?filial=&mes= (fase 1c)

Os números da tela `Vendas` e do início do vendedor (`VEN-08`, `VEN-09`, `VEN-12`, `VEN-16`, `VEN-19`; ADR 0042, item 13). Administrador, gerente, vendedor (só os números dele, `USR-08`) e financeiro. Filiais do `X-Filial` (`USR-07`); `?filial=` escolhe uma delas; `?mes=AAAA-MM` (padrão: o mês de hoje; fora do formato, 400 em `mes`). Sempre a venda de balcão (a da quitação fica fora), com as datas em `America/Sao_Paulo`.
```json
{
  "mes": "2026-10-01", "subtitulo": "Vendas de outubro · Filial Centro",
  "funil": { "interessados": 12, "proposta": 6, "negociacao": 3, "vendido": 4 },
  "conversao": { "vendidas": 4, "criadas": 12, "pct": 33 },
  "vendido": {
    "quantidade": 4, "soma_centavos": 3120000, "ticket_centavos": 780000, "vazio": null,
    "mes_anterior": { "quantidade": 4, "soma_centavos": 5500000, "ticket_centavos": 1375000 }
  },
  "em_negociacao": { "quantidade": 3, "soma_centavos": 5606800, "aguardando_aprovacao": 1 },
  "a_venda": 9,
  "meta": {
    "valor_centavos": 5000000, "vendido_centavos": 3120000, "pct": 62, "faltam_dias": 24,
    "texto": "62% de R$ 50.000,00 · faltam 24 dias"
  },
  "transferencias_pendentes": 1,
  "propostas_para_retornar": [
    { "venda_id": 177, "codigo": "VEN-0177", "comprador_nome": "Diego Martins", "celular": "85983332211",
      "veiculo": "Honda CB 300F · RTA-2C55", "valor_centavos": 2106800,
      "situacao_texto": "Aguardando gerente", "ultimo_contato_em": "2026-10-07T12:00:00Z" }
  ],
  "propostas_vazio": null
}
```
- `funil` (`VEN-08`): interessados = criadas no mês (também as que nasceram em `proposta`); proposta = primeira entrada em `proposta` no mês; negociação = primeira entrada em `negociacao` ou `aguardando_aprovacao` no mês; vendido = `vendida` no mês e ainda `vendida`.
- `conversao`: vendidas ÷ criadas nos últimos 30 dias, inteiro para baixo; `pct` nulo sem venda criada.
- `vendido` (`VEN-12`): número, soma dos preços finais e ticket médio (`ROUND_HALF_UP`) das vendas que viraram `vendida` no mês e continuam `vendida`; `vazio`: "Sem vendas em outubro.". É a mesma leitura do bloco "Ticket médio do mês" do início (`painel.md`, T-487), que agora conta as vendas de balcão concluídas.
- `em_negociacao`: soma do preço final e número das vendas `proposta`, `negociacao` e `aguardando_aprovacao` (`VEN-19`: R$ 56.068,00 em 3 propostas abertas).
- `meta` (`VEN-09`): a do vendedor (a dele nas filiais) ou a das filiais (a soma das metas dos vendedores); `pct` inteiro para baixo; `faltam_dias` = dias corridos até o fim do mês, só no mês corrente (nulo nos outros); sem meta, `valor_centavos` e `pct` nulos e `texto` "Sem meta em outubro.".
- `transferencias_pendentes`: vendidas sem a transferência no Detran registrada (as duas origens).
- `propostas_para_retornar` (`VEN-16`): as abertas (`interessado`, `proposta`, `negociacao`, `aguardando_aprovacao`), da mais antiga para a mais recente pelo último contato, até 10; `celular` mascarado para o suporte. `propostas_vazio`: para o vendedor sem abertas, "Você não tem propostas abertas."; nulo nos outros casos.
- O início do vendedor (`GET /api/painel/inicio/`, variante `vendedor`) traz `meta`, `funil` (com `conversao`) e `propostas` (`{ "abertas", "para_retornar", "vazio" }`) deste resumo; sem o módulo de vendas (`PLT-12`), nulos. O contador `propostas` do menu é o número de abertas.

### GET /api/vendas/metas/?filial=&mes= · PUT /api/vendas/metas/ (fase 1c)

Metas por vendedor, filial e mês (`VEN-09`). Administrador e gerente das filiais dele (403 para os outros perfis). A filial vem de `?filial=` (no `PUT`, de `filial_id`) ou da filial única do `X-Filial`; com "Todas as filiais" e sem filial escolhida, 400 em `filial` "Escolha a filial.".
- `GET` 200:
```json
{
  "filial": { "id": 1, "nome": "Filial Centro" }, "mes": "2026-10-01",
  "vendedores": [ { "vendedor": { "id": 3, "nome": "Bruna Alves" }, "valor_centavos": 5000000 } ],
  "soma_centavos": 5000000,
  "texto": "Defina a meta de cada vendedor da Filial Centro. Deixe em branco para ficar sem meta.",
  "ajuda": "A meta da filial é a soma das metas dos vendedores e se atualiza ao salvar."
}
```
  `vendedores`: os vendedores ativos ligados à filial, pelo nome, com `valor_centavos` nulo sem meta; `soma_centavos` nulo sem nenhuma meta.
- `PUT` `{ "filial_id": 1, "mes": "2026-10", "metas": [ { "vendedor_id": 3, "valor_centavos": 5000000 } ] }`: grava ou muda a meta de cada vendedor; `valor_centavos: null` tira a meta (a linha sai; é a única exclusão física aceita, porque meta não é registro de negócio com efeito). Responde o quadro do `GET`. Quem não é vendedor ativo da filial: 400 em `metas` "Escolha vendedores ativos desta filial."; valor menor que 1: 400.
- Auditoria `meta_venda.definir` (configurações, regra `VEN-09`, antes e depois) e `meta_venda.tirar` (com o valor de antes).

### Vencimento da proposta (`AUT-19`)

Tarefa `aut_19_vencer_propostas` (o Beat chama `aut_19_vencer_propostas_de_todas` às 02:40), por empresa com o recurso `vendas_comissoes`. A venda `proposta` cuja data local do último envio + 7 dias ≤ hoje vai para `perdida` com o motivo "proposta vencida" (enviada em 07 out, perdida na rodada de 14 out). `interessado`, `negociacao` e `aguardando_aprovacao` não vencem. Ator Sistema, regra `AUT-19`; idempotente.

### Trava do estoque (`VEN-10`)

Com venda aberta (`proposta`, `negociacao`, `aguardando_aprovacao`), "Voltar para a frota" e "Baixar" o veículo respondem 409 `{ "codigo": "VEN-10", "mensagem": "Este veículo tem uma venda em andamento (VEN-0177).", "detalhes": { "venda_id": 177 } }` (trava registrada por `vendas` em `veiculos.services.registrar_trava_do_estoque`).

## A venda da quitação

```json
{
  "id": 18, "codigo": "VEN-0178", "status": "vendida", "origem": "quitacao_locacao",
  "origem_rotulo": "Quitação de locação",
  "descricao": "Quitação da LOC-2901",
  "cliente": { "id": 1310, "nome": "Lucas Ferreira" },
  "veiculo": { "id": 640, "placa": "RTA2C55", "modelo": "Honda CG 160 Fan" },
  "filial": { "id": 1, "nome": "Filial Centro" },
  "vendedor": { "id": 3, "nome": "Bruna Alves" },
  "locacao": { "id": 2901, "codigo": "LOC-2901" },
  "preco_final_centavos": 0,
  "vendida_em": "2028-10-10T13:20:00Z",
  "transferencia": { "feita_em": null, "registrada_por": null, "pendente": true }
}
```

Com os outros campos do item da lista: `forma` e `forma_texto` vazios, `situacao_texto` "Quitação de locação", `calculo` nulo, `acoes.registrar_transferencia` como abaixo e as outras ações `false`.

- Nasce pelo assinante de `locacoes.locacao_quitada`, na transação da quitação (`vendas.services.criar_venda_da_quitacao`, ADR 0037, item 4): já `vendida`, R$ 0,00, cliente, veículo e filial da locação, vendedor da locação, `vendida_em` = `quitada_em`. Sem contas a receber, sem contrato de compra e venda e sem comissão (`FIN-09`). Auditoria `venda.criar_da_quitacao`, ator Sistema, regra `VEN-11`.
- Na mesma transação, o veículo vai de `alugado` para `vendido` por `veiculos.services.transicionar`, com a origem na venda e o motivo "Quitação da LOC-2901" (`VEN-06`).
- O cancelamento responde 409 `{ "codigo": "VEN-11", "mensagem": "A venda da quitação de uma locação não se cancela." }`.
- Fica fora de funil, conversão, meta e comissão (`VEN-08`, `VEN-09`, `FIN-09`): toda conta dessas filtra `origem = "balcao"`.

## A tarefa da transferência

Não há entidade de tarefa: a pendência é a venda `vendida` com `transferencia.feita_em` nula (ADR 0037, item 6), das duas origens: a da quitação (`VEN-11`) e a de balcão concluída (`VEN-17`, desde a 1b). `?transferencia_pendente=true` e `transferencia.pendente` seguem a mesma regra.

**Aviso da venda de balcão** (`VEN-17`; texto proposto pelo arquiteto, ADR 0042, item 7, para o Produto confirmar). Na conclusão, depois do commit, aos mesmos destinatários da quitação, no sino e por e-mail:
```
tipo: "transferencia_venda"
titulo: "Fazer a transferência no Detran: RTA-2C55 para Diego Martins. VEN-0177 vendida em 07/10/2026."
link: "/vendas/177"
urgente: false
chave: "venda-transferencia-{venda_id}"
```

**Aviso da quitação.** Ao nascer a venda da quitação, depois do commit, os gerentes ativos da filial (`FIL-02`) e os administradores ativos da empresa, sem repetir pessoa (`vendas.services.destinatarios_da_transferencia`; decisão do dono em 12 nov 2026), recebem no sino e por e-mail:
```
tipo: "transferencia_quitacao"
titulo: "Fazer a transferência no Detran: RTA-2C55 para Lucas Ferreira. LOC-2901 quitada em 10/10/2028."
link: "/locacoes/2901"
urgente: false
chave: "quitacao-transferencia-{venda_id}"
```

**Pendência no painel.** `vendas.selectors.transferencias_pendentes(filiais)`, a mais antiga primeiro:
- quitação: `{ "tipo": "transferencia_quitacao", "locacao_id": 2901, "venda_id": 18, "destino": { "chave": "locacoes", "id": 2901 }, "rotulo": "Transferência no Detran · RTA-2C55", "detalhe": "Lucas Ferreira · LOC-2901 quitada em 10/10/2028", "link": "/locacoes/2901" }`;
- balcão: `{ "tipo": "transferencia_venda", "locacao_id": null, "venda_id": 177, "destino": { "chave": "vendas", "id": 177 }, "rotulo": "Transferência no Detran · RTA-2C55", "detalhe": "Diego Martins · VEN-0177 vendida em 07/10/2026", "link": "/vendas/177" }`.

O painel (`relatorios`) usa o `destino` de cada item.

### POST /api/locacoes/{id}/transferencia/

Perfis: administrador e gerente da filial. Sob a locação, para abrir em qualquer plano (recurso `locacoes_vistoria`).
Corpo: `{ "feita_em": "2028-10-15" }` (não depois de hoje, não antes de `quitada_em`).
- 200: o detalhe da locação, com `compra.venda.transferencia = { "feita_em", "registrada_por": { "id", "nome" }, "pendente": false }`.
- Auditoria `venda.registrar_transferencia` e uma linha no histórico do veículo.
- 409 `VEN-11` "A transferência desta venda já foi registrada."; 404 se a locação não tem venda da quitação; 400 em `feita_em`; 403 para os outros perfis e para o suporte em "só ver".

## Na auditoria

| Ação | Regra | `resumo` | `detalhe` |
| --- | --- | --- | --- |
| `venda.criar` | VEN-13 | Criou a venda VEN-0177 | o estado inicial ("Aguardando gerente") |
| `venda.editar` | VEN-02 | Editou a proposta da VEN-0177 | |
| `venda.enviar_proposta` | VEN-13 | Enviou a proposta da VEN-0177 | |
| `venda.reenviar_proposta` | VEN-15 | Reenviou a proposta da VEN-0177 | |
| `venda.registrar_resposta` | VEN-13 | Registrou a resposta do cliente da VEN-0177 | a nota |
| `venda.pedir_desconto` | APR-01 | Pediu desconto de 8,00% na VEN-0177 | o motivo |
| `venda.aprovar_desconto`, `venda.recusar_desconto`, `venda.cancelar_desconto` | APR-01 | Desconto da VEN-0177 aprovado (ou recusado); Pedido de desconto da VEN-0177 cancelado | o motivo |
| `venda.perder` | VEN-13 | Marcou como perdida a venda VEN-0177 | o motivo |
| `venda.vencer_proposta` | AUT-19 | Proposta da VEN-0177 vencida | 7 dias sem resposta do cliente |
| `venda.perdida` | VEN-10 | Venda VEN-0177 perdida | veículo vendido |
| `venda.preparar_assinatura` | VEN-15 | Preparou a assinatura da VEN-0177 | Contrato gerado e entrada em Contas a receber |
| `venda.cancelar_assinatura` | VEN-19 | Cancelou a assinatura da VEN-0177 | Contrato e cobrança da entrada cancelados |
| `venda.registrar_assinatura` | VEN-15 | Cliente assinou o contrato da VEN-0177 | |
| `venda.registrar_entrada` | VEN-15 | Entrada da VEN-0177 paga | |
| `venda.concluir` | VEN-06 | Venda VEN-0177 concluída | Contrato assinado e entrada paga |
| `contrato.cancelar_assinado` | — | Cancelou o contrato VEN-0177 | Venda perdida: <motivo> |
| `reembolso.criar` | DEV-02 | texto do financeiro | Venda perdida com a entrada paga |
| `comissao.lancar`, `comissao.recalcular`, `comissao.estornar` | FIN-09 | texto genérico | |
| `venda.copiar_link_proposta` | S-15 | Copiou o link da proposta da VEN-0177 | o vencimento do link (fase 1c) |
| `venda.proposta_aberta` | VEN-15 | Proposta da VEN-0177 aberta pelo link | ator Sistema, IP truncado (fase 1c) |
| `meta_venda.definir`, `meta_venda.tirar` | VEN-09 | texto genérico | o valor de antes e o de depois (fase 1c) |
| `venda.criar_da_quitacao` | VEN-11 | Criou a venda VEN-0001 da quitação | Quitação da LOC-2856 |
| `venda.registrar_transferencia` | VEN-11 | Registrou a transferência no Detran da VEN-0001 | Feita em 13/11/2026 |

`interessado_nome` e `interessado_celular` vão mascarados (`CAMPOS_AUDITORIA`).

Testes: `tests/aceitacao/test_t502_fluxo_de_venda.py`, `tests/aceitacao/test_t502b_assinatura_e_vendida.py`, `tests/aceitacao/test_t502_fase_1c.py`, `tests/aceitacao/test_t502c_resumo_com_venda_concluida.py`, `apps/vendas/tests/test_calculo.py` e `tests/aceitacao/test_t420_venda_da_quitacao.py`.

## Interface interna

| Item | Uso |
| --- | --- |
| `vendas.eventos.locacao_quitada` | assinante de `locacoes.locacao_quitada`: `criar_venda_da_quitacao`. |
| `vendas.eventos.decisao_do_pedido` | assinante de `aprovacoes.pedido_decidido` (`APR-01`, origem `venda`): `aplicar_decisao_desconto`. |
| `vendas.eventos.contrato_assinado` | assinante de `contratos.contrato_assinado` (origem `venda`, `tipo = contrato`): `registrar_contrato_assinado` e `concluir_se_pronto`. |
| `vendas.eventos.entrada_paga` | assinante de `financeiro.parcela_paga` (origem `venda`, `tipo = entrada`): `registrar_entrada_paga` e `concluir_se_pronto`. |
| `vendas.contrato` | os valores dos marcadores da venda; registra o montador em `contratos.origens` no `ready()` (a prévia do modelo com `venda_id`). |
| `vendas.services.trava_do_estoque(veiculo)` | registrada em `veiculos.services.registrar_trava_do_estoque` no `ready()` (`VEN-10`). |
| `vendas.calculo` | módulo puro: `calcular(Entrada)`, `vencimentos(dia, n)`, `LIMITE_DESCONTO_PCT`. |
| `vendas.services.criar_venda_da_quitacao(...)` | idempotente pela `locacao` única. |
| `vendas.services.registrar_transferencia(venda, feita_em, usuario)` | a rota da locação. |
| `vendas.selectors.venda_da_locacao(locacao_id)` | bloco `compra.venda` do detalhe da locação (ADR 0015). |
| `vendas.selectors.transferencias_pendentes(filiais)` | painel (`relatorios`). |
| `vendas.selectors.vendas_do_veiculo(veiculo_id)` | histórico do veículo (ADR 0015); o interessado sem cadastro não entra. |
| `vendas.selectors.vendidas_entre(filiais, inicio, fim, vendedor_id=None)` | `VEN-12`: número e soma das vendas de balcão concluídas; lida pelo ticket médio do início (`relatorios`) e pelo resumo. |
| `vendas.resumo` | fase 1c: `resumo(usuario, filiais, mes, onde)`, `vendidas_do_mes`, `funil`, `conversao`, `em_negociacao`, `meta`, `para_retornar`, `ticket`; lido pelo início do vendedor e pelo contador `propostas` (`relatorios`). |
| `vendas.envio` | fase 1c: o PDF (`pdf_da_proposta`, `gravar_pdf`), o e-mail depois do commit (`agendar_envio`, tarefa `vendas_enviar_proposta`), o texto do envio e o link público (`gerar_link`, `consultar`). |
| `vendas.metas` | fase 1c: `definir_metas(filial, mes, pedidas, por)`, `quadro(filial, mes)`, `soma(filiais, mes, vendedor_id)`. |

`financeiro` ganha `lancar_comissao(..., base_centavos=, pct=)`, `recalcular_comissao(origem, base_centavos=, valor_centavos=)` (só a `pendente`) e o tipo de conta `entrada`. `empresas.ConfiguracaoEmpresa` ganha `comissao_venda_pct` (3,00) e `juros_venda_mes_pct` (0,00).

`contratos` (fase 1b): a finalidade `venda` passa a "Compra e venda" (migration `contratos` 0005, só o rótulo); o modelo pronto `compra_venda` (rascunho do backend, para o dono revisar com o advogado); os marcadores `venda.codigo`, `venda.preco_tabela`, `venda.desconto`, `venda.preco_final`, `venda.forma`, `venda.entrada`, `venda.parcelas`, `venda.juros_mes` e `venda.primeiro_vencimento`, só na finalidade `venda`; o `IMP-04` com o texto da venda (`sem_modelo_publicado(finalidade)`); `cancelar_assinado(contrato, motivo)`, só com `origem_tipo = venda` (o `cancelar` comum recusa o assinado com 409 `contrato_assinado`); e a prévia do modelo aceita `venda_id`.

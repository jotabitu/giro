# Locações

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-038) · **App:** `locacoes` (schema da empresa) · **Regras:** LOC-01 a LOC-15, CLI-02, CLI-03, CLI-05, IMP-04, APR-01, APR-02, FIL-03, FIL-05, FIN-09 · **ADRs:** 0005, 0011, 0015 · **Telas:** Locacoes, Locacao, Locacao-Detalhe

Convenções gerais em `docs/api/README.md`. Modelo: itens 12 e 13 (`PlanoEspecial`, `Locacao`, `TrechoLocacao`, `ExtraLocacao`) em `docs/decisoes/modelo-de-dados.md`. Vistoria, devolução e acerto estão em `vistorias.md`; modelo de contrato, PDF e assinatura, em `contratos.md`; receber parcela no caixa ou por Pix, em `financeiro.md` (T-017).

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver lista e detalhe (filiais da pessoa) | sim | sim | sim | só agenda e vistoria, sem valores | sim |
| Criar, editar rascunho, confirmar, renovar, trocar veículo | sim | sim | sim | — | — |
| Desconto até o limite (5%, `LOC-03`) | sim | sim | sim | — | — |
| Desconto acima do limite | sim | sim (direto) e aprova os pedidos | pede (`APR-01`) | — | — |
| Cancelar | sim | sim (direto) | pede (`APR-02`) | — | — |
| Planos especiais | sim | — | — | — | — |

- Permissão extra `aprovar_desconto` dá ao vendedor o direito de aprovar pedidos de outros (`USR-03`); quem pediu nunca aprova o próprio (`APR-09`).
- Gerente cancela e dá desconto acima do limite direto, como no desbloqueio de cliente (decidido em 07 out 2026, T-041). Só o vendedor pede.
- O vistoriador recebe a representação sem nenhum campo `_centavos` (`Vistoriador`: "Valores e dados de pagamento ficam ocultos").

## Ciclo de vida

```
rascunho ──confirmar──► aguardando_retirada ──(vistoria de saída + contrato assinado + 1º pagamento)──► ativa
   │ 24 h sem uso                │                                                                     │
   ▼                             ├──cancelar (sem multa)──► cancelada                                    ├──AUT-02──► devolucao_atrasada
cancelada                        │                                                                     │                   │
                                 │                                          encerramento antecipado ──┴─► (devolução) ──► cancelada
                                                                                       devolução ─────────────────────────► encerrada
```

- `ativa` acontece sozinha quando as 3 condições estão cumpridas, em qualquer ordem: `vistoria_saida_ok_em`, `contrato_assinado_em`, `primeiro_pagamento_em` (1ª parcela **e** caução pagas). O veículo vira `alugado` na mesma transação.
- `devolucao_atrasada`: a tarefa `aut_02_marcar_devolucao_atrasada` (de hora em hora) aplica `LOC-10` e `LOC-11`: passou do fim previsto + tolerância, a locação vira `devolucao_atrasada` no dia seguinte. Feriado da filial conta como fechado (`FIL-03`).
- Sinais calculados (não são status): `pagamento_atrasado`, `devolve_hoje`, `cancelamento_pendente`.

## Representação

### Linha da lista

```json
{
  "id": 2836, "codigo": "LOC-2836", "status": "ativa",
  "cliente": { "id": 1201, "nome": "Juliana Rocha" },
  "veiculo": { "id": 412, "modelo": "Yamaha Factor 150", "placa": "PNB7C04" },
  "periodicidade": "semanal", "plano_especial": null,
  "inicio": "2026-09-30T12:10:00Z", "fim_previsto": "2026-10-07T21:00:00Z",
  "sinais": { "pagamento_atrasado": false, "devolve_hoje": true, "cancelamento_pendente": false },
  "situacao": { "codigo": "devolve_hoje", "rotulo": "Devolve hoje", "tom": "info" },
  "pagamento": { "rotulo": "Pago", "tom": "sucesso", "em_aberto_centavos": 0 },
  "acao_principal": { "codigo": "receber_devolucao", "rotulo": "Receber devolução" }
}
```

`situacao` (a primeira que valer): `devolucao_atrasada` ("Devolução atrasada 25 dias"), `cancelamento_pendente` ("Pedido de cancelamento"), `pagamento_atrasado` ("Parcela 2 atrasada"), `aguardando_assinatura` / `aguardando_vistoria` / `aguardando_pagamento` (o que falta em `aguardando_retirada`, nessa ordem), `devolve_hoje`, `ativa`, `encerrada`, `cancelada`.
`pagamento.rotulo`: "R$ 1.347,00 em aberto", "Pago", "Pix automático", "R$ 329,00 pago" (antes da retirada), "Multa R$ 84,80" (com cancelamento pendente), forma de pagamento quando em dia.
`acao_principal`: `cobrar` (há valor em aberto), `receber_devolucao` (`devolve_hoje` ou `devolucao_atrasada`), `abrir`.

### Detalhe

A linha mais:

```json
{
  "filial": { "id": 1, "nome": "Filial Centro" },
  "vendedor": { "id": 3, "nome": "Bruna Alves" },
  "precos": { "valor_periodo_centavos": 32900, "diaria_centavos": 5490, "caucao_centavos": 30000,
              "desconto_pct": "0.00", "assinado_em_preco_de": "2026-09-30" },
  "extras": [ { "id": 1, "nome": "Capacete extra", "quantidade": 1, "valor_centavos": 0 } ],
  "km_saida": 18402, "km_livre": true,
  "forma_pagamento": "pix", "parcelamento_mensal": null,
  "condicoes": { "vistoria_saida_ok_em": "...", "contrato_assinado_em": "...", "primeiro_pagamento_em": "..." },
  "parcelas": [
    { "id": 9001, "tipo": "parcela", "numero": 1, "vencimento": "2026-09-30", "valor_centavos": 32900, "status": "paga", "forma": "pix", "pago_em": "..." },
    { "id": 9002, "tipo": "parcela", "numero": 2, "vencimento": "2026-10-07", "valor_centavos": 32900, "status": "paga", "forma": "pix", "pago_em": "..." },
    { "id": 9003, "tipo": "caucao", "numero": null, "vencimento": "2026-09-30", "valor_centavos": 30000, "status": "paga", "forma": "pix", "pago_em": "...", "observacao": "Devolver na entrega" }
  ],
  "total_pago_centavos": 95800,
  "contrato": { "id": 77, "status": "assinado", "modelo": "Locação semanal", "versao": 3, "assinado_em": "...", "pdf_disponivel": true },
  "devolucao": { "prevista_para": "2026-10-07T21:00:00Z", "faltam_minutos": 360,
                 "aviso_atraso": "Se atrasar, cobra R$ 54,90 por dia a mais (diária)", "devolucao_id": null },
  "trechos": [ { "veiculo": "PNB7C04", "inicio": "...", "fim": null } ],
  "cancelamento": null,
  "acoes": { "renovar": true, "registrar_devolucao": true, "trocar_veiculo": true, "cancelar": "direto",
             "imprimir_contrato": true, "reenviar_contrato": true, "continuar_vistoria": false, "receber": false }
}
```

- `total_pago_centavos` inclui a caução paga, como na tela. Caso do seed (`LOC-06`, `LOC-05`): LOC-2836 = 32900 + 32900 + 30000 = **95800**.
- `parcelas` vêm de `financeiro.selectors` (`financeiro` está acima de `locacoes`, ADR 0011). Status como em `FIN-01` (`vence_hoje` e `atrasada` calculados).
- `acoes.cancelar`: `direto`, `pedir` ou `false`, conforme o perfil.
- `cancelamento`: quando há pedido ou encerramento antecipado aprovado: `{ "status": "pendente" | "aprovado", "pedido_aprovacao_id", "antes_da_retirada": false, "data": "2026-10-07", "multa_centavos": 8480, "devolver_centavos": 28620, "motivo" }`. Depois da retirada, `multa_centavos` e `devolver_centavos` são a estimativa para `data`; o valor final sai no acerto da devolução (T-116).

### GET /api/locacoes/{id}/historico/
Linha do tempo de `Locacao-Detalhe`: `{ "resultados": [ { "em": "...", "rotulo": "Vistoria de saída · 12 fotos", "detalhe": "João Silva · 18.402 km · tanque cheio", "tipo": "vistoria" } ] }`. Montada a partir dos eventos de auditoria da locação (criação, contrato, mudanças de status), dos pagamentos (`financeiro.selectors`) e das vistorias (anotação de `vistorias`, ADR 0015). O vistoriador não vê os itens de pagamento.

---

## Lista

### GET /api/locacoes/
Perfis: todos menos vistoriador (que usa a agenda, `vistorias.md`). Escopo de filial pelo `X-Filial`.
Query: `?aba=abertas|precisam_acao|devolvem_hoje|encerradas|canceladas` (padrão `abertas`: `aguardando_retirada`, `ativa`, `devolucao_atrasada`), `?periodicidade=`, `?plano_especial=`, `?veiculo=<id>`, `?cliente=<id>`, `?busca=` (código, cliente, placa), `?ordem=fim_previsto|-inicio`.
`precisam_acao` = devolução atrasada, pagamento atrasado, aguardando assinatura ou cancelamento pendente.
200:
```json
{
  "indicadores": { "ativas": 42, "frota_alugada_pct": "71.00", "devolvem_hoje": 4, "devolvem_hoje_ate_12h": 2,
                   "devolucao_atrasada": 1, "devolucao_atrasada_destaque": "Rafael · 25 dias",
                   "pagamentos_atrasados": 2, "pagamentos_atrasados_centavos": 164640 },
  "contagens": { "abertas": 42, "precisam_acao": 4, "devolvem_hoje": 4, "encerradas": 310, "canceladas": 12 },
  "resultados": [ { ...linha... } ],
  "proximo": "...", "anterior": null
}
```
`?veiculo=` e `?cliente=` atendem a ficha do veículo e do cliente (histórico de locações).

---

## Nova locação (tela `Locacao`)

### POST /api/locacoes/simular/
Perfis: quem cria. Não grava nada (ADR 0005). Chamado a cada mudança do formulário.
Corpo:
```json
{ "cliente_id": 1310, "veiculo_id": 501, "periodicidade": "semanal", "plano_especial_id": null,
  "inicio": "2026-10-07T12:30:00Z", "periodos": 1, "fim_previsto": null,
  "extras": [ { "extra_id": 1, "quantidade": 1 } ], "desconto_pct": "0.00",
  "forma_pagamento": "pix_automatico", "parcelamento_mensal": null }
```
`periodos` (quantas diárias, semanas ou meses) **ou** `fim_previsto`; a API devolve os dois.
200:
```json
{
  "fim_previsto": "2026-10-14T12:30:00Z",
  "linhas": [
    { "rotulo": "1 semana × R$ 329,00", "valor_centavos": 32900 },
    { "rotulo": "Adicionais", "valor_centavos": 0 },
    { "rotulo": "Desconto", "valor_centavos": 0 },
    { "rotulo": "Caução (devolvida no fim)", "valor_centavos": 30000 }
  ],
  "valor_periodo_centavos": 32900,
  "proximos_periodos_centavos": 32900,
  "hoje_na_retirada_centavos": 62900,
  "texto_retirada": "Hoje: primeira semana mais caução.",
  "parcelas_previstas": [ { "numero": 1, "vencimento": "2026-10-07", "valor_centavos": 32900 } ],
  "caucao_centavos": 30000,
  "precisa_aprovacao_desconto": false,
  "impedimentos": [],
  "avisos": []
}
```
- `LOC-01`: preço da categoria do veículo vigente na data (`LOC-15`); plano especial substitui ou desconta (`Entregador` 27900/semana; `Mensal fidelidade` −10% a partir do 3º mês seguido).
- `LOC-14`: mensal é mês fechado, nunca diária × 30; período menor que um mês não aceita `mensal` (400 `validacao`). Com `parcelamento_mensal = "quatro_semanais"`, o mês é dividido em 4 parcelas pela `dividir_em_parcelas` (diferença na última).
- `LOC-02`: extras somam por período, pelo valor do cadastro.
- `LOC-04`: caução da categoria, cobrada uma vez na retirada.
- `LOC-05`: diária = tudo na retirada; semanal = 1ª na retirada e depois a cada 7 dias; mensal = 1ª na retirada e depois a cada mês.
- `impedimentos`: `[{ "codigo", "mensagem" }]` de `clientes.selectors.impedimentos_para_nova_locacao` (`CLI-05` bloqueado, `cliente_inativo`) e do veículo (`LOC-03` não está `disponivel` nem `reservado`; `CLI-02` CNH sem a categoria). Com impedimento, `confirmar` recusa.
- `avisos`: o que não impede criar, mas impede a retirada: `CLI-03` (cadastro incompleto), CNH vencida há mais de 30 dias (`CLI-02`), `IMP-04` (sem modelo de contrato publicado, com link para `Contratos-Modelos`).
- Caso do seed: Lucas, CG 160 Fan, semanal Street → `valor_periodo_centavos` 32900, caução 30000, `hoje_na_retirada_centavos` **62900**.

### POST /api/locacoes/
Corpo: o mesmo da simulação. 201: detalhe, com `status = "rascunho"` e `codigo` já reservado (`LOC-2856`).
O rascunho guarda o formulário; some com 24 h sem uso (vai para `cancelada`, sem evento de negócio além do de cancelamento).

### PATCH /api/locacoes/{id}/
Só em `rascunho`. Mesmo corpo. 200: detalhe. 409 `transicao_locacao` fora de `rascunho`.

### POST /api/locacoes/{id}/confirmar/
Botões "Continuar para vistoria" e "Salvar como reserva". Corpo: `{ "primeiro_vencimento": "2026-10-07" }` (opcional; padrão = data do início).
200: detalhe com `status = "aguardando_retirada"`. Na mesma transação:
- Congela preços (`valor_periodo_centavos`, `diaria_centavos`, `caucao_centavos`, extras) pela data de hoje (`LOC-15`).
- Cria as contas a receber em `financeiro`: as parcelas até o `fim_previsto` e a caução (`tipo = caucao`), todas com origem nesta locação.
- Se o `inicio` é futuro (data posterior a hoje na filial), o veículo vai para `reservado`; senão fica `disponivel` até a ativação.
- Desconto acima do limite: cria o pedido `APR-01` e devolve `"desconto": { "status": "pendente", "pedido_aprovacao_id": 88 }`. As parcelas nascem com o preço sem desconto e o contrato não é gerado até a decisão; aprovado, as parcelas abertas são refeitas com o desconto; recusado, o desconto volta a 0 e o vendedor é avisado com o motivo.
- Comissão de locação nova (`FIN-09`, R$ 16,00) é lançada como `pendente` para o vendedor, vira `confirmada` na ativação, `paga` no dia 5 do mês seguinte (`FIN-09`) e `estornada` só se a locação for cancelada antes da retirada; o encerramento antecipado não estorna.
Erros:
409 `{ "codigo": "LOC-03", "mensagem": "Veículo indisponível no período" }` (inclusive pela restrição de uma locação aberta por veículo).
422 `CLI-05`, `cliente_inativo`, `CLI-02` (impedimentos da simulação).
422 `{ "codigo": "IMP-04", "mensagem": "Publique um modelo de contrato antes de concluir a locação", "detalhes": { "link": "/admin/contratos" } }`.
422 `{ "codigo": "FIL-05", "mensagem": "O veículo é de outra filial. Transfira antes de alugar." }` quando a filial do veículo difere da filial da locação.
Regras: LOC-01 a LOC-05, LOC-14, LOC-15, IMP-04, APR-01, FIL-05.

### Depois de confirmar

- **Vistoria de saída:** `POST /api/locacoes/{id}/vistorias/` (ver `vistorias.md`).
- **Contrato:** `POST /api/locacoes/{id}/contrato/` gera o PDF do modelo publicado e envia o link de assinatura por WhatsApp (ver `contratos.md`). 202 `{ "contrato_id", "status": "gerado" }`; o envio e o PDF saem em segundo plano.
- **1º pagamento:** pelo caixa ou Pix, nas contas a receber da locação (`financeiro.md`). O assinante de `financeiro.parcela_paga` grava `primeiro_pagamento_em` quando a 1ª parcela e a caução estão pagas.
- Cada uma das três chama `locacoes.services.verificar_ativacao`, que leva a `ativa` quando as três estão cumpridas.

### GET /api/locacoes/{id}/contrato/pdf/
Perfis: quem vê o detalhe, menos vistoriador. 200: `{ "url": "...", "url_expira_em": "..." }` (URL assinada de 15 min, `AUD-05`). Botão "Imprimir".

### POST /api/locacoes/{id}/contrato/reenviar/
Gera novo link de assinatura (o anterior deixa de valer, `contratos.md`) e reenvia por WhatsApp. Só com contrato não assinado; depois de assinado, reenvia o PDF assinado.

---

## Durante a locação

### POST /api/locacoes/{id}/renovar/simular/ · POST /api/locacoes/{id}/renovar/
Perfis: quem cria. Só em `ativa` ou `devolucao_atrasada`. Corpo: `{ "periodos": 1 }` ou `{ "fim_previsto": "..." }`.
Simular devolve as novas parcelas; renovar (`LOC-08`):
- Estende o `fim_previsto` e cria as novas parcelas na mesma locação (não cria outro `LOC-`).
- Usa o preço vigente hoje (`LOC-15`: renovação usa o preço novo) e atualiza `valor_periodo_centavos` dali em diante.
- Gera um aditivo pelo app `contratos` (`tipo = aditivo`) e o envia. A renovação vale na hora; se o aditivo não for assinado em 7 dias, os gerentes da filial recebem uma tarefa (`LOC-08`).
- Não gera comissão (`FIN-09`).
- `devolucao_atrasada` renovada volta a `ativa` se o novo fim for futuro; o atraso já corrido continua cobrado na devolução.
- Dentro do prazo (fim previsto mais a tolerância, `LOC-10`, `LOC-11`), o período novo começa no fim previsto antigo. Depois do prazo, mesmo com a locação ainda `ativa`, começa na hora da renovação, e o atraso até ali fica guardado (`atraso_anterior_*`) e é cobrado no acerto (T-111, CA-015-26: fim 07 out 10:00, renovada em 09 out 10:00 → 10980 de atraso, parcela de 32900 vencendo em 09 out, fim em 16 out 10:00).
- Período e extras por período pelo preço de hoje (os extras pelo valor atual do cadastro, que passa a valer na locação); o mesmo `desconto_pct`, sem novo `APR-01`; plano de preço fixo pelo valor de hoje, plano de desconto contando os períodos desde o começo da locação; plano desativado → tabela (CA-015-27).
200: detalhe.

### POST /api/locacoes/{id}/trocar-veiculo/
Perfis: quem cria. Só em `ativa`. Corpo: `{ veiculo_novo_id, motivo }`.
202: `{ "troca": { "id", "status": "pendente", "devolucao_vistoria_id", "saida_vistoria_id" } }`. Abre as duas vistorias (devolução do atual e saída do novo, `vistorias.md`) e reserva o novo veículo.
Quando as duas são concluídas: o trecho atual fecha (`TrechoLocacao.fim`), o novo começa, o veículo antigo segue a regra da devolução (`disponivel` ou `em_manutencao`, `DEV-04`), o novo vira `alugado`, e o valor passa a ser o da nova categoria a partir da troca (`LOC-09`): as parcelas abertas com vencimento posterior são refeitas.
422 `LOC-03` (veículo novo indisponível), `FIL-05` (de outra filial), `CLI-02` (CNH sem a categoria).
Caução e cobranças na troca (`LOC-09`):
- Caução da nova categoria **maior**: a diferença vira conta a receber (`tipo = caucao`) na hora, e o veículo novo só sai depois de paga.
- Caução **menor** e cobranças da vistoria do veículo antigo não geram conta na troca: vão para o acerto final da locação, descontadas da caução total paga (um acerto só por locação, `vistorias.md`).

### Cancelamento e encerramento antecipado (LOC-12, LOC-13, APR-02)

**POST /api/locacoes/{id}/cancelamento/simular/** · corpo `{ "data": "2026-10-07" }` (padrão hoje).
200:
```json
{ "antes_da_retirada": false, "periodo_atual": { "inicio": "2026-09-15", "fim": "2026-10-15", "dias": 30 },
  "dias_restantes": 8, "valor_restante_centavos": 42400, "multa_centavos": 8480,
  "credito_semanas": { "semanas": 1, "valor_centavos": 37100 },
  "credito_dias": { "dias": 0, "valor_centavos": 0 }, "parcelas_canceladas_centavos": 0,
  "devolver_centavos": 28620, "cobrar_centavos": 0, "avisos": [] }
```
- Antes da retirada: sem multa; devolve tudo o que foi pago (parcelas e caução).
- Depois da retirada: multa de 20% sobre o valor dos dias restantes do período em curso (preço do período ÷ dias do período × dias restantes), mínimo de 1 diária da categoria. Diária: sem multa, cobra só os dias usados.
- Mensal (`LOC-13`): devolve as semanas inteiras não usadas (7 × preço mensal ÷ 30 por semana), menos a multa; se a multa for maior, a diferença vira conta a receber (`cobrar_centavos`).
- Diária (`LOC-12`): os dias usados contam em blocos de 24 h desde o início, e fração conta como dia. A simulação só tem a data e conta a devolução na hora do início; `avisos` traz `[ { "codigo": "LOC-12", "mensagem": "O acerto final usa a hora da devolução." } ]`. Nos outros planos, `avisos` é `[]`. O acerto da devolução recalcula pela hora real (CA-015-28: Urbana de 05 a 10 out 10:00, devolvida em 07 out até 10:00 → 13470; a partir de 10:01 → 8980).
- Mensal em 4 semanais (`LOC-13`): `credito_semanas.valor_centavos` é o bruto; `parcelas_canceladas_centavos` são as parcelas em aberto do mês em curso que vencem depois do dia e que o encerramento cancela (0 fora do mensal em 4 semanais). `devolver_centavos`/`cobrar_centavos` já são líquidos: crédito − canceladas − multa, o mesmo saldo do mês à vista (CA-015-29: encerrada em 25 set com 2 pagas → 74200 − 79500 − 21200 → cobrar **26500**).
- Caso do seed: Patrícia, LOC-2812, NMax mensal 159000, pedido em 07 out, fim 15 out → restante 42400, multa **8480**, crédito 37100, devolve **28620**.

**POST /api/locacoes/{id}/cancelar/** · corpo `{ motivo, data? }`.
- Administrador, gerente ou quem tem `cancelar_contrato`: 200, efeito na hora.
- Vendedor: 202 `{ "pedido_aprovacao": { "id", "tipo": "APR-02", "status": "pendente" } }`; o sinal `cancelamento_pendente` acende.
Efeito ao valer:
- Antes da retirada (`rascunho`, `aguardando_retirada`): `cancelada` na hora; contas abertas canceladas, pagas estornadas (devolução ao cliente pelo `financeiro`), veículo `reservado` volta a `disponivel`, comissão `estornada`.
- Depois da retirada: a locação fica marcada com o encerramento antecipado aprovado (`cancelamento.status = "aprovado"`) e segue para a devolução (`vistorias.md`). A aprovação não cancela parcelas: até a devolução, elas vencem, atrasam e podem ser pagas como qualquer outra. `cancelamento.multa_centavos` e `devolver_centavos` são a estimativa para `cancelamento.data`. O acerto da devolução recalcula a multa e o crédito pelo dia da devolução, com o mesmo cálculo de `cancelamento/simular`, e o encerramento da devolução cancela as parcelas que vencem depois desse dia (`DEV-07`, T-116; CA-016-25: Carlos aprovado para 07 out com estimativa de 5988 e devolvido em 16 out → multa 5490, cobrar 67377). Ao encerrar a devolução, o status final é `cancelada`. Se a devolução é no dia do fim previsto ou depois, ela é comum: sem multa nem crédito, com o atraso da `LOC-10`, `forma_devolucao` escolhida no acerto e a locação `encerrada`; o pedido aprovado fica registrado, sem efeito (`DEV-07`, T-118; Carlos devolvido em 28 out → cobrar 92855).
Recusado pelo gerente: o sinal apaga e o vendedor é avisado com o motivo.
409 `transicao_locacao` em `encerrada` ou `cancelada`.

---

## Planos especiais (tela Precos)

`GET /api/planos-especiais/` (todos) → `{ "resultados": [ { "id", "nome": "Entregador", "periodicidade": "semanal", "regra": "preco_fixo", "preco_centavos": 27900, "desconto_pct": null, "a_partir_do_periodo": null, "categorias": [], "condicoes": "Semanal com km livre e troca de óleo inclusa", "locacoes_ativas": 18, "ativo": true } ] }`.
`POST`, `PATCH /api/planos-especiais/{id}/`, `POST .../desativar/` · administrador. Mudança vale para locações novas (`LOC-15`); quem já assinou mantém.

---

## Interface interna

| Item | Uso |
| --- | --- |
| `locacoes.services.registrar_vistoria_saida(locacao, vistoria)` | chamado por `vistorias` ao concluir a saída; grava `vistoria_saida_ok_em`, `km_saida` e verifica a ativação. |
| `locacoes.services.encerrar(locacao, devolucao)` | chamado por `vistorias` ao encerrar a devolução (`DEV-06`): `encerrada` (ou `cancelada` no encerramento antecipado), `devolvida_em`, comissão e eventos. |
| `locacoes.selectors.calcular_atraso(locacao, momento) -> { dias, valor_centavos }` | `LOC-10`, `LOC-11`, `FIL-03`; usado no acerto. |
| `locacoes.selectors.calcular_encerramento_antecipado(locacao, data)` | `LOC-12`, `LOC-13`; o mesmo cálculo de `cancelamento/simular`. |
| assinantes | `financeiro.parcela_paga` (1º pagamento), `contratos.contrato_assinado`, `aprovacoes.pedido_decidido` (`APR-01`, `APR-02`). |
| evento publicado | `locacoes.locacao_encerrada` (preventivas, `MAN-03`). |
| anotações fornecidas (ADR 0015) | `locacao_atual` para `veiculos` e `clientes`; `locacoes_ativas` e contador de operação para `filiais`; filtro `com_locacao` e contador `locacao_aberta` (inativar, `cliente_com_pendencia`) para `clientes`. |
| tarefas | `aut_01_lembrete_de_devolucao` (08:00), `aut_02_marcar_devolucao_atrasada` (de hora em hora), limpeza de rascunhos com 24 h. |

# Locações

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-038), troca de veículo em 10 out 2026 (T-122), `acoes.gerar_contrato` em 15 out 2026 (T-263), reserva na confirmação, nada vence antes da retirada e cancelamento automático em 03 nov 2026 (T-410), copiar link para assinar em 03 nov 2026 (T-411, `copiar-link.md`), locação com intenção de compra em 03 nov 2026 (T-420, ADR 0037) · **App:** `locacoes` (schema da empresa) · **Regras:** LOC-01 a LOC-16, VEN-11, CLI-02, CLI-03, CLI-05, IMP-04, APR-01, APR-02, FIL-03, FIL-05, FIN-03, FIN-09, AUT-17 · **ADRs:** 0005, 0011, 0015, 0035, 0037 · **Telas:** Locacoes, Locacao, Locacao-Detalhe · **Critérios:** `docs/qa/criterios/T-410.md` (CA-410-01 a 23), `docs/qa/criterios/T-420.md` (CA-420-01 a 17)

Convenções gerais em `docs/api/README.md`. Modelo: itens 12 e 13 (`PlanoEspecial`, `Locacao`, `TrechoLocacao`, `ExtraLocacao`) em `docs/decisoes/modelo-de-dados.md`. Vistoria, devolução e acerto estão em `vistorias.md`; modelo de contrato, PDF e assinatura, em `contratos.md`; receber parcela no caixa ou por Pix, em `financeiro.md` (T-017).

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver lista e detalhe (filiais da pessoa) | sim | sim | sim | só agenda e vistoria, sem valores | sim |
| Criar, editar rascunho, confirmar, renovar, trocar veículo, cancelar a troca pendente | sim | sim | sim | — | — |
| Desconto até o limite (5%, `LOC-03`) | sim | sim | sim | — | — |
| Desconto acima do limite | sim | sim (direto) e aprova os pedidos | pede (`APR-01`) | — | — |
| Cancelar | sim | sim (direto) | pede (`APR-02`) | — | — |
| Planos especiais | sim | — | — | — | — |
| Planos de compra (`LOC-16`) | sim | — | — | — | — |
| Encerrar por atraso a locação com intenção de compra (`LOC-16`) | sim | sim | — | — | — |

- Permissão extra `aprovar_desconto` dá ao vendedor o direito de aprovar pedidos de outros (`USR-03`); quem pediu não aprova o próprio, e a permissão extra não abre a exceção, que é só do administrador (`APR-09`, T-249, `aprovacoes.md`).
- Gerente cancela e dá desconto acima do limite direto, como no desbloqueio de cliente (decidido em 07 out 2026, T-041). Só o vendedor pede.
- O vistoriador recebe a representação sem nenhum campo `_centavos` (`Vistoriador`: "Valores e dados de pagamento ficam ocultos").

## Ciclo de vida

```
rascunho ──confirmar──► aguardando_retirada ──(vistoria de saída + contrato assinado + 1º pagamento)──► ativa
   │ 24 h sem uso                │                                                                     │
   ▼                             ├──cancelar (sem multa) ou AUT-17──► cancelada                          ├──AUT-02──► devolucao_atrasada
cancelada                        │                                                                     │                   │
                                 │                                          encerramento antecipado ──┴─► (devolução) ──► cancelada
                                                                                       devolução ─────────────────────────► encerrada
```

- `aguardando_retirada` (T-410, ADR 0035): o veículo fica `reservado` desde a confirmação, com qualquer data de início, e as contas da locação esperam a retirada (`aguarda_retirada`), sem `vence_hoje` nem `atrasada` (`LOC-05`). A locação não retirada até o `ultimo_dia_retirada` (data de início + 3 dias corridos, `America/Sao_Paulo`) é cancelada pela `AUT-17` no começo do dia seguinte ("Cancelamento automático", abaixo).
- `ativa` acontece sozinha quando as 3 condições estão cumpridas, em qualquer ordem: `vistoria_saida_ok_em`, `contrato_assinado_em`, `primeiro_pagamento_em` (1ª parcela **e** caução pagas). O veículo vira `alugado` na mesma transação, e as contas da locação são liberadas com o dia da retirada (`financeiro.services.liberar_contas_da_retirada`, `FIN-03`). O vencimento gravado e o `fim_previsto` não mudam (`LOC-05`, padrão A do produto).
- `devolucao_atrasada`: a tarefa `aut_02_marcar_devolucao_atrasada` (de hora em hora) aplica `LOC-10` e `LOC-11`: passou do fim previsto + tolerância, a locação vira `devolucao_atrasada` no dia seguinte. Feriado da filial conta como fechado (`FIL-03`).
- Sinais calculados (não são status): `pagamento_atrasado`, `devolve_hoje`, `cancelamento_pendente`.

## Representação

### Linha da lista

```json
{
  "id": 2836, "codigo": "LOC-2836", "status": "ativa",
  "cliente": { "id": 1201, "nome": "Juliana Rocha" },
  "veiculo": { "id": 412, "modelo": "Yamaha Factor 150", "placa": "PNB7C04", "tipo": "moto" },
  "periodicidade": "semanal", "plano_especial": null,
  "inicio": "2026-09-30T12:10:00Z", "fim_previsto": "2026-10-07T21:00:00Z",
  "sinais": { "pagamento_atrasado": false, "devolve_hoje": true, "cancelamento_pendente": false },
  "situacao": { "codigo": "devolve_hoje", "rotulo": "Devolve hoje", "tom": "info" },
  "pagamento": { "rotulo": "Pago", "tom": "sucesso", "em_aberto_centavos": 0, "pago_centavos": 65800 },
  "acao_principal": { "codigo": "receber_devolucao", "rotulo": "Receber devolução" }
}
```

`veiculo.tipo` (`moto` ou `carro`, da categoria) e `pagamento.pago_centavos` (contas pagas da locação, **sem** caução, como o `total_pago_centavos` do cliente) entram na T-128 para a ficha do cliente (`GET /api/locacoes/?cliente=`) não precisar abrir o detalhe de cada locação. Na LOC-2836 do exemplo: duas parcelas de R$ 329,00 pagas = 65800; a caução de R$ 300,00 fica de fora.

`sinais.pagamento_atrasado` (`LOC-07`) usa a `financeiro.selectors.q_atrasada`: na locação `aguardando_retirada`, nunca acende (`LOC-05`, T-410), mesmo com o vencimento gravado já passado. O mesmo vale para `indicadores.pagamentos_atrasados*` e para a aba `precisam_acao`.
`situacao` (a primeira que valer): `devolucao_atrasada` ("Devolução atrasada 25 dias"), `cancelamento_pendente` ("Pedido de cancelamento"), `pagamento_atrasado` ("Parcela 2 atrasada"), `aguardando_assinatura` / `aguardando_vistoria` / `aguardando_pagamento` (o que falta em `aguardando_retirada`, nessa ordem), `devolve_hoje`, `ativa`, `encerrada`, `cancelada`.
`pagamento.rotulo`: "R$ 1.347,00 em aberto", "Pago", "Pix automático", "R$ 329,00 pago" (antes da retirada), "Multa R$ 84,80" (com cancelamento pendente), forma de pagamento quando em dia.
`acao_principal`: `cobrar` (há valor em aberto), `receber_devolucao` (`devolve_hoje` ou `devolucao_atrasada`), `abrir`.

### Detalhe

A linha mais:

```json
{
  "cliente": { "id": 1201, "nome": "Juliana Rocha", "celular": "85988771203", "cnh_categoria": "A",
               "ficha_liberada": true },
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
  "troca": null,
  "acoes": { "renovar": true, "registrar_devolucao": true, "trocar_veiculo": true, "cancelar_troca": false,
             "cancelar": "direto", "gerar_contrato": false, "imprimir_contrato": true, "reenviar_contrato": true,
             "copiar_link_contrato": false, "continuar_vistoria": false, "receber": false }
}
```

- `cliente` no detalhe traz, além de `id` e `nome` (os da linha da lista), o `celular` e a `cnh_categoria` (`null` se o cadastro não tem) e `ficha_liberada`: `true` se o perfil abre a ficha do cliente (`GET /api/clientes/{id}/`), `false` para o vistoriador, que recebe 403 lá (`USR-09`, T-207). A tela da locação usa isso no lugar de chamar a ficha do cliente.
- `total_pago_centavos` inclui a caução paga, como na tela. Caso do seed (`LOC-06`, `LOC-05`): LOC-2836 = 32900 + 32900 + 30000 = **95800**.
- `parcelas` vêm de `financeiro.selectors` (`financeiro` está acima de `locacoes`, ADR 0011). Status como em `FIN-01` (`vence_hoje` e `atrasada` calculados).
- `acoes.cancelar`: `direto`, `pedir` ou `false`, conforme o perfil. É `false` com uma troca de veículo pendente (`LOC-12`, T-122).
- `acoes.gerar_contrato` (T-263, passo 3 do fluxo da retirada): `true` quando `POST /api/locacoes/{id}/contrato/` passaria, pelas mesmas condições do serviço: perfil que cria locação (administrador, gerente, vendedor), locação `aguardando_retirada`, sem pedido de desconto pendente (`APR-01`), sem cancelamento em curso (`LOC-12`) e sem contrato vigente (o `contrato` do detalhe é `null` ou `cancelado`). Não olha o modelo publicado: sem ele, o botão aparece e o `POST` responde 422 `IMP-04` com o atalho para publicar (`IMP-04` manda mostrar o atalho). A tela mostra "Enviar contrato" só por ele; com contrato vigente, as ações são `reenviar_contrato` e `imprimir_contrato`. Na LOC-2836 (ativa, contrato assinado) é `false`.
- `acoes.trocar_veiculo`: quem cria, locação `ativa`, sem cancelamento em curso e sem troca pendente.
- `acoes.cancelar_troca`: quem cria, com uma troca pendente cuja saída do veículo novo não foi concluída (T-122). `acoes.renovar` continua `true` com a troca pendente (`LOC-08`).
- `troca`: a troca pendente, ou `null` (as concluídas aparecem em `trechos` e no histórico, as canceladas só no histórico):
  ```json
  { "id": 41, "status": "pendente", "motivo": "Cliente pediu scooter", "pedida_em": "2026-10-07T21:00:00Z",
    "veiculo_antigo": { "id": 12, "placa": "PNB7C04", "modelo": "Yamaha Factor 150" },
    "veiculo_novo": { "id": 31, "placa": "GEN0001", "modelo": "Yamaha NMax 160" },
    "devolucao_vistoria": { "id": 3101, "status": "concluida" },
    "saida_vistoria": { "id": 3102, "status": "rascunho" },
    "preco": { "valor_periodo_centavos": 44900, "diaria_centavos": 7990, "caucao_centavos": 50000, "preco_do_dia": "2026-10-07" },
    "caucao": { "conta_id": 9010, "valor_centavos": 20000, "status": "paga" } }
  ```
  `preco` é o guardado no pedido (`LOC-09`); `caucao` é a conta da diferença de caução, ou `null` sem diferença a cobrar. O vistoriador recebe a troca sem `preco` e sem `caucao`.
- `cancelamento`: quando há pedido ou encerramento antecipado aprovado: `{ "status": "pendente" | "aprovado", "pedido_aprovacao_id", "antes_da_retirada": false, "data": "2026-10-07", "multa_centavos": 8480, "devolver_centavos": 28620, "motivo" }`. Depois da retirada, `multa_centavos` e `devolver_centavos` são a estimativa para `data`; o valor final sai no acerto da devolução (T-116).
- `prazo_retirada` (T-410, `LOC-12`): só na locação `aguardando_retirada`; nos outros status, `null`.
  ```json
  "prazo_retirada": { "ultimo_dia": "2026-11-08", "cancela_em": "2026-11-09" }
  ```
  `ultimo_dia` = data local do `inicio` + 3 dias corridos (`locacoes.selectors.ultimo_dia_retirada`), feriado da filial contando; `cancela_em` = o dia seguinte, quando a `AUT-17` cancela às 00:10. Datas sem hora. A tela de referência não mostra o prazo; o campo existe para a tela que vier a mostrar e para o QA, e a tela não calcula a data por conta própria.
- `parcelas` da locação `aguardando_retirada`: status `aberta`, mesmo com o vencimento já passado (`LOC-05`), e `valor_hoje` sem multa nem juros (`FIN-03`, `financeiro.md`).
- `cancelamento` da locação cancelada pela `AUT-17`: `{ "status": "aprovado", "pedido_aprovacao_id": null, "antes_da_retirada": true, "automatico": true, "data": "2026-11-09", "multa_centavos": 0, "devolver_centavos": 62900, "motivo": "Não retirada em 3 dias da data de início" }`. `automatico` é `false` nos outros cancelamentos.

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
- `impedimentos`: `[{ "codigo", "mensagem" }]` de `clientes.selectors.impedimentos_para_nova_locacao` (`CLI-05` bloqueado, `cliente_inativo`), do veículo (`LOC-03` não está `disponivel`; `CLI-02` CNH sem a categoria) e do início (`inicio_vencido`, abaixo). Com impedimento, `confirmar` recusa.
  - **T-410:** o veículo `reservado` deixou de servir para a Nova locação. Todo `reservado` é de uma locação `aguardando_retirada` ou de uma troca pendente (`LOC-09`), e nenhum dos dois vai para outro cliente (CA-410-01, CA-410-05). Antes, o `reservado` passava na simulação e só a restrição de uma locação aberta por veículo recusava.
  - `{ "codigo": "inicio_vencido", "mensagem": "O início passou de 3 dias. Mude a data de início para confirmar." }` quando o `ultimo_dia_retirada` do `inicio` informado já passou (hoje > início + 3, `LOC-12`, padrão A do produto). Ex.: hoje 09 nov, início 05 nov. Com início 06 nov, passa. O rascunho pode ser criado e editado com esse início; só a confirmação recusa. A tela mostra o impedimento como os outros, sem fazer a conta.
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
- Cria as contas a receber em `financeiro`: as parcelas até o `fim_previsto` e a caução (`tipo = caucao`), todas com origem nesta locação e com `aguarda_retirada = true` (ADR 0035, `LOC-05`). Os vencimentos seguem o calendário a partir da data de início, como antes.
- **O veículo vai para `reservado`, com qualquer data de início** (T-410; tabela de transições do veículo): futuro, hoje ou passado. O serviço trava o veículo e exige `disponivel`; com outro status, 409 `LOC-03`. A transição é de `veiculos.services.transicionar`, com a origem na locação e o motivo "Reserva da LOC-2856" (evento de auditoria do veículo, CA-410-01). Antes, só o início futuro reservava, e o veículo da locação com início hoje ou passado ficava `disponivel` até a ativação.
- Confirmada no próprio `ultimo_dia_retirada` depois das 08:00, a locação manda na hora o aviso da `AUT-17` aos gerentes (depois do commit, mesma chave; CA-410-17).
- Desconto acima do limite: cria o pedido `APR-01` e devolve `"desconto": { "status": "pendente", "pedido_aprovacao_id": 88 }`. As parcelas nascem com o preço sem desconto e o contrato não é gerado até a decisão; aprovado, as parcelas abertas são refeitas com o desconto, ainda com `aguarda_retirada = true`; recusado, o desconto volta a 0 e o vendedor é avisado com o motivo. A reserva do veículo não espera a decisão.
- Comissão de locação nova (`FIN-09`, R$ 16,00) é lançada como `pendente` para o vendedor, vira `confirmada` na ativação, `paga` no dia 5 do mês seguinte (`FIN-09`) e `estornada` só se a locação for cancelada antes da retirada; o encerramento antecipado não estorna. Só é lançada se a empresa tem `vendas_comissoes` no momento da confirmação (`PLT-12`; no Essencial, nunca); a ativação, o pagamento e o estorno só mexem em comissão que existe, então a locação confirmada antes do upgrade nunca ganha comissão (ADR 0024, item 11, CA-ASS-53, `test_plt_12_comissao_so_depois_do_upgrade`).
Erros:
409 `{ "codigo": "inicio_vencido", "mensagem": "O início passou de 3 dias. Mude a data de início para confirmar.", "detalhes": { "inicio": "2026-11-05", "ultimo_dia_retirada": "2026-11-08" } }` (T-410, `LOC-12`, CA-410-18): o `ultimo_dia_retirada` já passou. Conferido logo depois do 409 `transicao_locacao` (fora de `rascunho`) e antes de tudo o mais: a locação continua `rascunho`, nenhuma conta nasce, o veículo não muda e nada é auditado. Datas em `detalhes` sem hora, no fuso da filial.
409 `{ "codigo": "LOC-03", "mensagem": "Veículo indisponível no período" }` (inclusive pela restrição de uma locação aberta por veículo, e o veículo `reservado` por outra locação ou troca).
422 `CLI-05`, `cliente_inativo`, `CLI-02` (impedimentos da simulação).
422 `{ "codigo": "IMP-04", "mensagem": "Publique um modelo de contrato antes de concluir a locação", "detalhes": { "link": "/admin/contratos" } }`.
422 `{ "codigo": "FIL-05", "mensagem": "O veículo é de outra filial. Transfira antes de alugar." }` quando a filial do veículo difere da filial da locação.
Regras: LOC-01 a LOC-05, LOC-12, LOC-14, LOC-15, IMP-04, APR-01, FIL-05, tabela de transições do veículo.

### Depois de confirmar

- **Vistoria de saída:** `POST /api/locacoes/{id}/vistorias/` (ver `vistorias.md`).
- **Contrato:** `POST /api/locacoes/{id}/contrato/` gera o PDF do modelo publicado e envia o link de assinatura por WhatsApp (ver `contratos.md`). 202 `{ "contrato_id", "status": "gerado" }`; o envio e o PDF saem em segundo plano.
- **1º pagamento:** pelo caixa ou Pix, nas contas a receber da locação (`financeiro.md`). O assinante de `financeiro.parcela_paga` grava `primeiro_pagamento_em` quando a 1ª parcela e a caução estão pagas. Pagas antes ou no dia da retirada, as duas nunca têm multa nem juros, mesmo com o vencimento gravado antes (`FIN-03`, CA-410-09: R$ 629,00 em 07 nov, com vencimento em 05 nov).
- Cada uma das três chama `locacoes.services.verificar_ativacao`, que leva a `ativa` quando as três estão cumpridas e, na mesma transação, libera as contas (`liberar_contas_da_retirada(origem, dia)`, com o dia local da ativação). Dali em diante, as contas seguem o calendário de sempre (CA-410-10: parcela 2 vence em 12 nov e atrasa em 13 nov).

### GET /api/locacoes/{id}/contrato/pdf/
Perfis: quem vê o detalhe, menos vistoriador. 200: `{ "url": "...", "url_expira_em": "..." }` (URL assinada de 15 min, `AUD-05`). Botão "Imprimir".

### POST /api/locacoes/{id}/contrato/reenviar/
Gera novo link de assinatura (o anterior deixa de valer, `contratos.md`) e reenvia por WhatsApp. Só com contrato não assinado; depois de assinado, reenvia o PDF assinado.

### POST /api/locacoes/{id}/contrato/link/ (copiar link para assinar, T-411)

Regras comuns das rotas de copiar link em `copiar-link.md`. Sem corpo. Gera um link novo de assinatura do contrato vigente e o devolve **uma vez**, para a tela copiar e a pessoa mandar por outro canal. Não envia nada.

200, com `Cache-Control: no-store`:
```json
{ "link": "https://motorapida.girolocadoras.com.br/assinar#<token>",
  "expira_em": "2026-11-10T14:00:00Z",
  "aviso": "O link anterior deixa de valer.",
  "contrato": { "id": 77, "status": "enviado", "modelo": "Locação semanal", "versao": 3, "assinado_em": null, "pdf_disponivel": true } }
```

- **O que faz** (`contratos.services.gerar_link(contrato, por)`, chamado por `locacoes.contrato.copiar_link(locacao, por)`): numa transação, com o contrato travado (`select_for_update`, o mesmo lock da tarefa `contratos_preparar_e_enviar`), confere o estado e chama `novo_token(contrato)`, que troca o hash e o `token_assinatura_expira_em` (7 dias a partir de agora). O link é `link_de_assinatura(host, token)`, o mesmo do WhatsApp. O token em claro só existe nesta resposta.
- **Não muda o status.** O contrato `gerado` com o PDF pronto continua `gerado` (nada foi enviado); `enviado` continua `enviado`, e `enviado_em` não muda. A assinatura pelo link copiado é a mesma de sempre (`POST /api/publico/assinaturas/assinar/`).
- **Invalida o anterior:** o link do WhatsApp, o do e-mail e um copiado antes deixam de valer. Reenviar depois invalida o copiado.
- **Registra de onde veio o link** (`LOC-15`, M-02 da revisão de segurança da T-411): quem copia tem o token na mão e poderia assinar pelo cliente. A rota não bloqueia isso (no balcão, o cliente assina no celular, na rede da loja), mas a prova da assinatura passa a dizer como o link chegou. `novo_token` grava no contrato `token_assinatura_canal` (`copiado`; a tarefa de envio grava `whatsapp_email`), `token_assinatura_gerado_por` (quem copiou) e `token_assinatura_gerado_ip` (o IP da cópia). Na assinatura, ver `contratos.md`.
- **A tarefa de envio não mata o link copiado** (B-02 da mesma revisão): `contratos_preparar_e_enviar` e `contratos_reenviar` travam o contrato e não geram token quando `token_assinatura_expira_em` existe e é mais novo que o momento em que a tarefa entrou na fila (um link foi copiado ou enviado depois). Nesse caso a tarefa termina sem enviar e sem erro. Teste: `test_s_15_reenvio_em_fila_nao_mata_link_copiado`.
- **Na tela**, junto do link: "Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link." (texto fixado pelo produto em 05 nov 2026, passo 3 do fluxo da locação nas regras).
- **Quando passa:**
  - sem contrato vigente: 409 `{ "codigo": "sem_contrato", "mensagem": "Esta locação ainda não tem contrato. Gere o contrato." }`;
  - `gerado` sem o PDF (a tarefa ainda não rodou): 409 `{ "codigo": "contrato_em_preparo", "mensagem": "O contrato ainda está sendo gerado. Tente de novo em alguns segundos." }`. Sem o PDF não há o que assinar, e o token gerado agora seria trocado pela tarefa logo depois;
  - `assinado`: 409 `{ "codigo": "contrato_assinado", "mensagem": "Este contrato já foi assinado. Para mandar o PDF assinado, use Reenviar." }`;
  - `cancelado`: 409 `contrato_cancelado`, como no reenviar;
  - titular anonimizado: 409 `titular_anonimizado` (`copiar-link.md`).
  O contrato vigente não assinado só existe antes da retirada, e o cancelamento da locação cancela o contrato (`LOC-12`); a rota não olha o status da locação.
- **Quem:** quem gera e reenvia o contrato (administrador, gerente, vendedor; `CRIAM`); financeiro e vistoriador, 403 `permissao`; token de suporte, 403 `PLT-07`, com qualquer permissão de acesso.
- **Limite:** 5 por hora por contrato e 20 por hora por pessoa (`comum.limites`, escopos `link_contrato_contrato` e `link_contrato_usuario`), conferido antes da transação; acima, 429 `muitas_requisicoes`.
- **Auditoria:** evento `contrato.copiar_link`, categoria `seguranca`, objeto o contrato, com `token_assinatura_expira_em` novo; sem o link nem o token (`CAMPOS_AUDITORIA` já omite `token_assinatura_hash`). Texto pronto no histórico da locação: "Copiou o link para assinar o contrato".
- **`acoes.copiar_link_contrato`** no detalhe da locação: `true` quando esta rota passaria pelo perfil e pelo estado: perfil que cria locação, sem token de suporte, contrato vigente `enviado`, ou `gerado` com `pdf_disponivel`, e titular não anonimizado. Não olha o limite por hora. Na LOC-2836 (assinado) é `false`; numa locação recém-confirmada com o contrato `enviado`, `true`.
- Testes com o código: `test_s_15_copiar_link_contrato_invalida_o_anterior` (o token do WhatsApp deixa de abrir; o copiado abre e assina), `test_s_15_copiar_link_contrato_estados` (sem contrato, em preparo, assinado, cancelado, anonimizado), `test_s_15_copiar_link_contrato_perfis_e_suporte`, `test_s_15_copiar_link_contrato_limite_por_hora`, `test_s_15_copiar_link_contrato_evento_sem_token` e `test_loc_15_assinatura_por_link_copiado_registra_canal`.
- **Ordem na view** (a mesma do `link-convite`, T-252): permissão e 403 `PLT-07` primeiro, depois o limite, depois o serviço. Um 403 não gasta o limite, e um 429 não gera link nem invalida o anterior.

---

## Durante a locação

### POST /api/locacoes/{id}/renovar/simular/ · POST /api/locacoes/{id}/renovar/
Perfis: quem cria. Só em `ativa` ou `devolucao_atrasada`. Corpo: `{ "periodos": 1 }` ou `{ "fim_previsto": "..." }`.
Simular devolve as novas parcelas; renovar (`LOC-08`):
- Estende o `fim_previsto` e cria as novas parcelas na mesma locação (não cria outro `LOC-`).
- Usa o preço vigente hoje (`LOC-15`: renovação usa o preço novo) e atualiza `valor_periodo_centavos` dali em diante.
- Gera um aditivo pelo app `contratos` (`tipo = aditivo`) e o envia. A renovação vale na hora; se o aditivo não for assinado em 7 dias, os gerentes da filial recebem uma tarefa (`LOC-08`).
- Não gera comissão (`FIN-09`).
- Permitida com uma troca de veículo pendente: as parcelas novas saem da categoria atual e as que vencem depois do dia da troca são refeitas na conclusão (`LOC-08`, `LOC-09`).
- `devolucao_atrasada` renovada volta a `ativa` se o novo fim for futuro; o atraso já corrido continua cobrado na devolução.
- Dentro do prazo (fim previsto mais a tolerância, `LOC-10`, `LOC-11`), o período novo começa no fim previsto antigo. Depois do prazo, mesmo com a locação ainda `ativa`, começa na hora da renovação, e o atraso até ali fica guardado (`atraso_anterior_*`) e é cobrado no acerto (T-111, CA-015-26: fim 07 out 10:00, renovada em 09 out 10:00 → 10980 de atraso, parcela de 32900 vencendo em 09 out, fim em 16 out 10:00).
- Período e extras por período pelo preço de hoje (os extras pelo valor atual do cadastro, que passa a valer na locação); o mesmo `desconto_pct`, sem novo `APR-01`; plano de preço fixo pelo valor de hoje, plano de desconto contando os períodos desde o começo da locação; plano desativado → tabela (CA-015-27).
200: detalhe.

### Troca de veículo (LOC-09)

As rotas da troca ficam em `apps/vistorias/api`, porque abrem e descartam vistorias (`vistorias` está abaixo de `locacoes`, ADR 0011); o caminho fica sob a locação. A troca (`TrocaVeiculo`), o preço, as parcelas e os veículos mudam por `locacoes.services`; as vistorias e o acerto, por `vistorias.services`. Uma troca `pendente` por locação. Estados: `pendente` → `concluida` | `cancelada`; as duas últimas não mudam mais.

#### POST /api/locacoes/{id}/trocar-veiculo/
Perfis: quem cria. Só em `ativa`. Corpo: `{ veiculo_novo_id, motivo }`.
202: `{ "troca": { "id", "status": "pendente", "devolucao_vistoria_id", "saida_vistoria_id" } }`. Na mesma transação:
- a troca nasce `pendente`, com o preço da nova categoria **no dia do pedido** guardado nela (`LOC-09`, `LOC-15`): período (sem descontos, como `Locacao.valor_periodo_centavos`; o plano especial de preço fixo continua se valer para a nova categoria), diária e caução, mais `preco_do_dia` (a data local da filial). A diferença de caução, as parcelas refeitas, a diária do atraso, a caução da locação e a diferença do período em curso saem todos desse preço, mesmo que a tabela mude até a conclusão;
- o veículo novo fica `reservado`;
- abrem a chegada do veículo atual e a saída do novo, em `rascunho`, e a devolução da locação nasce em `rascunho` com essa chegada (um acerto só, `vistorias.md`);
- caução da nova categoria **maior**: a diferença vira conta `caucao` aberta com vencimento hoje, e o veículo novo só sai depois de paga (Juliana: 20000). Caução **menor**: nenhuma conta; o acerto final desconta da caução total paga.

Recusas: 400 `motivo` vazio; 403 para quem não cria; 409 `transicao_locacao` fora de `ativa`; 409 `cancelamento_em_andamento`; 409 `troca_pendente` ("Esta locação já tem uma troca de veículo pendente."); 422 `LOC-03` (veículo novo indisponível), `FIL-05` (de outra filial), `CLI-02` (CNH sem a categoria), `LOC-01` (categoria sem preço vigente).

Com a troca pendente: a renovação é permitida (`LOC-08`; as parcelas novas saem da categoria atual e são refeitas na conclusão), o cancelamento e o pedido de cancelamento respondem 409 `troca_pendente` (abaixo), e encerrar a devolução responde 409 `troca_pendente` (`vistorias.md`).

#### Troca concluída
Quando a chegada do veículo antigo e a saída do novo estão concluídas, em qualquer ordem, `vistorias` chama `locacoes.services.concluir_troca`, numa transação. "Dia da troca" é o dia local da filial na conclusão.
- O trecho atual fecha (`TrechoLocacao.fim`) e o novo começa. A locação passa ao veículo novo (`alugado`), com o período, a diária e a caução **guardados na troca**. O veículo antigo fica `disponivel`, ou `em_manutencao` com avaria "vai para oficina" (`DEV-04`).
- **Parcelas refeitas inteiras** (`LOC-09`, como na renovação, `LOC-08`): cada parcela em aberto que vence depois do dia da troca passa a valer o período `k` dela pelo preço guardado com todos os descontos daquele período (`calculo.preco_com_descontos`: o `desconto_pct` do vendedor e o plano especial de desconto contando os períodos desde o começo da locação), mais os extras como estavam. No mensal em 4 semanais, cada parcela é a sua quarta parte desse valor. Ex.: Mensal fidelidade no 3º mês, Street → Scooter premium: 107100 → **143100**; no 1º mês, sem desconto. Juliana (semanal, sem desconto): parcela 3 de 32900 → **44900**.
- **Diferença do período em curso** (`LOC-09`, `DEV-01`), calculada aqui e guardada na troca:
  - o período em curso e os dias restantes são os do `calcular_encerramento` (`LOC-12`) no dia da troca: o período `k` que contém o dia, `dias_do_periodo = fim − início` e `dias_restantes = fim − dia`, em datas locais. Na diária, `dias_do_periodo = 1` e `dias_restantes` são os blocos inteiros de 24 h até o fim previsto (`diarias_nao_usadas`). No dia do fim previsto ou depois, não há período em curso e a diferença é 0;
  - `periodo_antigo_centavos` = preço do período `k` da locação antes da troca e `periodo_novo_centavos` = preço do período `k` pelo preço guardado, ambos com os descontos daquele período;
  - `diferenca_centavos` = sinal × `proporcional(|novo − antigo|, dias_restantes, dias_do_periodo)` (`comum.dinheiro`, arredondado uma vez no centavo), menos `ja_refeito_centavos`;
  - `ja_refeito_centavos`: só no mensal em 4 semanais, a soma do que as parcelas refeitas que vencem antes do fim do período em curso subiram (ou, com sinal, desceram). Esses dias já passaram ao preço novo pela parcela e não entram duas vezes (`[decisão]` da T-122 para o produto confirmar; nos outros planos é 0, porque a parcela do período em curso vence no começo dele);
  - positivo é cobrança e negativo é crédito, um item por troca no acerto final (`diferenca_troca`, `vistorias.md`). Juliana: período de 07 a 14 out, (44900 − 32900) ÷ 7 × 7 = **12000**.
- Auditoria: `locacao.trocar_veiculo` e `locacao.concluir_troca`, com `LOC-09`. Evento `vistorias.troca_concluida` (`vistorias.md`).

#### POST /api/locacoes/{id}/trocar-veiculo/cancelar/
Cancela a troca pendente (`LOC-09`). App `vistorias` (`apps/vistorias/api`), pelo serviço `vistorias.services.cancelar_troca`, que chama `locacoes.services.cancelar_troca`.
Perfis: administrador, gerente e vendedor (quem pode pedir a troca), na filial da locação. Vistoriador e financeiro: 403. Locação `ativa` ou `devolucao_atrasada`.
Corpo: `{ "motivo": "Cliente desistiu da scooter" }`.
200:
```json
{ "troca": { "id": 41, "status": "cancelada", "cancelada_em": "2026-10-07T22:10:00Z",
             "saida_vistoria": { "id": 3102, "status": "descartada" },
             "devolucao_vistoria": { "id": 3101, "status": "concluida" },
             "conta_caucao": { "id": 9010, "status": "paga" },
             "devolucao_id": 701 } }
```
`conta_caucao` vem `null` quando a troca não teve diferença de caução a cobrar.

Na mesma transação, com a locação e a troca travadas:

| Peça | Antes | Depois |
| --- | --- | --- |
| Troca | `pendente` | `cancelada`, com `motivo_cancelamento`, `cancelada_por` e `cancelada_em` |
| Saída do veículo novo | `rascunho` | `descartada` (`vistorias.md`); fotos e respostas ficam guardadas |
| Veículo novo | `reservado` | `disponivel`, pelo sistema (`veiculos.services.transicionar`, origem a locação) |
| Conta da diferença de caução | aberta (inclusive vencida) | `cancelada` |
| | paga | fica como está: entra na caução total paga e volta no acerto final (`DEV-02`) |
| Chegada do veículo antigo | `rascunho` | `descartada`; o cliente segue com o veículo antigo, que continua `alugado`. Se a devolução da locação apontava para ela, a devolução continua `rascunho` sem chegada (`vistoria = null`), e `POST /api/locacoes/{id}/devolucao/` abre uma chegada nova do veículo atual quando ele voltar (`vistorias.md`); `devolucao_id` vem `null` na resposta e no detalhe enquanto não houver chegada |
| | `concluida` | fica como a chegada da devolução da locação, que segue as regras de sempre: antes do dia do fim previsto, encerrar pede o encerramento antecipado aprovado (`DEV-07`); o veículo antigo continua `alugado` até encerrar |
| Locação | | não muda: mesmo veículo, preço, caução, parcelas e trechos |

Nada da troca cancelada é apagado. Auditoria, com `LOC-09` e o motivo: `locacao.cancelar_troca` (a troca), `vistoria.descartar` (cada vistoria descartada), a transição do veículo (`veiculos`) e `conta_receber.cancelar` (`financeiro`). Nenhum evento de domínio: nada acima de `vistorias` reage a uma troca que não aconteceu.

Recusas:
- 400 `{ "codigo": "validacao", "campos": { "motivo": ["Informe o motivo do cancelamento da troca."] } }`.
- 409 `{ "codigo": "transicao_troca", "mensagem": "Esta locação não tem troca de veículo pendente." }`: sem troca, ou a troca já `concluida` ou `cancelada` (inclusive concluída por outra pessoa ao mesmo tempo).
- 409 `{ "codigo": "troca_saida_concluida", "mensagem": "O veículo novo já foi entregue. Conclua a troca com a chegada do veículo antigo." }`: a saída do veículo novo já está concluída. A `LOC-09` só diz o que fazer com a saída em rascunho; a recusa é provisória, `[decisão]` da T-122 para o produto.
- 409 `transicao_locacao` com a locação fora de `ativa` e `devolucao_atrasada`.

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
- Com uma troca de veículo pendente, o cancelamento direto e o pedido respondem 409 `{ "codigo": "troca_pendente", "mensagem": "Conclua ou cancele a troca antes" }` (`LOC-12`, `LOC-09`), antes do perfil e do resto; nada muda. O caminho é cancelar a troca e então pedir o encerramento. `cancelamento/simular` continua respondendo (é só leitura). O pedido de troca já é recusado com um cancelamento em curso (`cancelamento_em_andamento`), então o pedido de cancelamento pendente e a troca pendente não convivem.
- Administrador, gerente ou quem tem `cancelar_contrato`: 200, efeito na hora.
- Vendedor: 202 `{ "pedido_aprovacao": { "id", "tipo": "APR-02", "status": "pendente" } }`; o sinal `cancelamento_pendente` acende.
Efeito ao valer:
- Antes da retirada (`rascunho`, `aguardando_retirada`): `cancelada` na hora; contas abertas canceladas, pagas estornadas (devolução ao cliente pelo `financeiro`), veículo `reservado` volta a `disponivel`, comissão `estornada`. Depois do commit, publica `locacoes.locacao_cancelada`, e `vistorias` descarta a vistoria de saída em `rascunho` (T-410, ADR 0035; antes ela ficava aberta).
- Depois da retirada: a locação fica marcada com o encerramento antecipado aprovado (`cancelamento.status = "aprovado"`) e segue para a devolução (`vistorias.md`). A aprovação não cancela parcelas: até a devolução, elas vencem, atrasam e podem ser pagas como qualquer outra. `cancelamento.multa_centavos` e `devolver_centavos` são a estimativa para `cancelamento.data`. O acerto da devolução recalcula a multa e o crédito pelo dia da devolução, com o mesmo cálculo de `cancelamento/simular`, e o encerramento da devolução cancela as parcelas que vencem depois desse dia (`DEV-07`, T-116; CA-016-25: Carlos aprovado para 07 out com estimativa de 5988 e devolvido em 16 out → multa 5490, cobrar 67377). Ao encerrar a devolução, o status final é `cancelada`. Se a devolução é no dia do fim previsto ou depois, ela é comum: sem multa nem crédito, com o atraso da `LOC-10`, `forma_devolucao` escolhida no acerto e a locação `encerrada`; o pedido aprovado fica registrado, sem efeito (`DEV-07`, T-118; Carlos devolvido em 28 out → cobrar 92855).
Recusado pelo gerente: o sinal apaga e o vendedor é avisado com o motivo.
409 `transicao_locacao` em `encerrada` ou `cancelada`.

### Cancelamento automático da locação não retirada (LOC-12, AUT-17, T-410)

Sem endpoint: só a tarefa automática cancela (ADR 0035, itens 3 e 4). A tela vê o resultado no detalhe (`status = "cancelada"`, `cancelamento.automatico = true`) e no histórico.

**Prazo.** `ultimo_dia_retirada` = data local do `inicio` + 3 dias corridos, em `America/Sao_Paulo`; o feriado da filial conta (`FIL-03` não vale aqui). Início 05 nov → último dia 08 nov, cancelamento em 09 nov 00:10 (CA-410-14). Início futuro: o prazo só corre do início (confirmada em 01 nov com início em 10 nov → cai em 14 nov 00:10, CA-410-16).

**Às 00:10** (`aut_17_cancelar_nao_retiradas`): toda locação `aguardando_retirada` com `ultimo_dia_retirada < hoje`, uma transação por locação, com a locação travada e o status conferido de novo. Na mesma transação, pelo núcleo do cancelamento antes da retirada (acima):

| Peça | Depois |
| --- | --- |
| Locação | `cancelada`, `cancelada_em`, motivo "Não retirada em 3 dias da data de início"; auditoria `locacao.cancelar_nao_retirada`, ator Sistema, regra `LOC-12` |
| Contas abertas (parcelas e caução) | `cancelada` (`conta_receber.cancelar`, `LOC-12`) |
| Contas pagas | um `Reembolso` `a_fazer` do total pago (CA-410-22: R$ 629,00), forma `estorno_cartao` se o 1º pagamento foi no cartão, senão `pix`. Nunca `dinheiro`: à meia-noite não há caixa aberto |
| Pedidos abertos (`APR-01`, `APR-02`) | fechados por `aprovacoes.cancelar_pendentes`, com o motivo da locação |
| Contrato | não assinado vai para `cancelado` (`contratos`), e o link de assinatura deixa de valer |
| Comissão (`FIN-09`), se existir | `estornada` |
| Veículo | `reservado` → `disponivel` (`veiculos.services.transicionar`, origem a locação) |
| Vistoria de saída | `rascunho` vira `descartada` por `vistorias`, pelo evento `locacoes.locacao_cancelada`; a `concluida` fica no histórico |

Nenhuma multa (`multa_centavos = 0`). A locação cancelada não volta: o cliente faz outra. A locação `ativa`, `devolucao_atrasada`, `encerrada` ou `cancelada` nunca é selecionada (CA-410-20). A retirada concluída até 23:59 do último dia leva a `ativa`, e a tarefa não a pega (CA-410-15).

**Execução perdida** (CA-410-19): a seleção é "passou do último dia", então a próxima execução cancela o que ficou para trás, uma vez por locação (a cancelada sai da seleção).

**Às 08:00** (`aut_17_avisar_nao_retiradas`): toda locação `aguardando_retirada` com `ultimo_dia_retirada == hoje`. Os gerentes ativos ligados à filial da locação (`filiais.selectors.gerentes`, `FIL-02`) recebem, no sino e por e-mail (`notificacoes.services.avisar(..., por_email=True)`):

```
tipo: "locacao_nao_retirada"
titulo: "A LOC-2866 será cancelada amanhã se não for retirada hoje. Honda Biz 125 CDL-0B10, cliente {nome}."
link: "/locacoes/2866"
urgente: true
chave: "aut17-aviso-{locacao_id}"
```

- Modelo e placa como no texto da regra: `{marca} {modelo} {placa com hífen}` (`docs/api/README.md`, placa em texto montado). Seed: "A LOC-2856 será cancelada amanhã se não for retirada hoje. Honda CG 160 Fan SAK-1D39, cliente Lucas Ferreira." (CA-410-22).
- Uma vez por gerente e por locação (a `chave`); e-mail só para quem recebeu o aviso agora. Vendedor, administrador e o cliente não recebem (CA-410-13; aviso ao cliente é o ponto em aberto 3 do produto, padrão A).
- O aviso de um dia perdido não sai depois: no dia seguinte, a locação está na seleção do cancelamento e fora desta.
- Confirmada no último dia depois das 08:00: o aviso sai na confirmação, com a mesma `chave` (CA-410-17).
- **Push:** a regra pede sino, push e e-mail. O push não existe no código nem tem contrato de notificações (`PreferenciaNotificacao` está só no modelo de dados). A `AUT-17` sai com sino e e-mail, e o push entra quando o canal existir, sem mudar a tarefa (ADR 0035, item 6; registrado no backlog).

---

## Planos especiais (tela Precos)

`GET /api/planos-especiais/` (todos) → `{ "resultados": [ { "id", "nome": "Entregador", "periodicidade": "semanal", "regra": "preco_fixo", "preco_centavos": 27900, "desconto_pct": null, "a_partir_do_periodo": null, "categorias": [], "condicoes": "Semanal com km livre e troca de óleo inclusa", "locacoes_ativas": 18, "ativo": true } ] }`.
`POST`, `PATCH /api/planos-especiais/{id}/`, `POST .../desativar/` · administrador. Mudança vale para locações novas (`LOC-15`); quem já assinou mantém.

## Planos de compra (tela Precos, `LOC-16`, T-420)

`GET /api/planos-compra/` (todos os perfis que criam locação; `?ativo=true` para a Nova locação, `?categoria=<id>`) →
```json
{ "resultados": [ { "id": 3, "nome": "Compra Street 24 meses", "categoria": { "id": 2, "nome": "Street 150–160" },
  "periodicidade": "mensal", "parcelas": 24, "valor_parcela_centavos": 119000, "condicoes": "",
  "caucao_centavos": 30000, "ultima_parcela_centavos": 89000, "locacoes_ativas": 0, "ativo": true } ] }
```
- `caucao_centavos` é a caução vigente da categoria; `ultima_parcela_centavos` = `max(0, valor_parcela_centavos − caucao_centavos)`, para a tela mostrar sem conta. Os dois são de hoje e podem mudar até a confirmação.
- `POST /api/planos-compra/`, `PATCH /api/planos-compra/{id}/`, `POST /api/planos-compra/{id}/desativar/` · administrador. Corpo: `{ nome, categoria_id, periodicidade: "semanal" | "mensal", parcelas, valor_parcela_centavos, condicoes? }`. 400 `validacao`: nome repetido, `parcelas` fora de 2 a 260, valor 0. Mudar ou desativar vale só para locações novas (`LOC-15`); auditoria `plano_compra.criar`, `editar`, `desativar`.
- Valem com o padrão A do ponto em aberto 1 da `LOC-16` (ADR 0037, item 2).

---

## Locação com intenção de compra (`LOC-16`, T-420, ADR 0037)

Tudo o que esta seção não muda segue a locação comum: estados, retirada (vistoria, contrato e 1º pagamento), contas que esperam a retirada (`LOC-05`, ADR 0035), régua e bloqueio (`LOC-07`, `CLI-05`), cancelamento antes da retirada e `AUT-17` (`LOC-12`), devolução e acerto (`vistorias.md`). Critérios: `docs/qa/criterios/T-420.md` (CA-420-01 a 17).

### Na representação

A linha da lista e o detalhe ganham `tipo` (`comum` ou `intencao_compra`) e `tipo_rotulo` ("Com intenção de compra"; `null` na comum). `GET /api/locacoes/?tipo=intencao_compra` filtra. No detalhe do tipo `intencao_compra`, o bloco `compra` (na comum, `null`):

```json
"tipo": "intencao_compra", "tipo_rotulo": "Com intenção de compra",
"compra": {
  "plano": { "id": 3, "nome": "Compra Street 24 meses" },
  "parcelas_total": 24, "parcelas_pagas": 1,
  "valor_parcela_centavos": 119000, "ultima_parcela_centavos": 89000, "sobra_caucao_centavos": 0,
  "andamento": "Parcela 1 de 24 · faltam 23 para a transferência",
  "falta_para_quitar": [],
  "quitada_em": null,
  "venda": null
}
```

- `plano`, `parcelas_total` e `valor_parcela_centavos` são os congelados na confirmação (`LOC-15`); no rascunho, os do plano escolhido.
- `parcelas_pagas`: parcelas (`tipo = parcela`) pagas da locação. `ultima_parcela_centavos`: o valor da última, já com a caução abatida. `sobra_caucao_centavos`: o que volta ao cliente na quitação quando a caução é maior que a parcela (CA-420-14: R$ 101,00).
- `andamento` (montado pela API, CA-420-05; textos fixados pelo produto em 05 nov 2026, `LOC-16` "Na tela"):
  - parcela a pagar: "Parcela {pagas} de {total} · faltam {total − pagas} para a transferência"; com uma só a pagar, no singular: "Parcela 23 de 24 · falta 1 para a transferência";
  - todas as parcelas pagas e outra conta da locação aberta: "24 de 24 parcelas pagas · faltam as contas abaixo para a transferência" (as de `falta_para_quitar`);
  - quitada, com `venda.transferencia.pendente`: "Quitada em 10/10/2028 · falta a transferência no Detran"; com a transferência registrada: "Quitada em 10/10/2028 · transferência feita em 15/10/2028" (datas no fuso da filial);
  - antes da 1ª parcela paga (`rascunho`, `aguardando_retirada`): `null`.
- `falta_para_quitar` (CA-420-13): as outras contas da locação abertas, de `financeiro.selectors`: `[ { "conta_id": 9120, "rotulo": "Avaria · Retrovisor direito", "valor_centavos": 12000 } ]`, com o valor do dia (`FIN-03`). Vazia enquanto ainda há parcela a pagar (as parcelas não entram na lista).
- `quitada_em` e `venda` depois da quitação: `{ "id": 18, "codigo": "VEN-0178", "transferencia": { "feita_em": null, "registrada_por": null, "pendente": true }, "acoes": { "registrar_transferencia": true } }`, a venda da `VEN-11`, fornecida por `vendas` (`vendas.md`). "Transferência feita" chama `POST /api/locacoes/{id}/transferencia/` (`vendas.md`).
- O vistoriador recebe `compra` sem os campos `_centavos` (`USR-09`).
- `situacao` e `sinais`: `devolve_hoje` nunca acende neste tipo, e a locação não chega a `devolucao_atrasada` pela data (`LOC-10` não vale, CA-420-10). Encerrada pela quitação, `situacao` é `{ "codigo": "quitada", "rotulo": "Quitada", "tom": "sucesso" }`.
- `devolucao`: `prevista_para` e `aviso_atraso` vêm `null` (não há devolução no fim previsto), a não ser com o encerramento aprovado: aí `prevista_para` é a `cancelamento.data`.
- `acoes`: `renovar` e `trocar_veiculo` sempre `false` (CA-420-06); `encerrar_por_atraso` (abaixo); `cancelar` como na comum (o encerramento pedido pelo cliente passa pela `APR-02` do vendedor ou direto pelo gerente, CA-420-09); `registrar_devolucao` só com o encerramento aprovado.

### POST /api/locacoes/simular/ e POST /api/locacoes/ com o tipo

Corpo: `{ "tipo": "intencao_compra", "plano_compra_id": 3, "cliente_id", "veiculo_id", "inicio", "forma_pagamento" }`. Sem `tipo`, é `comum`, como hoje.
- `periodicidade` e `periodos` vêm do plano; mandados, são ignorados se iguais e recusados se diferentes. `plano_especial_id`, `fim_previsto`, `extras` com item, `desconto_pct` diferente de 0 e `parcelamento_mensal` recusam com 400 `validacao` no campo: "A locação com intenção de compra usa o valor do plano." (CA-420-02).
- O veículo tem de ser da categoria do plano: 400 `validacao` em `veiculo_id`, "O veículo não é da categoria do plano.". Plano inativo: 400 em `plano_compra_id`.
- `tipo` só muda no rascunho.

Simulação do CA-420-01 (início 10 nov 2026 10:00):
```json
{
  "fim_previsto": "2028-11-10T13:00:00Z",
  "linhas": [
    { "rotulo": "24 parcelas mensais × R$ 1.190,00", "valor_centavos": 2856000 },
    { "rotulo": "Caução (abatida na última parcela)", "valor_centavos": 30000 },
    { "rotulo": "Última parcela", "valor_centavos": 89000 }
  ],
  "valor_periodo_centavos": 119000,
  "hoje_na_retirada_centavos": 149000,
  "texto_retirada": "Na retirada: primeira parcela mais caução.",
  "parcelas_previstas": [ { "numero": 1, "vencimento": "2026-11-10", "valor_centavos": 119000 },
                          "...",
                          { "numero": 24, "vencimento": "2028-10-10", "valor_centavos": 89000 } ],
  "caucao_centavos": 30000,
  "compra": { "parcelas_total": 24, "valor_parcela_centavos": 119000, "ultima_parcela_centavos": 89000, "sobra_caucao_centavos": 0 },
  "precisa_aprovacao_desconto": false, "impedimentos": [], "avisos": []
}
```
- `fim_previsto` = início + o prazo do plano (24 meses ou o número de semanas, `LOC-05`). As parcelas seguem o calendário da `LOC-05` a partir do início; a última nasce com `ultima_parcela_centavos`.
- `avisos` traz `{ "codigo": "LOC-16", "mensagem": "Publique o modelo de contrato da locação com intenção de compra antes de confirmar.", "detalhes": { "link": "/admin/contratos" } }` sem o modelo publicado.

### POST /api/locacoes/{id}/confirmar/ com o tipo

Como na comum (reserva, contas com `aguarda_retirada`, comissão de locação da `FIN-09`), mais:
- congela `plano_compra`, `compra_parcelas` e `compra_valor_parcela_centavos` (CA-420-04);
- cria as `compra_parcelas` parcelas de uma vez, a última com a caução abatida (no mínimo R$ 0,00; a de R$ 0,00 nasce `paga`, sem movimento de caixa), e a caução;
- sem modelo publicado de `finalidade = locacao_compra`: 422 `{ "codigo": "LOC-16", "mensagem": "Publique o modelo de contrato da locação com intenção de compra antes de confirmar.", "detalhes": { "link": "/admin/contratos" } }`, conferido antes de tudo o mais depois do `inicio_vencido` (CA-420-03). Na comum, nada muda (o `IMP-04` continua na geração do contrato).
- O contrato gerado depois (`POST /api/locacoes/{id}/contrato/`) usa o modelo dessa finalidade (`contratos.md`).

### Renovar e trocar

`POST .../renovar/simular/`, `.../renovar/` e `.../trocar-veiculo/`: 409 `{ "codigo": "LOC-16", "mensagem": "A locação com intenção de compra não se renova." }` e `{ "codigo": "LOC-16", "mensagem": "A locação com intenção de compra não troca de veículo. Encerre esta e abra outra." }` (CA-420-06).

### POST /api/locacoes/{id}/encerrar-por-atraso/

Perfis: administrador e gerente da filial. Só no tipo `intencao_compra`, `ativa`, com parcela atrasada (`sinais.pagamento_atrasado`). Corpo: `{ "motivo": "Parcela 2 com 16 dias de atraso", "data": "2026-12-26" }` (`data` padrão hoje, não antes de hoje).
- 200: detalhe, com `cancelamento = { "status": "aprovado", "pedido_aprovacao_id": null, "antes_da_retirada": false, "por_atraso": true, "data", "multa_centavos": 0, "devolver_centavos": 0, "motivo" }` e `acoes.registrar_devolucao = true`. Sem `APR-02` (CA-420-08).
- Segue pelo mesmo caminho do encerramento antecipado aprovado: a devolução e o acerto de sempre, e o status final `cancelada`.
- `acoes.encerrar_por_atraso`: `true` nessas condições, para esses perfis.
- 409 `{ "codigo": "LOC-16", "mensagem": "Esta locação não tem parcela atrasada. Para encerrar a pedido do cliente, use Cancelar locação." }` (texto fixado pelo produto em 05 nov 2026; a exigência da parcela atrasada está na `LOC-16`); 409 `transicao_locacao` fora de `ativa`; 409 `cancelamento_em_andamento` com pedido ou encerramento já em curso; 403 para os outros perfis. Auditoria `locacao.encerrar_por_atraso`.

### Encerramento antes do fim (`cancelamento/simular`, `cancelar`, acerto)

No tipo `intencao_compra`, o cálculo da `LOC-12` e da `LOC-13` não vale (padrão A do ponto em aberto 2):
- `cancelamento/simular` devolve `multa_centavos: 0`, `credito_semanas` e `credito_dias` com 0, `devolver_centavos: 0`, `cobrar_centavos: 0` e `parcelas_canceladas_centavos` com as parcelas abertas que vencem depois da `data`; `avisos: [ { "codigo": "LOC-16", "mensagem": "O que foi pago fica como aluguel do período usado." } ]`.
- No acerto da devolução (`vistorias.md`), entram as parcelas vencidas até o dia e não pagas, com multa e juros (`DEV-07`, `FIN-03`); as que vencem depois são canceladas; sem multa de encerramento nem crédito; a caução cobre o acerto e a sobra volta, como na comum (CA-420-08, 09). Depois do dia do encerramento sem o veículo voltar, corre o atraso da `LOC-10` daquela data.

### Quitação

Sem endpoint: acontece no pagamento (ADR 0037, item 4).
- `locacoes.services.quitar_se_pago(locacao)` roda no assinante de `financeiro.parcela_paga` para toda conta da locação. Quita quando a locação é `intencao_compra`, está `ativa`, sem encerramento aprovado, todas as parcelas estão pagas e não há outra conta da locação aberta. Idempotente pelo `quitada_em`.
- Na mesma transação:

| Peça | Depois |
| --- | --- |
| Locação | `encerrada`, `quitada_em`, `encerrada_em`; sem vistoria de devolução e sem acerto; auditoria `locacao.quitar`, ator Sistema, regra `LOC-16` |
| Caução | continua `paga`, usada no abatimento; não volta |
| Sobra da caução (caução maior que a parcela) | `Reembolso` `a_fazer` de `sobra_caucao_centavos` pelo `financeiro`, forma `pix`, motivo "Sobra da caução na quitação da LOC-x" (CA-420-14) |
| Venda, veículo e aviso | evento `locacoes.locacao_quitada` (abaixo): `vendas` cria a venda de R$ 0,00 (`VEN-11`), passa o veículo de `alugado` a `vendido` e avisa os gerentes (`vendas.md`) |
| Comissão de locação (`FIN-09`) | como estava (a quitação não estorna) |

- O veículo **não** volta a `disponivel`: o `encerrar(locacao, devolucao)` de sempre não é chamado.
- Estorno de parcela depois da quitação: a conta estornada vira conta a receber do cliente (`financeiro`), e a quitação não se desfaz.
- `AUT-06` e preventivas param sozinhas porque o veículo `vendido` sai da seleção delas (CA-420-17).

### Evento `locacoes.locacao_quitada`

Publicado dentro da transação da quitação (não depois do commit): `locacao_id`, `codigo`, `filial_id`, `cliente_id`, `veiculo_id`, `vendedor_id` (o vendedor da locação), `quitada_em`. Assinante: `vendas.eventos` (`vendas.md`). Se o assinante falha, a quitação volta inteira, e o pagamento também (ADR 0011).

---

## Interface interna

| Item | Uso |
| --- | --- |
| `locacoes.services.registrar_vistoria_saida(locacao, vistoria)` | chamado por `vistorias` ao concluir a saída; grava `vistoria_saida_ok_em`, `km_saida` e verifica a ativação. |
| `locacoes.services.encerrar(locacao, devolucao)` | chamado por `vistorias` ao encerrar a devolução (`DEV-06`): `encerrada` (ou `cancelada` no encerramento antecipado), `devolvida_em`, comissão e eventos. |
| `locacoes.services.pedir_troca`, `vincular_vistorias_da_troca`, `concluir_troca`, `cancelar_troca(troca, motivo, usuario)` | chamados por `vistorias` (`LOC-09`). `cancelar_troca` leva a troca a `cancelada`, o veículo novo a `disponivel` e a conta aberta da diferença de caução a `cancelada` (`financeiro.services.cancelar_conta`, nova); as vistorias são de `vistorias`. |
| `locacoes.services.troca_pendente(locacao)` e `caucao_da_troca_paga(troca)`; `locacoes.selectors.trocas_concluidas(locacao)` | a troca pendente; a diferença de caução paga; as trocas concluídas, com `diferenca_centavos` e os campos da conta, para o acerto (`vistorias`). |
| `locacoes.selectors.calcular_atraso(locacao, momento) -> { dias, valor_centavos }` | `LOC-10`, `LOC-11`, `FIL-03`; usado no acerto. |
| `locacoes.selectors.calcular_encerramento_antecipado(locacao, data)` | `LOC-12`, `LOC-13`; o mesmo cálculo de `cancelamento/simular`. |
| assinantes | `financeiro.parcela_paga` (1º pagamento), `contratos.contrato_assinado`, `aprovacoes.pedido_decidido` (`APR-01`, `APR-02`). |
| evento publicado | `locacoes.locacao_encerrada` (preventivas, `MAN-03`). `locacoes.locacao_cancelada` (T-410): `locacao_id`, `codigo`, `antes_da_retirada`, `automatico`, `motivo`, depois do commit de todo cancelamento antes da retirada, pedido ou automático; `vistorias` assina e descarta a saída em `rascunho`. |
| `locacoes.services.quitar_se_pago(locacao)` | `LOC-16` (T-420): a quitação, chamada pelo assinante de `financeiro.parcela_paga`; publica `locacoes.locacao_quitada` (`locacao_id`, `codigo`, `filial_id`, `cliente_id`, `veiculo_id`, `vendedor_id`, `quitada_em`) dentro da transação; `vendas` assina (ADR 0037). |
| `locacoes.selectors.ultimo_dia_retirada(locacao) -> date` | `LOC-12` (T-410): data local do `inicio` + 3. Uma função só para a confirmação (`inicio_vencido`), a simulação, o `prazo_retirada` do detalhe e a `AUT-17`. |
| `locacoes.services.cancelar_nao_retirada(locacao_id)` e `avisar_nao_retirada(locacao)` | `AUT-17` (T-410): o cancelamento automático e o aviso aos gerentes, acima. |
| anotações fornecidas (ADR 0015) | `locacao_atual` para `veiculos` e `clientes`; `locacoes_ativas` e contador de operação para `filiais`; filtro `com_locacao` e contador `locacao_aberta` (inativar, `cliente_com_pendencia`) para `clientes`. |
| tarefas | `aut_01_lembrete_de_devolucao` (08:00), `aut_02_marcar_devolucao_atrasada` (de hora em hora), limpeza de rascunhos com 24 h, `aut_17_cancelar_nao_retiradas` (00:10) e `aut_17_avisar_nao_retiradas` (08:00), com as versões `_de_todas` no Beat e o módulo `locacoes_vistoria` (`PLT-12`). |

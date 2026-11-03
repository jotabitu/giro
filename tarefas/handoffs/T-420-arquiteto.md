# T-420 (parte do arquiteto) · Locação com intenção de compra · arquiteto → orquestrador, backend, frontend, design-system, produto, qa

**O que foi feito:**
1. ADR 0037, com as decisões caras de desfazer.
2. Contrato e modelo de dados, a partir da ADR.

Tudo no PR #476 (o #475, só com a ADR, foi fechado).

**Onde:**
- `docs/decisoes/0037-locacao-com-intencao-de-compra.md` (ajustada aqui: o modelo não publicado é 422, como o `IMP-04`; a transferência fica em `POST /api/locacoes/{id}/transferencia/`).
- `docs/api/locacoes.md`: "Planos de compra" e "Locação com intenção de compra" (novas), "Quem pode" e "Interface interna".
- `docs/api/vendas.md` (novo): a venda da quitação e a tarefa da transferência.
- `docs/api/contratos.md`: finalidade `locacao_compra` e o grupo de marcadores `compra`.
- `docs/api/painel.md`: transferências pendentes nas `pendencias.itens`.
- `docs/decisoes/modelo-de-dados.md`: item 12a (`PlanoCompra`), item 13 (`tipo` e os campos da compra, `CHECK locacao_tipo_campos`), item 17 (`Venda` com `origem`, `locacao`, transferência) e as restrições.

**Decisões (ADR 0037):**
1. `Locacao.tipo` com o plano congelado (`plano_compra`, `compra_parcelas`, `compra_valor_parcela_centavos`), `quitada_em` e `encerrada_por_atraso`; o calendário é o de hoje (`periodicidade` + `periodos`); a última parcela nasce com a caução abatida, no mínimo R$ 0,00 (a de R$ 0,00 nasce `paga`).
2. `locacoes.PlanoCompra` separado do `PlanoEspecial` (padrão A do ponto em aberto 1).
3. Finalidade de contrato `locacao_compra`; sem modelo publicado, 422 `LOC-16` na confirmação.
4. Quitação em `locacoes.services.quitar_se_pago`, em todo `financeiro.parcela_paga` da locação; evento `locacoes.locacao_quitada` dentro da transação; `vendas` cria a venda, passa o veículo a `vendido` e avisa os gerentes. A ordem dos apps não muda.
5. `vendas.Venda` inteira, com `origem` `balcao` ou `quitacao_locacao`; só os serviços da `VEN-11` agora.
6. A tarefa da transferência é a própria venda (`transferencia_feita_em`); a rota fica sob a locação porque `/api/vendas/...` só abre com o recurso `vendas_comissoes` (`PLT-12`), e a locação com intenção de compra existe em qualquer plano que aluga.

**Contrato (resumo):**
- `GET/POST/PATCH /api/planos-compra/`, `POST .../desativar/` (administrador).
- Simular, criar e confirmar com `tipo` e `plano_compra_id`; desconto, extras, plano especial e `parcelamento_mensal` recusados (400); veículo fora da categoria do plano (400).
- Detalhe e lista com `tipo` e `tipo_rotulo`; bloco `compra` com `andamento`, `falta_para_quitar`, `quitada_em` e `venda`.
- Renovar e trocar: 409 `LOC-16`. `POST /api/locacoes/{id}/encerrar-por-atraso/` (administrador e gerente, sem `APR-02`). Encerramento antes do fim sem multa nem crédito.
- Quitação sem endpoint; `POST /api/locacoes/{id}/transferencia/` fecha a tarefa.
- `GET /api/vendas/` e `GET /api/vendas/{id}/` com o recurso `vendas_comissoes`.

**Regras cobertas:** `LOC-16`, `VEN-11` (no contrato; os testes `test_loc_16_*` e `test_ven_11_*` são do backend).

## CA-420-12 (a venda "aparece em Vendas"): decidido

**Decisão do dono em 03 nov 2026: opção A.** A tela `Vendas` (`docs/telas/html/Vendas-*.dc.html`, rota `/vendas`) não existe no frontend, e a T-420 não a faz.

- **Na T-420, o QA confere pela API:** o detalhe da locação quitada traz `compra.venda` (código, transferência, `acoes.registrar_transferencia`), e o histórico do veículo traz a venda; com o recurso `vendas_comissoes`, `GET /api/vendas/` devolve a venda com `origem_rotulo` "Quitação de locação", R$ 0,00, sem contas nem comissão; `cancelar` responde 409 `VEN-11`. Critério ajustado em `docs/qa/criterios/T-420.md`.
- **Passa para a tarefa da tela `Vendas`** (registrado na T-418 do backlog): a venda aparece na lista com o rótulo, e o funil, a conversão e a meta não a contam, pelo filtro `origem = "balcao"` que já está no contrato.
- O frontend da T-420 não faz nada em `/vendas`. O contrato não muda.

## Para o produto confirmar

Textos que a regra não dá e que o contrato propõe (`locacoes.md` e `vendas.md`): o `andamento` com todas as parcelas pagas e outra conta aberta ("24 de 24 parcelas pagas · falta pagar o que está abaixo para a transferência") e depois da quitação ("Quitada · veículo do cliente"); as mensagens dos 409 de renovar, trocar e encerrar por atraso; "Só se encerra por atraso com uma parcela atrasada." (a regra não diz se o encerramento por atraso exige parcela atrasada; o contrato exige). Se o produto mudar, é só texto.

## Próximo passo

- **Orquestrador:** avisar o design-system (tipo na Nova locação, planos de compra em `Precos`, bloco de compra e "Transferência feita" no detalhe, toggle da `Onboarding-Contrato`) e o produto (textos acima).
- **Backend (quando o dono liberar):** migrações de `PlanoCompra`, `Locacao` e `Venda` (o app `vendas` ganha `models`, `services`, `selectors`, `eventos`, `api`); o modelo pronto do contrato; os `if` do tipo em `locacoes.services` (confirmar, renovar, trocar, `AUT-02`, encerramento); `quitar_se_pago` no assinante; a rota da transferência em `apps/vendas/api`; OpenAPI e `npm run api:gerar`. Testes com os números do CA-420-01 (24 × R$ 1.190,00, última R$ 890,00, fim 10 nov 2028) e do CA-420-14 (sobra de R$ 101,00).
- **Frontend (quando o dono liberar):** tipo e plano na Nova locação sem desconto e extras; `compra.andamento` e `falta_para_quitar` no detalhe, sem contar parcelas; "Encerrar por atraso" e "Transferência feita" pelas `acoes`; planos de compra em `Precos`.
- **QA:** CA-420-01 a 17 com valores de teste (nenhum número do seed muda).

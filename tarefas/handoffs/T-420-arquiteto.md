# T-420 (ADR do arquiteto) · Locação com intenção de compra · arquiteto → orquestrador, backend, design-system

**O que foi feito:** a ADR 0037, com as decisões caras de desfazer da `LOC-16` e da `VEN-11`. O contrato da API e o modelo de dados ficam para a próxima parte do arquiteto.

**Onde:** `docs/decisoes/0037-locacao-com-intencao-de-compra.md` e o índice em `docs/decisoes/README.md`.

**Decisões:**
1. `Locacao.tipo` (`comum`, `intencao_compra`) com `plano_compra`, `compra_parcelas`, `compra_valor_parcela_centavos` e `quitada_em`; `CHECK` amarrando os campos ao tipo; o calendário é o de hoje (`periodicidade` + `periodos`); última parcela = parcela − caução, no mínimo 0.
2. `locacoes.PlanoCompra` novo (categoria, periodicidade, parcelas, valor), separado do `PlanoEspecial`. Vale com o padrão A do ponto em aberto 1; se o dono escolher B, sai o model e a locação não muda.
3. `contratos.Finalidade.locacao_compra` com modelo pronto; sem modelo publicado, 409 `LOC-16` na confirmação.
4. Quitação em `locacoes.services.quitar_se_pago`, chamada em todo `financeiro.parcela_paga` da locação; publica `locacoes.locacao_quitada`; `vendas` cria a venda, passa o veículo a `vendido` e avisa os gerentes, na mesma transação. A ordem dos apps (ADR 0011) não muda.
5. `vendas.Venda` criada inteira (item 17 do modelo de dados) com `origem` (`balcao`, `quitacao_locacao`), `locacao` única, `descricao`, `transferencia_feita_em` e `transferencia_registrada_por`; só os serviços da `VEN-11` agora; cancelamento da quitação 409 `VEN-11`.
6. A tarefa da transferência é a venda com `transferencia_feita_em` nula: aviso no sino e por e-mail, pendência no painel do gerente, `POST /api/vendas/{id}/transferencia/`.

**Regras cobertas:** `LOC-16`, `VEN-11` (no desenho; testes `test_loc_16_*` e `test_ven_11_*` são do backend).

**O que ficou de fora:** contrato (`docs/api/locacoes.md`, `docs/api/vendas.md` novo), modelo de dados (itens 12a, 13 e 17), o texto do andamento e as rotas do plano de compra em `Precos`.

**Próximo passo:**
- **Orquestrador:** liberar a parte do contrato e do modelo de dados (arquiteto) e avisar o design-system (tipo na Nova locação, planos de compra em `Precos`, andamento na ficha, rótulo em `Vendas`, toggle da `Onboarding-Contrato`). A tela `Vendas` ainda não existe no frontend: o CA-420-12 depende dela ou de uma lista mínima.
- **Backend:** não comece antes do contrato.

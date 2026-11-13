# Conferência T-420 · locação com intenção de compra · 13 nov 2026

Pedido do Orquestrador. Conferido na develop em 623e65c2 (#567), `http://motorapida.localhost:3000`, a 1440 e 390 px, contra `docs/qa/criterios/T-420.md` (LOC-16, VEN-11). Capturas em `tarefas/handoffs/anexos/T-420/`.

O relógio é o real (13 nov), não o de 10 nov dos critérios: as datas do plano saem a partir de hoje (fim previsto 13 nov 2028; parcelas de 13 nov 2026 a 13 out 2028). Sem mexer no `GIRO_DATA_REFERENCIA`, os casos que dependem de dias passarem (07, 08, 10, 17) não foram exercidos. O CA-09 (encerramento pedido pelo cliente, com aprovação e vistoria de devolução) também não.

## Resumo

| CA | Resultado | Como foi |
| --- | --- | --- |
| 420-01 plano e parcelas | Passa | Plano "QA Compra Street 24 meses" (Street, mensal, 24 × R$ 1.190,00). LOC-2876 pela Bruna: fim previsto 13 nov 2028 10:00; 24 parcelas mensais, as 23 primeiras R$ 1.190,00 e a última R$ 890,00; caução R$ 300,00; moto `reservado` |
| 420-02 sem desconto e extras | Passa | API 400 "A locação com intenção de compra usa o valor do plano." para `desconto_pct` (criar e editar) e para `extras`. Na tela, ao escolher "Com intenção de compra" some o bloco "Adicionais" e entra "Plano de compra" (`ca02-nova-intencao-compra-bruna`) |
| 420-03 sem modelo publicado | Passa na API; tela não exercitada | Com o modelo arquivado, `confirmar` responde 422 `LOC-16` "Publique o modelo de contrato da locação com intenção de compra antes de confirmar." com `link: /admin/contratos`. O atalho na tela não foi capturado. Achado A6 |
| 420-04 plano congelado | Passa | Plano para R$ 1.250,00: a LOC-2876 segue com 23 × R$ 1.190,00 + R$ 890,00; a LOC-2877, nova, sai com 23 × R$ 1.250,00 + R$ 950,00 |
| 420-05 retirada e andamento | Passa | Vistoria de saída pela tela, contrato com o modelo da intenção de compra, assinatura pelo link, parcela 1 e caução pagas: `ativa`, moto `alugado`, ficha "Com intenção de compra" e "Parcela 1 de 24 · faltam 23 para a transferência" (`ca05-ficha-locacao-ativa-rodrigo`) |
| 420-06 sem renovar e sem trocar | Passa | `acoes.renovar` e `trocar_veiculo` `false`, sem os botões na ficha. API 409 `LOC-16` com os dois textos do critério (renovar, simular a renovação e trocar) |
| 420-07, 08, 09, 10, 17 | Não exercitados | Dependem do relógio (07, 08, 10, 17) ou do fluxo de devolução (09) |
| 420-11 quitar | Passa | Paga a 24ª (R$ 890,00): `encerrada` na hora, sem vistoria e sem acerto, caução não devolvida, moto `vendido` e fora da Frota (`ca11-frota-sem-a-moto-vendida`). Auditoria `locacao.quitar` (regra `LOC-16`) e `venda.criar_da_quitacao` (`VEN-11`), as duas do Sistema. A tarefa aos gerentes aparece no Início do Rodrigo com atraso (A2) |
| 420-12 a venda da quitação | Passa em parte | `VEN-0001`, `origem` `quitacao_locacao`, `origem_rotulo` "Quitação de locação", R$ 0,00, cliente Paula, vendedora Bruna, em `GET /api/vendas/` e em `compra.venda`. `acoes.cancelar` `false`. A rota de cancelar venda não existe na API, então o 409 `VEN-11` não dá para provocar |
| 420-13 conta aberta segura a quitação | Passa | LOC-2877 com avaria de R$ 120,00 aberta: 24 pagas e `ativa`, moto `alugado`, "24 de 24 parcelas pagas · faltam as contas abaixo para a transferência", avaria em `falta_para_quitar`. Paga a avaria, quita (VEN-0003) |
| 420-14 caução maior que a parcela | Passa, com A4 | Plano semanal 104 × R$ 199,00: LOC-2878, `sobra_caucao_centavos` 10.100; ao pagar a 103ª quita e nasce o reembolso de R$ 101,00 "Sobra da caução na quitação da LOC-2878" (A3) |
| 420-15 pagar antes | Passa | As parcelas 2 a 24 foram pagas hoje, bem antes do vencimento; a quitação saiu no pagamento da última, antes do fim previsto |
| 420-16 tarefa da transferência | Passa na API; a tela do veículo não mostra (A1) | Rodrigo registra "Transferência feita" com a data: "Quitada em 13/11/2026 · transferência feita em 13/11/2026", sai das pendências do Início, o veículo segue `vendido`. A Bruna e a Lúcia não têm `registrar_transferencia` |
| 420-18 andamento | Passa | Os quatro textos conferem: "Parcela 23 de 24 · falta 1 para a transferência", "24 de 24 parcelas pagas · faltam as contas abaixo para a transferência", "Quitada em 13/11/2026 · falta a transferência no Detran" e "… · transferência feita em 13/11/2026". `null` antes da retirada |
| 420-19 encerrar por atraso sem atraso | Passa | Com tudo em dia, `acoes.encerrar_por_atraso` `false`; a API responde 409 `LOC-16` "Esta locação não tem parcela atrasada. Para encerrar a pedido do cliente, use Cancelar locação." |

## Achados

- **A1 · A ficha do veículo vendido não mostra a venda nem a transferência (CA-420-16, `VEN-11`).** `GET /api/veiculos/47/` traz `vendas.itens` com `VEN-0001`, "Quitação de locação" e `transferencia_texto` "Transferência no Detran feita em 13/11/2026 · Rodrigo Pinheiro", mas a tela `/veiculos/47` não tem bloco com isso: só "Locações" (LOC-2876, "Quitada"). O critério diz que a tarefa "fica no histórico do veículo". Captura `ca16-veiculo-vendido-historico-rodrigo-1440`. Dono: Frontend.
- **A2 · O Início do gerente demora a mostrar a transferência pendente.** Logo depois da quitação o card "Pendências do dia" dizia "Nenhuma transferência no Detran pendente" (o canto mostrava "há 4 min"); alguns minutos depois a API devolvia "1 transferência no Detran pendente". Parece cache do painel. O critério pede a tarefa na hora. Capturas `ca11-inicio-gerente-transferencia-pendente`. Dono: Backend, ou confirmar que o tempo é aceito.
- **A3 · O reembolso da sobra da caução diz "Locação cancelada antes da retirada" (CA-420-14).** Em `Reembolsos`, a linha da LOC-2878 (R$ 101,00) traz esse rótulo de origem, embora o motivo diga "Sobra da caução na quitação da LOC-2878". Captura `ca14-reembolso-sobra-caucao-lucia-1440`. Dono: Backend (`origem_rotulo`) e Frontend.
- **A4 · A parcela de R$ 0,00 não existe na lista (CA-420-14).** Com 104 parcelas e caução de R$ 300,00, a ficha lista 103 parcelas e a caução; a "104ª" de R$ 0,00 não aparece, mas o andamento conta 104 ("Parcela 102 de 104 · faltam 2") e `Receber` mostra "Parcela 1 de 103". O critério diz que a última "nasce R$ 0,00". Pode ser decisão do Backend; peço confirmação do Produto. Dono: Produto, depois Backend.
- **A5 · Os textos de auditoria da quitação saem crus.** "Locação LOC-2877: quitar", "Venda VEN-0003: criar da quitacao" e "Veículo: vendido" (com o detalhe "Quitação da LOC-2877"), diferentes dos eventos em português corrido ("Confirmou a locação …"). Mesma classe do achado da T-437. Dono: Backend.
- **A6 · "Despublicar" o modelo é arquivar, e arquivar não tem volta.** Para o CA-420-03 arquivei o modelo "Locação com intenção de compra" (id 2); `publicar` depois respondeu 409 `modelo_arquivado`. Recriei pelo modelo pronto e publiquei (id 3, versão 1), o que devolveu a confirmação das locações de compra. O contrato já gerado (LOC-2876) fica ligado ao modelo 2 arquivado. O critério fala em "despublicado"; hoje a tela e a API só arquivam. Dono: Produto (existe "despublicar"?).
- **A7 · Ficha da locação ativa a 1440 px.** Um cartão em branco sem conteúdo acima do "Resumo", à direita, e o botão da linha da parcela aberta aparece cortado ("Registrar pa…"). Capturas `ca05-ficha-locacao-ativa-rodrigo-1440`. Dono: Frontend.
- **A8 · "Rendeu no ano R$ 0" no veículo vendido.** A ficha do KDG-0T14, quitado com R$ 28.260,00 em parcelas, mostra "locações – custos" zerado. Pode ser regra (a receita some depois da venda); peço confirmação do Produto.
- Observação: o Lucas Ferreira do critério está `bloqueado` no seed (LOC-2856 atrasada); usei Paula Tavares, Murilo Façanha e Letícia Aguiar.

## Dados que ficaram no banco compartilhado

- Planos de compra 2 ("QA Compra Street 24 meses", hoje R$ 1.250,00) e 3 ("QA Compra Street semanal 104").
- LOC-2876 (Paula, KDG-0T14), LOC-2877 (Murilo, MXF-8V34) e LOC-2878 (Letícia, PGF-7W44): quitadas, vendas VEN-0001 a 0003, motos `vendido`. A transferência da LOC-2876 está feita; as outras duas estão pendentes (aparecem no Início do gerente).
- LOC-2879 (Murilo, QRF-6X54): `aguardando_retirada`, moto `reservado`.
- Reembolso de R$ 101,00 da LOC-2878 `a_fazer`.
- O caixa de hoje da Filial Centro ficou **aberto** (Bruna, troco R$ 100,00): o login travou por excesso de tentativas (espera de uns 40 min) antes de eu fechar. Preciso que alguém feche ou me avise quando liberar.
- Modelo de contrato "Locação com intenção de compra" recriado (id 3); o id 2 está arquivado.

## Não exercitado

CA-420-03 na tela (atalho "publicar o modelo"), 07, 08, 09, 10 e 17, o 409 `VEN-11` de cancelar venda (sem rota) e o item da tela `Vendas` (passa para a T-418).

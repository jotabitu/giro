# Vendas

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

A venda tem 7 estados (o funil da tela mostra os 4 principais) e só vende veículo `a_venda`. Telas: `Vendas` (lista), `Venda` (Nova venda, 3 passos: Negócio → Documentos → Assinatura), `Vendedor` (início da vendedora), `Gerente` (aprovações), `Comissoes`.

| Estado | Significa |
| --- | --- |
| `interessado` | contato registrado, sem proposta |
| `proposta` | proposta com valor e forma de pagamento enviada ao cliente |
| `negociacao` | cliente respondeu; contraproposta, troca ou financiamento em análise |
| `aguardando_aprovacao` | desconto acima do limite; espera o gerente |
| `vendida` | contrato assinado e entrada (ou valor total) recebida |
| `perdida` | cliente desistiu ou proposta venceu (7 dias sem resposta) |
| `cancelada` | venda concluída desfeita (`VEN-07`); só a partir de `vendida` |

**Regras**

- `VEN-01` Preço de tabela = valor de venda definido ao colocar o veículo à venda (referência FIPE exibida ao lado).
  - **Textos da referência FIPE** (T-422, fase 2; montados pela API, a tela mostra como vêm):
    - **Rótulo:** "Referência FIPE · outubro de 2026", com o mês do preço; informada em "Colocar à venda", sem versão: "Referência FIPE · informada à mão".
    - **Valor antigo** (a API fora do ar ou a versão fora da tabela): o último valor fica, com o mês dele no rótulo. Atraso de um mês é normal, porque a tabela vira no começo do mês e a rotina leva alguns dias. Com o mês do preço dois ou mais meses antes do mês corrente, aparece o aviso "Esta referência é de agosto de 2026 e não foi atualizada.".
    - **Versão escolhida, preço ainda não trazido** (e o veículo que ainda não passou pela rotina): "A referência FIPE chega na próxima atualização, feita de madrugada.".
    - **Sem versão escolhida** (mais de uma serve): para quem escolhe (administrador e gerente), "Escolha a versão FIPE para ver a referência."; para os outros, "Falta escolher a versão FIPE. O gerente ou o administrador escolhe.".
    - **Versão não encontrada:** para quem escolhe, "Versão FIPE não encontrada. Escolha a versão ou digite o código."; para os outros, "Versão FIPE não encontrada. O gerente ou o administrador escolhe a versão ou digita o código.".
    - **Validação do cadastro:** "Escolha uma versão da lista FIPE." e "Digite o código FIPE no formato 811134-0.".
    - **Consulta por placa indisponível** (desligada, cota esgotada, limite do dia, placa não achada ou API fora do ar): sem erro, como decidiu o dono; depois de "Buscar pela placa", a tela mostra, em tom de informação, "A busca pela placa não está disponível agora. Preencha pelo CRLV-e ou escolha a versão na lista FIPE.". O motivo não aparece para a pessoa.
- `VEN-02` Desconto até 5% o vendedor dá sozinho; acima de 5% a venda vai para `aguardando_aprovacao` e o gerente aprova ou recusa pelo celular (`APR-01`). Ex.: VEN-0177, CB 300F, R$ 22.900 com 8% = R$ 21.068.
- `VEN-03` Formas: à vista (Pix ou TED), entrada + parcelas (boleto ou Pix mensal, gera contas a receber), financiamento pelo banco parceiro (venda fica em `negociacao` até o banco aprovar).
- `VEN-04` Parcelas: saldo ÷ número de parcelas, sem juros por padrão; juros configuráveis por empresa. Ex.: R$ 21.068 − R$ 5.000 = R$ 16.068 em 12 × R$ 1.339.
- `VEN-05` Troca: o veículo do cliente entra com valor de avaliação, abate do preço e é cadastrado na frota como `indisponivel` até a vistoria. Se o chassi já existe na empresa (veículo vendido antes), o cadastro é reaproveitado (`VEI-07`).
- `VEN-06` Ao virar `vendida`: gera o contrato de compra e venda, cria as parcelas em contas a receber, o veículo vai para `vendido` e sai de todos os indicadores da frota, e a comissão do vendedor é lançada (`FIN-09`).
- `VEN-07` Venda `vendida` pode ser cancelada (desistência dentro do prazo legal) só por gerente ou administrador, com motivo obrigatório e evento de auditoria. Ao cancelar: parcelas em aberto vão para `cancelada`, parcelas pagas são estornadas, a comissão vai para `estornada` (`FIN-09`) e o veículo volta de `vendido` para `a_venda`. Antes de `vendida`, desistência é `perdida`.
- `VEN-08` Funil do mês na lista e no início da vendedora: interessados, proposta, negociação, vendido. Conversão = vendidas ÷ interessados dos últimos 30 dias.
- `VEN-09` Meta de vendas por vendedor e mês (valor em R$), definida pelo gerente. A barra mostra vendido ÷ meta.
- `VEN-10` Uma venda aberta por veículo (`proposta`, `negociacao` ou `aguardando_aprovacao`); `interessado` não conta. Quando o veículo vira `vendido`, os outros registros `interessado` dele vão para `perdida` com o motivo "veículo vendido".
- `VEN-11` **Venda da quitação** (`LOC-16`). Na quitação da locação com intenção de compra, o sistema cria sozinho uma venda já `vendida` (única exceção ao "só vende veículo `a_venda`": o veículo está `alugado`), de R$ 0,00, ligada à locação: cliente e veículo da locação, filial da locação, vendedor de quem criou a locação, data da quitação, a descrição "Quitação da LOC-x". Não passa por proposta nem negociação, não gera contrato de compra e venda (o documento do negócio é o contrato da locação), não cria contas a receber nem comissão (`FIN-09`), e fica fora do funil, da conversão e da meta (`VEN-08`, `VEN-09`). O resto da `VEN-06` vale: o veículo vai para `vendido` e sai dos indicadores da frota. Ela não é cancelada pela `VEN-07` (409, "A venda da quitação de uma locação não se cancela."): a quitação não se desfaz pela tela. Registrar a transferência duas vezes também é recusado (409, "A transferência desta venda já foi registrada."). Aparece na lista de vendas com o rótulo "Quitação de locação" e no histórico do veículo. A tarefa da transferência no Detran vai aos gerentes ativos da filial e aos administradores ativos da empresa, sempre (`LOC-16`, decisão do dono de 12 nov 2026).

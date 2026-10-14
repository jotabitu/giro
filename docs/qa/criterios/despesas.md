# Despesas (decisões da T-167) · critérios de aceite

**Regras:** FIN-05, FIN-06, FIN-16, AUD-07, APR-03, APR-07, APR-09, FIN-07 · **Contrato:** `docs/api/financeiro.md` (Despesas) e `docs/api/auditoria.md` (Exportação), a ajustar pelo arquiteto · **Tela:** Despesas (desktop e celular) · **Decisão:** dono do produto, 13 out 2026 (T-176)

As tarefas de código destes critérios ainda não têm número (propostas em `tarefas/backlog.md`, "Propostas da T-176"). Quando tiverem, cada critério leva o número da tarefa que o cobre. Seed Moto Rápida em 07 out 2026, Filial Centro, as 6 despesas de outubro (caso "Despesas de outubro") e 86 veículos, nenhum `vendido` nem `baixado`. Fuso `America/Sao_Paulo`. O nome do teste leva o código da regra (`test_fin_16_...`).

## Indicadores (`FIN-16`)

**CA-DES-01 · Despesa por veículo de outubro**
Dado a Lúcia (financeiro) com `X-Filial` da Filial Centro, quando faz `GET /api/financeiro/despesas/?mes=2026-10`, então `indicadores` traz `gasto_mes_centavos` 706670 e o indicador da despesa por veículo 8217 (706670 ÷ 86 = 8217,09, arredondado uma vez). A tela mostra "R$ 82,17".

**CA-DES-02 · Recusada e veículo vendido ficam de fora**
Dado o mesmo mês, quando os pneus (R$ 1.200,00) são recusados e um veículo da filial vai para `baixado`, então o gasto vai para 586670 e a despesa por veículo para 6902 (586670 ÷ 85, exato). A tela mostra "R$ 69,02".

**CA-DES-03 · Sem veículos**
Dado uma filial sem nenhum veículo fora de `vendido` e `baixado`, com uma despesa no mês, quando a lista é pedida, então o indicador da despesa por veículo vem vazio (sem número) e a tela não mostra valor nem zero.

## Busca (`FIN-16`)

**CA-DES-04 · Busca pela descrição**
Dado a Lúcia em outubro, quando busca "pneu", então a lista traz só "Pneus (2 unidades)" (R$ 1.200,00); as contagens das abas ficam aguardando 1, a pagar 0, pagas 0; os indicadores continuam R$ 7.066,70 e aguardando aprovação 1 (R$ 1.200,00).

**CA-DES-05 · Busca pela placa, com hífen e sem acento**
Quando busca "pmz-3e17", então traz só os pneus (veículo PMZ3E17). Quando busca "ROE", então traz só "IPVA ROE-2A88" (R$ 186,40, A pagar). Quando busca "oleo", então traz só "Óleo 1 litro".

## Exportar (`FIN-16`, `AUD-07`)

**CA-DES-06 · Exportação de outubro**
Dado a Mariana (administradora) na tela de outubro da Filial Centro, quando clica em "Exportar", então nasce uma exportação `na_fila` que fica `pronta` em segundo plano, o link chega por e-mail e vale 7 dias, e "Exportações recentes" mostra "Despesas · 01/10/2026 a 31/10/2026" (texto final no contrato). O CSV tem 6 linhas, uma por despesa, somando R$ 7.066,70, com data, descrição, categoria, veículo, filial, valor, vencimento, situação, pago em, forma e quem lançou. O veículo sai pela placa com hífen: a linha dos pneus traz PMZ-3E17, a do óleo QXA-4B21; as despesas sem veículo saem com o campo vazio.

**CA-DES-06b · O financeiro exporta**
Dado a Lúcia (financeiro) na mesma tela, quando clica em "Exportar", então a exportação nasce igual à da Mariana, o link chega no e-mail dela, e ela baixa o arquivo pela rota de baixar (com o evento `exportacao.baixar`). A Lúcia continua sem exportar a auditoria (403) e sem a tela `Admin-Exportar`.

**CA-DES-07 · A busca e a aba não mudam o arquivo**
Com a busca "pneu" e a aba "Pagas" escolhidas, o CSV continua com as 6 linhas do mês.

**CA-DES-08 · Só o administrador e o financeiro exportam**
Dado o Rodrigo (gerente), a Bruna (vendedora) ou o João (vistoriador), então a tela não mostra "Exportar" e o pedido direto à API é recusado (403). A tela `Admin-Exportar` continua só com a auditoria.

**CA-DES-09 · Recusada sai no arquivo**
Com os pneus recusados, o CSV continua com 6 linhas, e a dos pneus traz a situação recusada.

## Lançamento (`FIN-05`, `FIN-06`)

**CA-DES-10 · Vencimento**
Dado a Lúcia, quando abre "Nova despesa" com a data 06 out, então o vencimento começa em 06 out; ela muda para 10 out e lança a conta de luz (R$ 412,30), que nasce `a_pagar` com vencimento 10 out ("Vence 10 out").

**CA-DES-11 · Pago no caixa com caixa aberto**
Dado a Bruna (vendedora) com o caixa da Filial Centro aberto, quando lança "Óleo 1 litro", R$ 48,00, com nota, marcando "Já paguei em dinheiro, pelo caixa", então a despesa nasce `paga`, forma dinheiro, "Pago · caixa", e o caixa ganha uma saída de R$ 48,00 em dinheiro.

**CA-DES-12 · Pago no caixa sem caixa aberto**
Dado o caixa da filial fechado (ou não aberto hoje), quando a Bruna lança o mesmo óleo marcando o caixa, então recebe 422 `FIN-07` "Abra o caixa do dia para pagar por ele", nenhuma despesa é gravada e o caixa não muda.

**CA-DES-13 · Pago no caixa acima de R$ 500**
Dado a Mariana com o caixa aberto, quando lança uma despesa de R$ 600,00 marcando o caixa, então recebe 422 `APR-03` e nada é gravado. Sem marcar o caixa, a mesma despesa nasce `aguardando_aprovacao`.

**CA-DES-14 · Quem não opera caixa não vê o campo**
Dado o João (vistoriador), quando abre o formulário, então não vê "Já paguei em dinheiro, pelo caixa", e o pedido com `pago_no_caixa` é recusado (403).

**CA-DES-15 · Nota obrigatória**
Dado qualquer perfil que lança, quando envia uma despesa sem nota, então recebe 400 `validacao` no campo `nota`, nada é gravado, e a tela mostra o campo "Foto da nota" como obrigatório.

## Detalhe: pagar, aprovar e recusar (`FIN-05`, `APR-03`, `APR-07`, `APR-09`)

**CA-DES-16 · Aprovar pelo detalhe**
Dado o Rodrigo (gerente), quando abre os pneus pela linha e aprova, então a despesa vai para `a_pagar`, o indicador "Aguardando aprovação" vai para 0 (R$ 0,00), e o pedido some do início dele e de `Aprovações`.

**CA-DES-17 · Quem lançou não decide**
Dado a Mariana, quando abre a despesa de R$ 600,00 que ela mesma lançou, então não vê Aprovar nem Recusar (`APR-09`); o Rodrigo vê os dois.

**CA-DES-18 · Recusar exige motivo**
Dado o Rodrigo, quando recusa os pneus sem motivo, então a tela não envia e pede o motivo; com o motivo, a despesa vai para `recusada` e sai do gasto do mês (R$ 5.866,70).

**CA-DES-19 · Pagar**
Dado a Lúcia, quando abre a conta de luz (`a_pagar`) e paga por Pix em 10 out, então a despesa fica `paga`, com a situação que a API devolve para Pix. O Rodrigo e a Bruna não veem Pagar; na despesa `aguardando_aprovacao`, ninguém vê Pagar.

# Aprovações: números da tela (decisões da T-190) · critérios de aceite

**Regras:** APR-12, APR-01, APR-08, APR-09, USR-07 · **Contrato:** `docs/api/aprovacoes.md`, a ajustar pelo arquiteto (indicadores, contagens por aba e o bloco `resumo` por tipo) · **Tela:** Aprovacoes (desktop e celular) · **Decisão:** dono do produto, 14 out 2026 (T-190, D12)

As tarefas de código ainda não têm número (propostas em `tarefas/backlog.md`, seção da T-190). Seed Moto Rápida em 07 out 2026, Filial Centro, caso "Números da tela Aprovações em 07 out" dos dados de referência: aluguel do ponto (Lúcia, pedido 05 out 08:30, aprovado por Rodrigo 09:10) e rastreadores (Lúcia, pedido 02 out 10:00, aprovado por Rodrigo 12:20); pendentes os pneus (João) e o encerramento da LOC-2812 (Bruna). Fuso `America/Sao_Paulo`. O nome do teste leva o código da regra (`test_apr_12_...`).

**CA-APR-01 · Números do seed**
Dado o Rodrigo (gerente) na Filial Centro em 07 out, quando abre `Aprovações`, então vê Aprovadas em outubro 2, tempo médio "1 h 30 min" ((40 + 140) ÷ 2 = 90 min), Recusadas em outubro 0, Descontos aprovados R$ 0,00 em 0 pedidos, Esperando você 2, e as abas Pendentes 2, Aprovadas 2, Recusadas 0. A Mariana (administradora) vê os mesmos números.

**CA-APR-02 · Desconto aprovado**
Dado o seed, quando a Bruna pede 8% de desconto numa locação semanal Street em 08 out 09:00 (tabela R$ 329,00, com desconto R$ 302,68) e o Rodrigo aprova às 09:40, então em 08 out: Aprovadas 3, tempo médio "1 h 13 min" ((40 + 140 + 40) ÷ 3 = 73,3 min, arredondado para o minuto), Descontos aprovados R$ 26,32 em 1 pedido.

**CA-APR-03 · Recusado**
Quando, em seguida, o Rodrigo recusa os pneus com motivo, então Recusadas 1, Esperando você 1, aba Recusadas 1, e o tempo médio não muda (só conta aprovados).

**CA-APR-04 · Cancelado não conta**
Quando a Bruna pede outro desconto e cancela o pedido antes da decisão, então nenhum número muda: o pedido não entra em Esperando você, Aprovadas, Recusadas nem Descontos aprovados; ele aparece só em "Meus pedidos" da Bruna, como cancelado.

**CA-APR-05 · Os pedidos da própria pessoa ficam de fora**
Dado o Rodrigo com uma diferença de caixa (`APR-04`) pedida por ele em 08 out e aprovada pela Mariana, então os números do Rodrigo não contam esse pedido, e ele aparece em "Meus pedidos" dele; os números da Mariana contam (Aprovadas 1 a mais).

**CA-APR-06 · Mês pela data da decisão**
Dado um pedido feito em 30 set e aprovado em 01 out, então ele entra em Aprovadas de outubro. Um pedido aprovado em 30 set não entra. Pendentes de setembro ainda sem decisão entram em Esperando você.

**CA-APR-07 · Sem aprovados**
Dado uma filial sem pedido aprovado no mês, então Aprovadas é 0 e o tempo médio vem vazio (sem número e sem "0 min").

**CA-APR-08 · Filial do seletor**
Dado a Mariana com "Todas as filiais", então os números somam as filiais dela; com uma filial escolhida, só os dessa filial (`USR-07`).

**CA-APR-09 · Lembrete das 4 horas fora do MVP**
A tela não mostra a frase do aviso ao administrador depois de 4 horas úteis (`APR-08`, fase 2).

**CA-APR-10 · Células do pedido de desconto**
Dado o pedido de desconto do CA-APR-02, então o detalhe mostra os valores vindos da API, sem conta na tela: preço de tabela R$ 329,00, com desconto R$ 302,68, desconto R$ 26,32 (8%) e "O limite de Bruna é 5%." (sem artigo: a API não sabe o gênero de ninguém, como em "A devolver").

**CA-APR-11 · Células do pedido de despesa**
Dado o pedido dos pneus (João, 07 out, R$ 1.200,00, PMZ-3E17, vencimento 07 out), então o detalhe mostra categoria Manutenção, descrição "Pneus (2)", veículo PMZ-3E17, valor R$ 1.200,00 e vencimento 07 out, e não mostra "Fornecedor" nem a forma de pagamento: a despesa não tem fornecedor e só ganha a forma ao ser paga (`APR-03`, `FIN-05`; decisão do dono de 15 out 2026, T-235).

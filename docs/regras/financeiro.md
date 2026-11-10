# Financeiro

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

Todo dinheiro que entra ou sai passa por uma conta a receber, uma despesa ou um movimento de caixa, e todo pagamento aponta para a origem (locação, venda, OS, despesa). Telas: `Receber`, `Despesas`, `Caixa`, `Conciliacao`, `Comissoes`, `Relatorios`, `Financeiro` (início da financeira).

**Contas a receber**

- `FIN-01` Estados: `aberta`, `vence_hoje`, `atrasada`, `paga`, `cancelada`, `renegociada`. Pagamento parcial não existe: ou paga a parcela inteira ou renegocia.
- `FIN-02` Faixas de atraso para a tela: 1–7 dias, 8–30 dias, mais de 30 dias.
- `FIN-03` Juros e multa por atraso configuráveis por empresa, com teto: multa de até 2% (CDC, art. 52, §1º) e juros de mora de até 1% ao mês, pro rata dia (mês de 30 dias: juros = valor × taxa ao mês ÷ 30 × dias corridos de atraso, contados do dia seguinte ao vencimento até o dia do pagamento; a multa é cobrada uma vez, a partir de 1 dia de atraso). Padrão: 2% + 1% ao mês. Calculados na hora do pagamento e escritos no contrato (sem cláusula no contrato, não cobra juros).
  - **Conta que nasce vencida:** quando a conta nasce depois do próprio vencimento (ex.: locação confirmada depois do início, com as contas nascendo na confirmação), o atraso para multa e juros conta a partir do dia seguinte ao dia em que ela nasceu, e não do dia seguinte ao vencimento. Dias de atraso = dia do pagamento − o mais tarde entre o vencimento e o dia em que a conta nasceu, em datas de `America/Sao_Paulo`. Paga no dia em que nasceu, não tem multa nem juros. Só a cobrança muda: o vencimento gravado, o estado e as faixas seguem a `FIN-01` e a `FIN-02`. Ex.: parcela 1 da LOC-2836 (R$ 329,00, vence 30 set, nasce na confirmação em 01 out): paga em 01 out, multa 0 e juros 0 (total pago R$ 958,00, `LOC-06`); paga em 02 out, 1 dia: multa R$ 6,58 e juros R$ 0,11.
  - **Conta da locação antes da retirada** (T-410): nada vence antes da retirada (`LOC-05`). Na conta da locação, o dia da retirada entra na mesma conta: dias de atraso = dia do pagamento − o mais tarde entre o vencimento, o dia em que a conta nasceu e o dia da retirada. Como a 1ª parcela e a caução são o 1º pagamento, pagas até a retirada, elas nunca têm multa nem juros. Na LOC-2836, o "paga em 02 out" do exemplo acima não acontece mais, porque a parcela 1 é paga na retirada, em 01 out; os números ficam só como exemplo da fórmula.
- `FIN-04` Pagamento por Pix ou boleto do parceiro baixa a conta sozinho (webhook). Dinheiro e cartão na maquininha são baixados no caixa.
- `FIN-15` Números de contas a receber (tela `Receber`, contador do menu e início `Financeiro`). Entram as contas da filial escolhida, sem caução (`LOC-04`) e sem as `cancelada` e `renegociada` (a renegociação gera contas novas, que entram no lugar). Valores sem multa e juros (`FIN-03`). A receita do painel (`receita_locacao` do administrador e `receita_semana` do gerente, `docs/api/painel.md`) segue a mesma base: soma o valor das contas de locação pagas no período (parcelas e cobranças do acerto, como avaria e multa de encerramento), sem caução e sem a multa e os juros por atraso. Multa e juros pagos entram só na DRE, na linha de multas (`FIN-13`). O período da tela é hoje, semana ou mês: a semana vai de segunda a domingo da semana de hoje, e sem período escolhido vale o mês. A caução não entra nos números: contagens das abas, indicadores e contador do menu. Na lista, ela aparece como as outras contas, na aba da situação dela, com o tipo "Caução" e "Registrar pagamento" (`FIN-18`).
  - **Previsto no mês:** soma e quantidade das contas com vencimento no mês corrente, pagas ou não.
  - **Recebido:** das contas do previsto, as `paga`. O percentual é recebido ÷ previsto, em valor, com 2 casas.
  - **Vence hoje** (no `Financeiro`, "Entra hoje"): contas ainda não pagas com vencimento hoje.
  - **Em atraso:** todas as contas `atrasada`, de qualquer mês, em valor, clientes e parcelas, separadas nas faixas da `FIN-02`.
  - **Abas da lista:** "Em atraso" mostra todas as atrasadas, de qualquer período; "Vencem hoje", "A vencer" e "Pagas" seguem o período escolhido (hoje, semana ou mês), pelo vencimento; "Todas" é a soma das quatro abas.
  - **Contador "Contas a receber" do menu:** quantidade de parcelas `atrasada`, o mesmo número da aba "Em atraso" (chave `receber` de `GET /api/painel/contadores/`). Conta parcelas, não clientes: um cliente com 2 parcelas atrasadas conta 2. Seed em 07 out: 2 (Carlos e Rafael).

**Contas a pagar e despesas**

- `FIN-05` Estados: `aguardando_aprovacao`, `a_pagar`, `paga`, `recusada`. Despesa acima de R$ 500 nasce `aguardando_aprovacao` (`APR-03`); até R$ 500 nasce `a_pagar` (ou `paga`, se lançada como paga no caixa).
  - **Vencimento:** toda despesa tem data e vencimento (dia sem hora). No lançamento, o vencimento começa igual à data e pode ser mudado. Ex.: conta de luz lançada em 06 out, vence em 10 out.
  - **Paga no caixa** ("Já paguei em dinheiro, pelo caixa"): só para quem abre e fecha caixa (tabela de perfis), só até R$ 500 e só com o caixa do dia da filial `aberto`. A despesa nasce `paga`, em dinheiro, com uma saída no caixa (`FIN-07`). Acima de R$ 500, o lançamento como pago é recusado (`APR-03`): a despesa precisa ser aprovada antes de ser paga. Sem caixa aberto, é recusado com "Abra o caixa do dia para pagar por ele" (`FIN-07`). Nos dois casos, nada é gravado. Ex.: óleo de R$ 48,00 lançado pela Bruna com o caixa aberto, "Pago · caixa".
  - **Suporte Giro:** mesmo em "ver e editar", o suporte não lança despesa, nem pela tela `Despesas` nem paga no caixa: recebe 403 `PLT-07` antes de a nota ser lida e de o formulário ser conferido, e nada é gravado (`PLT-07`).
  - **Pagar, aprovar e recusar** ficam no detalhe da despesa, aberto pela linha da lista na tela `Despesas`. Pagar é do administrador e do financeiro, só em `a_pagar`, com a forma, o dia e o comprovante (opcional). Aprovar e recusar são de quem aprova a `APR-03`, nunca de quem lançou, salvo o administrador (`APR-09`), e recusar exige motivo (`APR-07`). O mesmo pedido pode ser decidido também no início do gerente e na tela `Aprovações`: é um pedido só, e quem decide primeiro fecha o pedido.
- `FIN-06` Categorias, em dois grupos, nesta ordem na tela:
  - **Do veículo:** IPVA e licenciamento, seguro, multa de trânsito, peças, combustível, manutenção (o serviço da oficina, a mão de obra), rastreamento.
  - **Da empresa:** fixas (aluguel, luz, internet), impostos (os da empresa, como Simples e ISS; o IPVA vai em "IPVA e licenciamento"), pessoal, outros.
  - O grupo só organiza a escolha: qualquer categoria pode ser ligada a um veículo, e nenhuma exige veículo (um seguro ou rastreamento da frota inteira entra sem veículo, como os "Rastreadores (86)" do seed). As despesas já lançadas não mudam de categoria. Multa de trânsito é o que a locadora pagou ao órgão de trânsito; cobrar do cliente continua sendo um lançamento avulso em contas a receber (tabela de perfis), feito à parte.
  - O vistoriador lança só manutenção e peças.
  - **Nota e veículo:** despesa pode ser ligada a um veículo (entra no custo dele, `VEI-05`) e deve ter foto da nota: a nota (imagem ou PDF) é obrigatória ao lançar pela tela `Despesas` e pela ficha do veículo (`FIN-17`), e sem ela a despesa não é gravada. A despesa que nasce da OS concluída (`MAN-05`) segue as regras da manutenção (fase 2).
- `FIN-16` Números da tela `Despesas`. Entram as despesas da filial escolhida (de todas, para quem vê todas as filiais), com data no mês escolhido, sem as `recusada`.
  - **Gasto no mês:** soma do valor dessas despesas, pagas ou não. Seed, outubro na Filial Centro: R$ 7.066,70.
  - **Despesa por veículo:** gasto no mês ÷ veículos da filial fora de `vendido` e `baixado`, contados no último dia do mês (no mês corrente, hoje), com o mesmo recorte de filial do gasto. Arredondada uma vez para o centavo, meio centavo para cima, e mostrada com os centavos, como todo valor. Sem nenhum veículo, o indicador fica sem número. Ex.: outubro na Filial Centro, R$ 7.066,70 ÷ 86 = R$ 82,17. É um indicador de acompanhamento: o custo de cada veículo continua sendo o da ficha (`VEI-05`), com as despesas ligadas a ele.
  - **Busca:** procura na descrição e na placa do veículo ligado, sem diferenciar maiúsculas, minúsculas e acentos, e sem o hífen da placa, dentro do mês e da filial da tela. Muda a lista e as contagens das abas (como em contas a receber), mas não os indicadores, que são sempre os do mês e da filial. Ex.: "pneu" e "pmz-3e17" trazem só os pneus; "ROE" traz só o IPVA.
  - **Exportar:** o administrador e o financeiro exportam as despesas do mês e da filial da tela em CSV, pelo mesmo fluxo da exportação da auditoria (`AUD-07`): o arquivo fica pronto em segundo plano, o link chega por e-mail e vale 7 dias, e a exportação aparece em "Exportações recentes". O financeiro baixa só as exportações de despesas; as outras (auditoria) continuam só do administrador. Sai uma linha por despesa do mês, em qualquer situação (as `recusada` também, com a situação), sem a busca e sem a aba escolhidas. Colunas: data, descrição, categoria, veículo, filial, valor, vencimento, situação, pago em, forma e quem lançou. O veículo sai pela placa com hífen, como nas telas (PMZ-3E17). Ex.: outubro na Filial Centro, 6 linhas somando R$ 7.066,70.
  - **Filtro por veículo:** a tela tem o filtro "Veículo" (pela placa), ao lado do de categoria. Como o filtro de situação e o de categoria, muda a lista, mas não as contagens das abas nem os indicadores. Ex.: outubro na Filial Centro, veículo PMZ-3E17 → só os pneus.
- `FIN-17` **Despesas do veículo na ficha** (tela `Veiculo`).
  - **Quem vê:** a lista e o total só aparecem para administrador, gerente e financeiro, os mesmos que veem o custo do veículo (`VEI-05`, `USR-09`). Para vendedor e vistoriador, a API não manda a lista, e a ficha não mostra a seção.
  - **O que entra:** as despesas ligadas ao veículo com data no ano escolhido (padrão: o ano de hoje), de qualquer filial (o veículo pode ter sido transferido, `VEI-04`), inclusive as `recusada`, com a situação. Da mais nova para a mais antiga, 20 por página. Cada linha mostra data, descrição, categoria, valor e situação, e abre o detalhe da despesa (`FIN-05`), onde ficam a nota e o comprovante.
  - **Total:** "Despesas no ano" soma o valor das despesas da lista, pagas ou não, sem as `recusada`. É o mesmo valor que o "Rendeu no ano" desconta (`VEI-05`). Ex.: QXA-4B21 em 07 out 2026, R$ 48,00 (o óleo).
  - **"Lançar despesa":** aparece para quem lança despesa (tabela de perfis), mesmo sem ver a lista. Abre o lançamento da `FIN-05` com o veículo preenchido e travado, as categorias do veículo primeiro (as do vistoriador, só manutenção e peças) e a filial do veículo, que pode não ser a da tela. Todo o resto da `FIN-05` e da `FIN-06` vale: nota obrigatória, aprovação acima de R$ 500 (`APR-03`), pago no caixa só até R$ 500 e com o caixa da filial do veículo aberto.
  - A despesa que nasce da OS concluída (`MAN-05`) e a da parada de movimentação (`MOV-04`) entram na lista como as outras, porque já nascem ligadas ao veículo.
- `FIN-18` **Caução: onde se recebe e como se dá baixa** (`LOC-04`, `LOC-17`).
  - **É uma conta a receber da locação**, do tipo caução. Nasce na confirmação, junto com as parcelas, pelo valor da categoria, com o vencimento da 1ª parcela. Antes da retirada, nunca atrasa (`LOC-05`).
  - **Onde aparece para receber** (sempre com o rótulo "Caução" e, com ela em aberto, "Registrar pagamento" para quem recebe no caixa, pela tabela de perfis):
    - na seção Pagamentos da ficha da locação, como uma linha ao lado das parcelas ("Caução · R$ 300,00 · Em aberto");
    - na tela `Receber`, na lista, como as parcelas, mas fora dos números (`FIN-15`);
    - na busca do `Caixa` por cliente ou locação.
  - **Como se dá baixa:** como uma parcela.
    - Em dinheiro ou cartão na maquininha, pelo "Registrar pagamento", que lança a entrada no caixa aberto (`FIN-04`, `FIN-07`).
    - Por Pix ou boleto do parceiro, o webhook baixa sozinho.
    - Paga-se inteira, sem pagamento parcial (`FIN-01`), e sem multa nem juros antes da retirada (`FIN-03`).
    - A baixa vale para o 1º pagamento da `LOC-17`, junto com a 1ª parcela.
  - **Não é receita.** A caução paga entra no caixa do dia ("entrou hoje"), mas não na receita, na DRE nem nos números de contas a receber (`FIN-13`, `FIN-15`). Fica como valor a devolver até o acerto da devolução, que a usa (`DEV-02`).
  - **Ex.: LOC-2856** (Lucas, 07 out): "Caução · R$ 300,00 · Paga em 07 out", recebida em dinheiro no caixa de 07 out junto com a 1ª semana (R$ 629,00, caso "Caixa de 07 out").
  - **Seção Pagamentos da ficha da locação** (`LOC-17`): lista as parcelas e a caução, cada uma com o rótulo ("Parcela 1", "Caução"), o vencimento, o valor de hoje e a situação. Cada conta em aberto tem "Registrar pagamento" para quem recebe no caixa. Ele abre a mesma baixa de `Receber` sem sair da locação, e depois só a ficha se atualiza.

**Caixa do dia**

- `FIN-07` Um caixa por filial por dia. Abre com o troco (ex.: R$ 200,00); registra entradas por forma (Pix, cartão, dinheiro), saídas e sangrias. No fechamento a pessoa conta o dinheiro; o sistema compara com "deve ter na gaveta" = troco + entradas em dinheiro − saídas em dinheiro. Diferença exige motivo e avisa o gerente. Ex.: 200 + 629 − 548 = R$ 281,00. Abrir e fechar o caixa é de quem trabalha na empresa: o suporte Giro, mesmo em "ver e editar", vê o caixa e não abre nem fecha (403 `PLT-07`).
- `FIN-08` Caixa não fechado até 23h59 fecha sozinho com status `fechado_sem_conferencia` e gera tarefa para o gerente.

**Comissões**: **fase 2**, com a tela `Comissoes` e a `AUT-10` (decisão do dono do produto em 25 out 2026, T-356). No MVP, nenhuma comissão é lançada nem mostrada, nem a de locação. A locadora paga as comissões por fora, como fazia antes do sistema.

- `FIN-09` Regras padrão (configuráveis): 3% do preço final em vendas; R$ 16,00 por locação nova; renovação não gera comissão. Comissão de venda nasce `pendente` quando a venda espera aprovação, fica `confirmada` quando vira vendida, `paga` no dia 5 do mês seguinte e `estornada` se a venda for cancelada. Comissão de locação nasce `pendente` quando a locação é confirmada, fica `confirmada` quando a locação fica `ativa`, `paga` no dia 5 do mês seguinte e `estornada` se a locação for cancelada antes da retirada; o encerramento antecipado não a estorna. No plano Essencial, sem o módulo de comissões, não há comissão (`PLT-12`).
- `FIN-10` Exemplo outubro, Bruna: 4 vendas (R$ 31.200 × 3% = R$ 936,00) + 2 locações (R$ 32,00) = R$ 968,00 confirmados; R$ 632,04 da CB 300F pendentes.

**Conciliação bancária**

- `FIN-11` O extrato é importado (integração ou arquivo OFX). Para cada linha o sistema sugere um par por valor e data (±3 dias) e nome do pagador. A pessoa confirma, cria o lançamento que falta ou ignora.
- `FIN-12` Diferença entre saldo do banco e do sistema = soma das linhas sem par. Ex.: +R$ 150,00 (Pix sem lançamento) − R$ 12,90 (tarifa) = R$ 137,10.

**Relatórios e DRE**: **fase 2**, com a tela `Relatorios` (decisão do dono do produto em 25 out 2026, T-356). No MVP, os números do dia a dia ficam nos inícios por perfil e nas telas `Receber`, `Despesas` e `Caixa`.

- `FIN-13` DRE simplificada por mês e filial: receita de locações + multas, extras e avarias − taxas de pagamento = receita líquida; − despesas − comissões = resultado. Caução não entra como receita. Venda de veículo entra em linha separada (receita de venda − valor contábil do veículo).
- `FIN-14` Relatórios prontos (planilha e PDF): DRE, locações por cliente, rentabilidade por veículo, inadimplência por faixa, comissões, manutenções por veículo e oficina.

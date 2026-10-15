# Assinatura, planos, cancelar e pausar (decisões da T-190) · critérios de aceite

**Regras:** PLT-01, PLT-02, PLT-03, PLT-04, PLT-05, PLT-06, PLT-11, PLT-12, PLT-13, PLT-14, PLT-15, AUT-03, AUT-13, AUD-08, tabela de estados da empresa · **Contrato:** `docs/api/assinatura.md` (T-183), a ajustar pelo arquiteto; cancelar e pausar ainda sem contrato · **Telas:** Admin-Assinatura, Admin-Cancelar, Compra-Planos, Compra-Checkout, Plat-Planos (desktop e celular) · **Decisão:** dono do produto, 14 out 2026 (T-190; pontos em aberto e `[decisão]` da T-193 resolvidos na T-211, CA-ASS-40 a 48; reativação no período pago na T-216, CA-ASS-49)

As tarefas de código destes critérios ainda não têm número (propostas em `tarefas/backlog.md`, seção da T-190); as que já existem (T-184 a T-189) estão citadas onde se aplicam. Quando tiverem número, cada critério leva o número da tarefa que o cobre. Seed Moto Rápida: plano Profissional mensal, teste de 07 a 21 out 2026, compra sem cartão, 86 veículos, 1 filial, 5 usuários, Mariana Costa administradora. Fuso `America/Sao_Paulo`, relógio de referência (ADR 0021). O nome do teste leva o código da regra (`test_plt_04_...`).

## Teste e 1ª fatura (`PLT-01`, tabela de estados)

**CA-ASS-01 · 1ª fatura no dia seguinte ao fim do teste**
Dado a Moto Rápida no seed, quando a Mariana abre a assinatura em 07 out, então a empresa está `em_teste` até 21 out e existe a FAT-0001 `aberta`, R$ 449,00, vencendo em 22 out, "Plano Profissional · 22 out a 21 nov". A tela mostra "R$ 449,00 por mês, a partir de 22 out" (não 21 out).

**CA-ASS-02 · Escolher a forma não ativa a empresa**
Dado a Moto Rápida em 10 out, quando a Mariana escolhe boleto (ou Pix automático, ou cartão), então a empresa continua `em_teste`, a faixa "Teste grátis até 21 out" continua, e os avisos da `IMP-06` continuam saindo (faltam 3 dias em 18 out).

**CA-ASS-03 · Paga antes, fica em teste até o fim**
Dado a Moto Rápida com boleto, quando a FAT-0001 é paga em 18 out (baixa pelo webhook), então ela fica `paga` em 18 out, a empresa continua `em_teste` até 21 out e vira `ativa` em 22 out, sem nenhuma mensagem da régua depois do pagamento.

**CA-ASS-04 · Paga no vencimento**
Dado a Moto Rápida com boleto e a FAT-0001 em aberto, quando é paga em 22 out, então a empresa vira `ativa` na hora.

**CA-ASS-05 · Com forma e sem pagar**
Dado a Moto Rápida com boleto e a FAT-0001 sem pagamento, então em 23 out a empresa vai para `inadimplente` (faixa de aviso no topo), recebe a régua em 25 out (D+3) e 29 out (D+7, aviso de suspensão) e vai para `suspensa` em 06 nov (D+15). Pagando em qualquer desses dias, volta a `ativa` na hora.

**CA-ASS-06 · Sem forma no fim do teste**
Dado a Moto Rápida sem forma de pagamento em 21 out, então em 22 out ela vai para `suspensa` (só ver e exportar). Quando a Mariana escolhe o boleto e paga a FAT-0001 em 24 out, a empresa volta a `ativa` na hora, e a próxima fatura continua em 22 nov.

**CA-ASS-07 · Faturas seguintes no mesmo dia**
Dado a Moto Rápida `ativa` com a FAT-0001 paga, então as faturas seguintes vencem em 22 nov ("Plano Profissional · 22 nov a 21 dez") e 22 dez, de R$ 449,00 cada.

**CA-ASS-08 · Mês sem o dia**
Dado uma empresa com teste de 16 a 30 jan 2027 (1ª fatura em 31 jan 2027), então as faturas seguintes vencem em 28 fev 2027 (período de 28 fev a 30 mar) e 31 mar 2027.

**CA-ASS-09 · Anual**
Dado uma empresa no Profissional anual com teste até 21 out 2026, então a 1ª fatura é de R$ 4.490,00, vence em 22 out 2026 e paga de 22 out 2026 a 21 out 2027 ("Plano Profissional anual · out 2026 a out 2027"); a seguinte vence em 22 out 2027.

## Régua e emissão (`PLT-02`, `AUT-13`)

**CA-ASS-10 · Boleto 5 dias antes**
Dado a Moto Rápida com boleto, então o boleto (com Pix) da FAT-0001 é criado no parceiro em 17 out e vai por e-mail nesse dia para o e-mail de cobrança e para a Mariana; o lembrete D-3 sai em 19 out. Com Pix automático, a cobrança também é criada em 17 out.

**CA-ASS-11 · Cartão na 1ª fatura**
Dado a Moto Rápida com cartão escolhido no teste, então o Giro não guarda nenhum cartão, a forma mostra "Você cadastra o cartão ao pagar a primeira fatura.", o lembrete de 19 out leva o link da página do parceiro, e "Pagar" abre essa página. Sem o cartão digitado até 22 out, nada é cobrado, e em 23 out a empresa vai para `inadimplente`.

**CA-ASS-12 · Cartão recusado: uma tentativa a mais**
Dado a Moto Rápida `ativa` com cartão guardado, quando a cobrança de 22 nov é recusada, então a fatura mostra "Cartão recusado · nova tentativa amanhã", o cartão é cobrado de novo em 23 nov uma única vez, e a empresa vai para `inadimplente` em 23 nov. Recusado de novo, não há terceira tentativa; a régua segue (25 nov, 29 nov, `suspensa` em 07 dez), e a Mariana pode pagar por Pix ou boleto pelo "Pagar".

## Mudar de plano (`PLT-04`, `PLT-05`)

**CA-ASS-13 · Upgrade no teste**
Dado a Moto Rápida `em_teste`, quando a Mariana muda para o Completo em 10 out, então o plano muda na hora, nada é cobrado, a FAT-0001 passa a R$ 899,00, o teste continua até 21 out, e os limites passam a sem limite.

**CA-ASS-14 · Upgrade proporcional**
Dado a Moto Rápida `ativa`, FAT-0001 paga, quando a Mariana muda para o Completo em 01 nov, então o plano muda na hora e nasce uma fatura de diferença de R$ 304,84 (45000 × 21 ÷ 31 = 30483,87, arredondado uma vez), "Mudança para o plano Completo · 01 a 21 nov", vencendo em 04 nov; no cartão, cobrada na hora. O preço contratado passa a R$ 899,00, e a fatura de 22 nov vem com R$ 899,00. `test_plt_04_upgrade_proporcional`.

**CA-ASS-15 · Downgrade que não cabe**
Dado a Moto Rápida (`em_teste` ou `ativa`), quando a Mariana tenta o Essencial, então é recusado e a tela diz o que passa: 86 de 30 veículos e 5 de 3 usuários (1 filial cabe). Diz também o que está aberto nos módulos que saem (`PLT-12`): 1 despesa aguardando aprovação (os pneus, R$ 1.200,00) e 2 despesas a pagar (IPVA ROE2A88 e conta de luz). O óleo, o aluguel e os rastreadores já estão pagos e não contam. O seed de 07 out não tem OS, venda nem comissão aberta, e esses grupos não aparecem. Nada muda. `test_plt_04_downgrade_nao_cabe`.

**CA-ASS-16 · Downgrade agendado e desfeito**
Dado uma empresa no Completo `ativa` com 86 veículos, 1 filial e 5 usuários, período de 22 out a 21 nov, quando o administrador muda para o Profissional em 01 nov, então nada é cobrado nem devolvido, a tela diz "O plano Profissional vale a partir de 22 nov. Até lá, você continua no Completo.", e a fatura de 22 nov vem com R$ 449,00. Quando ele desfaz em 10 nov, a fatura de 22 nov volta a R$ 899,00. Em 22 nov, sem desfazer, o plano vira Profissional.

**CA-ASS-17 · Estados que não mudam de plano**
Dado a Moto Rápida `inadimplente` (ou `suspensa`), quando a Mariana tenta mudar de plano, então é recusado com "Pague a fatura em atraso antes de mudar de plano." Em `pausada` e `cancelada`, a opção não aparece.

**CA-ASS-18 · Mensal e anual só pelo suporte**
Dado a Moto Rápida mensal, quando a Mariana tenta o Profissional anual pela tela, então é recusado com "Para mudar entre mensal e anual, fale com o suporte.", e a comparação mostra os planos no ciclo mensal.

**CA-ASS-19 · Só o administrador**
Dado o Rodrigo (gerente), a Lúcia (financeiro) ou o suporte Giro dentro da empresa (mesmo com "ver e editar"), quando tentam mudar o plano, a forma de pagamento, os dados fiscais, pagar uma fatura, pausar ou cancelar, então é recusado (403) e a tela não mostra as ações.

## Catálogo e módulos (`PLT-11`, `PLT-12`, `PLT-03`, `AUT-03`)

**CA-ASS-20 · Catálogo único**
Quando `Compra-Planos`, Comparar planos (`Admin-Assinatura`) e `Plat-Planos` listam os planos, então os três mostram Essencial R$ 199,00 (anual R$ 1.990,00, 30/1/3), Profissional R$ 449,00 (R$ 4.490,00, 150/3/10) e Completo R$ 899,00 (R$ 8.990,00, sem limite), com os textos da `PLT-11`. Nenhum dos três cita NF-e, assinatura digital como extra do Completo, domínio próprio, portal do cliente nem API e integrações.

**CA-ASS-21 · Cartão do plano acima**
Dado a Moto Rápida no Profissional, então a `Admin-Assinatura` mostra o cartão "Precisa de mais veículos ou filiais?" com veículos, filiais e usuários sem limite, implantação acompanhada por chamada e suporte prioritário. Dado uma empresa no Completo, o cartão não aparece.

**CA-ASS-22 · Essencial sem os módulos do Profissional**
Dado uma empresa no Essencial que aluga e vende, então o menu do administrador não tem Vendas, Manutenções, Despesas, Comissões, Conciliação nem Relatórios, a API recusa as rotas desses módulos, e o passo 10 da implantação (Recebimentos) não aparece. A régua de cobrança do cliente (`AUT-03`) sai só por e-mail, sem WhatsApp e sem o Pix do parceiro.

**CA-ASS-23 · Dados guardados ao descer e de volta ao subir**
Dado uma empresa no Profissional com 20 veículos, 1 filial, 3 usuários, despesas todas `paga` ou `recusada`, nenhuma OS aberta, venda aberta nem comissão a pagar, quando muda para o Essencial (na virada do período), então Despesas e os outros módulos somem do menu, e as despesas continuam no banco. Quando volta ao Profissional, as despesas aparecem como estavam.

**CA-ASS-24 · Downgrade recusado com módulo aberto**
Dado a mesma empresa com 1 despesa `a_pagar` e 1 OS aberta, quando tenta o Essencial, então é recusado, e a recusa diz quanto falta: 1 despesa a pagar e 1 OS aberta.

**CA-ASS-25 · Adicionais fora**
Dado uma empresa no Profissional com 3 de 3 filiais, quando o administrador tenta uma 4ª filial, então é recusado pelo limite (`PLT-03`), e a tela diz para mudar de plano, sem oferecer filial adicional. Nenhuma tela oferece filial adicional, pacote de 10 veículos ou assinatura digital avulsa.

## Forma de pagamento, faturas e nota (`PLT-13`, `PLT-14`, `PLT-15`)

**CA-ASS-26 · Troca da forma**
Dado a Moto Rápida `ativa` com boleto, quando a Mariana troca para Pix automático em 10 nov e autoriza no banco, então a fatura de 22 nov é cobrada pelo Pix automático (cobrança criada em 17 nov, sem boleto), e a empresa continua `ativa`. Dado a fatura de 22 nov já `atrasada`, quando ela troca a forma, então o "Pagar" dessa fatura passa a usar a forma nova.

**CA-ASS-27 · Suspensa paga**
Dado a Moto Rápida `suspensa` em 22 out (sem forma), quando a Mariana escolhe a forma e paga, então as duas ações são aceitas, embora a empresa esteja só leitura, e ela volta a `ativa` na hora.

**CA-ASS-28 · Lista de faturas**
Dado a Moto Rápida `ativa` em 05 nov, depois do upgrade de 01 nov, então a lista traz a fatura de diferença (R$ 304,84, vence 04 nov, conforme paga ou não) e a FAT-0001 (`paga`, "Paga em 22 out", com o recibo do parceiro); a aberta ou atrasada tem "Pagar".

**CA-ASS-29 · Nota fiscal e CNPJ**
Dado a FAT-0001 paga, então o Giro emite a NFS-e para Moto Rápida Locações Ltda, CNPJ 12.345.678/0001-95, Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza, CE, CEP 60325-000 (CA-ASS-47), enviada ao e-mail de cobrança (enquanto o cadastro municipal do Giro não estiver pronto, este critério fica `xfail` e o bloco só guarda os dados). Quando a Mariana troca o e-mail de cobrança para financeiro@motorapida.com.br, a próxima fatura, a régua e a nota vão para ele. Quando tenta trocar o CNPJ, é recusado com "O CNPJ não muda por aqui. Fale com o suporte."

## Cancelar e pausar (`PLT-06`, `AUD-08`)

**CA-ASS-30 · Cancelar no teste**
Dado a Moto Rápida `em_teste`, quando a Mariana cancela em 10 out (motivo escolhido e "Moto Rápida" digitado), então a tela mostra acesso até 21 out e nenhuma cobrança futura; a FAT-0001 vira `cancelada`; a empresa opera normalmente até 21 out e vira `cancelada` em 22 out; o aviso do apagamento sai em 13 jan 2027 e os dados são apagados em 20 jan 2027.

**CA-ASS-31 · Nome errado**
Quando a Mariana digita outro nome, o botão "Cancelar assinatura" não confirma e nada muda.

**CA-ASS-32 · Cancelar ativa**
Dado a Moto Rápida `ativa`, FAT-0001 paga, quando cancela em 05 nov, então o acesso continua até 21 nov, nenhuma fatura vence em 22 nov, a empresa vira `cancelada` em 22 nov, e os dados são apagados em 20 fev 2027. Cancelando em 19 nov, depois de emitida a fatura de 22 nov, essa fatura vira `cancelada`.

**CA-ASS-33 · Cancelar anual**
Dado uma empresa no anual de 22 out 2026 a 21 out 2027, quando cancela em 05 nov 2026, então nada é devolvido e o acesso vai até 21 out 2027.

**CA-ASS-34 · Cancelar inadimplente**
Dado a Moto Rápida `inadimplente` em 25 out, com a FAT-0001 atrasada, quando a Mariana cancela, então a empresa vira `cancelada` na hora, a FAT-0001 continua `atrasada` e devida, e a régua para: nada sai em 29 out (D+7) nem em 06 nov.

**CA-ASS-35 · Pausar**
Dado a Moto Rápida `ativa`, FAT-0001 paga, quando a Mariana pausa por 2 meses em 05 nov, então a empresa continua `ativa` até 21 nov, fica `pausada` (só leitura) de 22 nov a 21 jan 2027 sem nenhuma fatura, e volta sozinha a `ativa` em 22 jan 2027 com uma fatura de R$ 449,00 vencendo nesse dia. Pausar por 4 meses é recusado.

**CA-ASS-36 · Volta manual da pausa**
Dado a mesma pausa, quando a Mariana volta em 10 dez, então a empresa vira `ativa` na hora, com uma fatura de R$ 449,00 vencendo em 10 dez, e as seguintes vencem todo dia 10.

**CA-ASS-37 · Quem não pausa**
Dado a Moto Rápida `em_teste`, então a `Admin-Cancelar` não oferece pausar (só mudar para o Essencial). Dado a Moto Rápida `inadimplente`, pausar é recusado. Com uma pausa em andamento, outra pausa é recusada.

**CA-ASS-38 · Exportar antes de cancelar**
Na `Admin-Cancelar` e na `Admin-Assinatura`, "Exportar dados antes" leva à `Admin-Exportar` (auditoria em CSV), e o texto não promete exportar todos os dados: diz que o resto é pedido à equipe Giro.

**CA-ASS-39 · Contratos dos clientes**
Dado a Moto Rápida cancelada, então os contratos já assinados com clientes finais continuam válidos (nenhum contrato muda de estado com o cancelamento).

## Pontos em aberto resolvidos (T-211)

**CA-ASS-40 · Downgrade agendado que deixa de caber**
Dado uma empresa no Completo `ativa` com 86 veículos, 1 filial e 5 usuários, período de 22 out a 21 nov, com o Profissional agendado em 01 nov, quando o administrador convida mais 6 pessoas em 12 nov (11 usuários), então em 17 nov, na geração da fatura de 22 nov, o downgrade não acontece: a fatura de 22 nov sai com R$ 899,00, a tela deixa de dizer "O plano Profissional vale a partir de 22 nov", a empresa continua no Completo, e o administrador e o e-mail de cobrança recebem um e-mail com o motivo (11 de 10 usuários). Auditoria do downgrade recusado, pelo sistema. `test_plt_04_downgrade_agendado_deixa_de_caber`.

**CA-ASS-41 · Downgrade que cabia na geração da fatura**
Dado a mesma empresa sem convidar ninguém até 17 nov, quando a fatura de 22 nov sai com R$ 449,00 e o administrador convida as 6 pessoas em 19 nov, então os convites são aceitos (o limite ainda é o do Completo), e em 22 nov o plano vira Profissional com 11 de 10 usuários: ninguém sai, e um novo convite é recusado pelo limite (`PLT-03`) até sobrar vaga.

**CA-ASS-42 · Pausa com a fatura do período seguinte já emitida**
Dado a Moto Rápida `ativa`, FAT-0001 paga, e a FAT-0002 de 22 nov emitida em 17 nov, quando a Mariana pausa por 2 meses em 19 nov, então a FAT-0002 vira `cancelada` (nada é cobrado em 22 nov), a empresa continua `ativa` até 21 nov e fica `pausada` de 22 nov a 21 jan 2027, como no CA-ASS-35. `test_plt_06_pausa_comeca_no_fim_do_periodo_pago`.

**CA-ASS-43 · Desfazer o cancelamento no teste**
Dado a Moto Rápida cancelada em 10 out, no teste (CA-ASS-30), quando a Mariana desfaz o cancelamento em 15 out pela `Admin-Assinatura`, então a FAT-0001 continua `cancelada` e nasce a FAT-0002 `aberta`, R$ 449,00, vencendo em 22 out, "Plano Profissional · 22 out a 21 nov"; a empresa continua `em_teste` até 21 out, não vira `cancelada` em 22 out, e nenhum apagamento fica marcado. O desfazer fica na auditoria. `test_plt_06_desfazer_cancelamento_no_teste`.

**CA-ASS-44 · Desfazer o cancelamento na ativa**
Dado a Moto Rápida `ativa`, FAT-0001 paga, cancelada em 05 nov, quando a Mariana desfaz em 10 nov, então a fatura de 22 nov é gerada em 17 nov, como sempre, e a empresa segue `ativa` depois de 21 nov. Dado o cancelamento em 19 nov (FAT-0002 de 22 nov `cancelada`), quando ela desfaz em 20 nov, então nasce na hora a FAT-0003 `aberta`, R$ 449,00, vencendo em 22 nov, "Plano Profissional · 22 nov a 21 dez", com o boleto por e-mail em 20 nov; a FAT-0002 continua `cancelada`.

**CA-ASS-45 · Quem não desfaz**
Dado a Moto Rápida cancelada em 05 nov (acesso até 21 nov), quando a Mariana tenta desfazer em 22 nov, então não consegue (a empresa já é `cancelada` e não entra no sistema); só a equipe Giro reativa. Dado a Moto Rápida cancelada na hora como `inadimplente` (CA-ASS-34), não há o que desfazer. O Rodrigo, a Lúcia e o suporte Giro não desfazem (403, como no CA-ASS-19).

**CA-ASS-46 · Reativar a cancelada com fatura em atraso**
Dado a Moto Rápida cancelada em 25 out como `inadimplente`, com a FAT-0001 `atrasada`, quando a equipe Giro tenta reativar em 01 dez, então é recusado com "Receba a fatura em atraso antes de reativar." e nada muda. Quando a FAT-0001 é paga em 01 dez pela 2ª via (baixa pelo webhook) e a equipe reativa, então a empresa vira `ativa`, com a FAT-0002 de R$ 449,00 vencendo em 01 dez, "Plano Profissional · 01 dez a 31 dez", e as seguintes todo dia 1; a reativação fica na auditoria da empresa e na da plataforma, com o motivo. `test_plt_06_reativar_so_com_atrasada_paga`.

**CA-ASS-47 · Endereço da nota nasce da matriz**
Dado uma compra sem endereço (a `Compra-Checkout` não pede), antes do passo 6 os dados fiscais mostram o endereço vazio, e uma fatura paga nesse tempo não tem a nota pedida. Quando a Mariana cadastra no passo 6 a Filial Centro (matriz) em Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza, CE, CEP 60325-000, então os dados fiscais passam a ter esse endereço, e a nota que esperava é pedida (enquanto a NFS-e estiver desligada, como no CA-ASS-29, só o endereço é conferido). O seed Moto Rápida já nasce com esse endereço nos dados fiscais. `test_plt_15_endereco_nasce_da_matriz`.

**CA-ASS-48 · Endereço da nota e da filial mudam separados**
Dado a Moto Rápida do seed, quando a Mariana muda o número da Filial Centro para 1250 ou torna outra filial a matriz, então o endereço dos dados fiscais não muda. Quando ela muda o endereço da nota para Av. Dom Luís, 500, Sala 3, Meireles, Fortaleza, CE, CEP 60115-170, então as próximas notas levam esse endereço, e a Filial Centro continua na Bezerra de Menezes. A tela do passo 6 (`Onboarding-Filial`) pede o endereço pelo CEP e avisa que ele também vai na nota da assinatura; não diz "Mesmo endereço do CNPJ".

## Reativação no período pago (T-216)

**CA-ASS-49 · Reativar sem cobrar duas vezes o período pago**
Dado a Moto Rápida `ativa` com a FAT-0001 (22 out a 21 nov) paga em 22 out, upgrade para o Completo em 01 nov com a diferença de R$ 304,84 vencendo em 04 nov e não paga (`inadimplente` em 05 nov), cancelada em 10 nov (`cancelada` na hora), quando a diferença é paga em 15 nov pela 2ª via e a equipe Giro reativa em 15 nov, então a empresa vira `ativa` em 15 nov, nenhuma fatura vence em 15 nov, a fatura nova de R$ 899,00 vence em 22 nov ("Plano Completo · 22 nov a 21 dez"), e as seguintes continuam todo dia 22. Na reativação depois de 21 nov (CA-ASS-46), a fatura nova vence no dia da volta. `test_plt_06_reativar_no_periodo_pago`.

## Ramo e comissão nos módulos por plano (T-223)

**CA-ASS-50 · Troca de ramo com algo aberto**
Dado uma empresa no Profissional que aluga e vende, com 1 locação `ativa` e 1 venda `aguardando_aprovacao` (comissão dela `pendente`), quando o administrador muda o ramo em Configurações para "só vende", então é recusado, e a recusa diz quanto falta: 1 locação aberta. Quando muda para "só aluga", então é recusado com 1 venda aberta e 1 comissão não paga. Nada muda nas duas. Quando a locação é encerrada e ele muda para "só vende", então é aceito: Locações e Vistorias somem do menu no pedido seguinte, a API recusa as rotas delas (403 `PLT-12`, `motivo: "ramo"`), e a locação encerrada continua no banco. `test_plt_12_troca_de_ramo_com_algo_aberto`.

**CA-ASS-51 · Passo 7 do Essencial sem "só vende"**
Dado uma empresa no Essencial no passo 7, então a tela oferece "aluga" e "aluga e vende", e "vende" aparece com o aviso "Vendas faz parte do plano Profissional."; "só vende" não pode ser escolhido, e a API recusa o pedido com "só vende" no Essencial. Quando ela escolhe "aluga e vende", então o menu tem Locações e não tem Vendas nem Comissões (CA-ASS-22). Quando ela sobe para o Profissional, então Vendas e Comissões aparecem no pedido seguinte, sem refazer o passo 7. `test_plt_12_essencial_sem_so_vende`.

**CA-ASS-52 · Downgrade de quem só vende**
Dado uma empresa no Profissional que só vende, sem nada aberto e dentro dos limites do Essencial, quando o administrador tenta o Essencial, então é recusado com "O plano Essencial não inclui vendas. Para mudar, sua empresa precisa alugar." Nada muda. `test_plt_12_downgrade_so_vende`.

**CA-ASS-53 · Comissão de locação só depois do upgrade**
Dado uma empresa no Essencial `em_teste` que aluga e vende, quando a Bruna confirma uma locação em 10 out, então nenhuma comissão é lançada, nem quando a locação fica `ativa` em 16 out. Quando a empresa sobe para o Profissional em 15 out (no teste, vale na hora) e a Bruna confirma outra locação em 16 out, então nasce a comissão de R$ 16,00 `pendente` só para essa (`FIN-09`), `confirmada` quando ela fica `ativa`. A locação de 10 out continua sem comissão. `test_plt_12_comissao_so_depois_do_upgrade`.

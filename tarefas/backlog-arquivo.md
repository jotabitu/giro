# Backlog: itens resolvidos

> Decisões respondidas e tarefas feitas que ficavam riscadas no `backlog.md` (movidas na T-441). Não é leitura obrigatória. Daqui para frente, item resolvido sai do backlog em vez de ficar riscado.

## Decisões

- ~~[decisão]~~ (backend, T-365; para o produto) **Descrição da fatura no mesmo mês no CA-ASS-46.** **Decidido pelo dono em 30 out 2026:** vale a forma da `PLT-14`, como o código já faz; o produto acerta só o texto do CA-ASS-46. O CA-ASS-46 escreve "Plano Profissional · 01 dez a 31 dez", e a `PLT-14` diz que no mesmo mês é "01 a 21 nov". Padrão no código: a forma da `PLT-14` ("Plano Profissional · 01 a 31 dez"), a mesma de todas as faturas; `test_plt_06_reativar_so_com_atrasada_paga` espera essa. Pede só acertar o texto do CA-ASS-46.

- ~~[decisão]~~ **Cancelar e pausar: casos que a `PLT-06` não cobre** (arquiteto, T-194; avisar o produto). O contrato `docs/api/cancelamento.md` segue um padrão em cada um, e a T-195 pode começar por ele: (1) **cancelar em teste com a 1ª fatura já paga**: padrão, como a `ativa`, com acesso até o fim do período da 1ª fatura (como a mudança de plano no teste com a 1ª paga, `PLT-04`); alternativa: acesso até o fim do teste e a 1ª fatura estornada; (2) **desistir da pausa antes de começar**: padrão, o administrador desiste pela "voltar da pausa" e a fatura que a pausa cancelou nasce de novo, como no desfazer do cancelamento; alternativa: só pelo suporte; (3) **mudar de plano com cancelamento marcado**: padrão, recusado ("Desfaça o cancelamento antes de mudar de plano."); alternativa: aceitar o upgrade com a diferença; (4) **fatura de diferença em aberto ao começar a pausa**: padrão, continua devida com a régua dela, a `pausada` não vira `inadimplente`, e volta `inadimplente` se ainda estiver atrasada; (5) **o que fica no `public` depois do apagamento** (`AUD-08`, ADR 0025): padrão, a linha da empresa sem os dados de contato, as faturas da assinatura (registro fiscal do Giro) e a auditoria da plataforma; alternativa: apagar também a razão social e o endereço da linha (as faturas guardam o tomador). A validar com o contador o prazo das faturas.

- ~~[decisão]~~ **Cancelar a `ativa` com o período pago já vencido** (backend, T-195; para o produto). **Decidida pelo dono em 21 out 2026: A** (T-343, recomendação do produto): o acesso termina na hora, a empresa vira `cancelada` no mesmo dia e a fatura do dia é cancelada, sem ficar devida; com ela já paga, acesso até o fim do período dela. Regra `PLT-06`, tabela "Decisões de 21 out 2026", casos (e) e (f) de "Cancelamento da Moto Rápida", critério CA-ASS-69. O código da T-195 já faz A. A `PLT-06` dá acesso até o fim do período pago, mas não diz o que fazer quando esse fim já passou: a `ativa` no dia do vencimento da fatura seguinte, ainda sem pagar (o boleto vence hoje, ou o cartão é cobrado mais tarde no dia). Padrão no código (`calendario.datas_do_cancelamento`): o acesso termina agora, a empresa vira `cancelada` na hora e a fatura do dia vira `cancelada`, como na `inadimplente`; a tela mostra "termina agora". Alternativa: acesso até o fim do período da fatura do dia, se ela for paga. Teste `test_plt_06_acesso_que_ja_acabou_termina_agora`.

- ~~[divergência]~~ **Respondida na T-261 (produto):** o seed está certo (LOC-2856 `ativa` desde 07 out, com a 1ª semana e a caução no caixa); o CA-016-01 e o CA-016-08 são o momento antes da retirada, como fixture, e o CA-016-08 diz isso agora. (qa, T-105) A carteira de outubro (`docs/qa/carteira-outubro/locacoes.csv` e `tests/aceitacao/carteira.py`) traz a LOC-2856 como `ativa` desde 07 out 09:00. O CA-016-08 (e o CA-016-01) a quer `aguardando_retirada`, com retirada às 09:15. (O teste da agenda tira a LOC-2856 da carteira e cria a do critério.)

## Fase 1 · MVP

#### ~~[decisão]~~ Remetente do WhatsApp que o cliente da locadora vê (ADR 0034, levantada na T-385, T-387)
- **Decidido pelo dono em 30 out 2026: A**, o padrão abaixo. O produto tira o item dos "Pontos em aberto" das regras.
- **Para:** dono do produto, pelo orquestrador · **Contexto:** na opção A da ADR (um número só, do Giro), a Meta exige o nome de exibição do negócio verificado, e o cliente vê "Giro Avisos". Isso contraria "Toda mensagem ao cliente final sai com a marca da locadora, nunca com o nome Giro" (Automações).
  - **A:** exceção na fase 1. O remetente é "Giro Avisos", com a marca da locadora sempre no texto ("Moto Rápida informa: ...") e o perfil "Avisos das empresas que usam o sistema Giro. Este número não recebe mensagens."; número próprio na fase 2.
  - **B:** um número por locadora já, que é trabalho de fase 2.
  - **C:** sem WhatsApp ao cliente final na fase 1.

  **Padrão: A** (produto e arquiteto). Está em "Pontos em aberto" das regras; handoff `tarefas/handoffs/T-387-produto.md`.

#### ~~[decisão]~~ O que fica da empresa apagada: opção B da segurança (T-230, `AUD-08`, `PLT-14`)
- **Resolvido na T-235 (dono, 15 out 2026):** B para toda empresa, (a) para a fatura atrasada, e a compra de novo sem teste e esperando a fatura atrasada (`AUD-08`, `PLT-14`, `PLT-16`, CA-ASS-58 a 62).
- **Para:** produto (e o dono) · **Depois:** arquiteto (`cancelamento.md`, `assinatura.md`, `auditoria.md`) e backend (T-195).
- **Recomendação da segurança (B, igual para toda empresa, MEI ou não):** a linha apagada fica só com o CNPJ (sem razão social, nome de exibição, endereço e contato); a fatura guarda o tomador como foi na nota e ele sai com ela, no prazo de guarda; a auditoria do `public` guarda quais dados mudaram, sem os valores; depois da última fatura, o CNPJ sai e ficam reservados o subdomínio e o schema. **A**, o que está na `AUD-08` hoje, guarda nome e às vezes CPF e endereço de casa do MEI sem prazo e sem obrigação legal que peça a linha.
- **Junto (B-02):** `cnpj` único só entre empresas não apagadas, para a mesma empresa poder comprar de novo depois do apagamento.
- **Fatura atrasada no 90º dia:** (a) ela guarda o `email_cobranca` até a baixa ou o fim do prazo (recomendado, a dívida não some, `PLT-06`); (b) o Giro não cobra mais depois do apagamento.
- **Não depende do prazo** das faturas (dono e contador): só diz o que fica e preso a quê.

- ~~[decisão]~~ (T-338, para o dono) **Pedir a proposta à FIPE** pelo formulário de contato do site oficial, com as 7 perguntas do handoff. Enquanto ela não responde, a T-339 espera. Se a FIPE não licenciar ou cobrar caro demais: voltar à T-337 e escolher entre A (site, o dono assume o risco), uma API paga (mesmo risco da A, com o CSV pronto por R$ 59/mês) ou C (Renavam).
  - **Decidido (20 out 2026, dono): fonte provisória.** Enquanto não houver proposta da FIPE, o catálogo vem da API aberta da Parallelum (`https://parallelum.com.br/fipe/api/v2`, sem token; código MIT, dados da Tabela FIPE sem licença própria). O dono aceita o risco da opção A da T-337 enquanto isso for provisório. O pedido à FIPE ainda não foi feito. Se houver contrato, a fonte passa a ser a FIPE licenciada, e a ADR 0030 vale se o contrato proibir publicar. Registrado na ADR 0031 (T-342).

- ~~[decisão]~~ **Respondida (T-290, produto, 16 out 2026): fica o padrão do contrato, como leitura do produto a conferir pelo dono** (`MOV-02`, `USR-05`, "Pontos em aberto" das regras, item 6). O item Movimentações aparece para quem leva enquanto houver movimentação não concluída dele, no menu do perfil e no completo, e a tela mostra só as dele. Junto: a `MOV-02` passou a dizer que o financeiro não leva, como o contrato e o CA-246-11. (T-286, para o produto) **Como quem leva chega ao "Registrar chegada".** O vendedor e o vistoriador que levam o veículo não têm o item Movimentações (é de administrador e gerente, handoff da T-283), e a agenda do vistoriador com movimentações ficou fora. Padrão do contrato: o item `movimentacoes` aparece para quem leva enquanto houver uma movimentação aberta dele, e a lista mostra só as dele. Produto: confirmar ou trocar (ex.: aviso no sino ao ser escolhido).

- ~~[decisão]~~ **Respondida (T-290, produto, 16 out 2026): fica o padrão, só as concluídas hoje** (dia da filial de saída); as antigas na lista com o filtro de período. Registrado na seção Movimentações das regras. (T-286, para o produto) **Coluna Concluídas do quadro.** A tela mostra uma concluída "hoje 08:30". Padrão do contrato: só as concluídas hoje; as antigas ficam na lista com filtro. Produto: confirmar ou dar outra janela (últimos 7 dias, por exemplo).

#### ~~[decisão]~~ Pix automático da assinatura sem autorização (PLT-02, PLT-13, levantada na T-186 parte 2)
- **Decidida pelo dono em 16 out 2026: B** (T-296, recomendação do produto). Sem a autorização no dia da emissão (5 dias antes), a fatura sai em boleto com Pix por e-mail, como na forma boleto, com a linha "Seu Pix automático ainda não foi autorizado. Esta fatura vai por boleto com Pix.". A escolha do Pix automático continua e vale a partir da fatura seguinte, depois de autorizada; a fatura já emitida segue no boleto. Regras `PLT-13` e `PLT-02`, tabela "Decisões de 16 out 2026", critério CA-ASS-63. A tarefa do backend está no handoff `tarefas/handoffs/T-296-produto.md`, para o orquestrador numerar.
- Antes (A, o que o PR #302 fazia): nada era emitido, e a empresa só pagava pelo "Pagar". C (a forma voltar para boleto) foi descartada.

#### ~~[decisão]~~ Marco da régua da assinatura perdido (PLT-02, AUT-13, levantada na T-299)
- **Decidida pelo dono em 16 out 2026: B** (T-308, recomendação do produto). Só o D+7 sai depois, na próxima execução até o D+14, uma vez, com a ligação; o D-3, o D0 e o D+3 não são recuperados. Regras `PLT-02` e `AUT-13`, tabela "Decisões de 16 out 2026", critério CA-ASS-68. A T-303 já conta com B.
- **Para:** dono do produto, pelo orquestrador · **Contexto:** se a tarefa das 09:00 não rodar no dia de um marco, a mensagem não sai depois (como na `AUT-03`); no D+7, perde-se o último aviso antes da suspensão e a tarefa de ligação. A) nenhum marco é recuperado; B) só o D+7 sai na próxima execução, até o D+14, uma vez. **Padrão: B.** Em "Pontos em aberto" das regras. Entra na tarefa de backend dos textos (handoff `tarefas/handoffs/T-299-produto.md`).

#### ~~[decisão]~~ Suporte Giro nas movimentações (MOV-02, PLT-07, levantada na T-315, T-318)
- **Decidida pelo dono em 16 out 2026: A** (T-319, recomendação do produto e da segurança). Mesmo em "ver e editar", o suporte só lê as movimentações; toda escrita dá 403 `PLT-07`. Regras `MOV-02` e `PLT-07`, tabela "Decisões de 16 out 2026", critério CA-246-24. A T-316 já faz A.
- **Para:** dono do produto, pelo orquestrador · **Contexto:** o suporte em "ver e editar" age como administrador (ADR 0013), e a regra não diz se a movimentação é exceção. A) não: só lê; toda escrita das movimentações (criar, editar, iniciar, cancelar, chegada na parada e no destino, foto, local de apoio) dá 403 `PLT-07`; B) sim, como administrador, nunca como quem leva nem quem recebe. **Padrão: A** (o da segurança). Em "Pontos em aberto" das regras; handoff `tarefas/handoffs/T-318-produto.md`.

#### ~~[decisão]~~ Baixa de veículo com movimentação aberta (MOV-03, levantada na T-300, T-302)
- **Decidida pelo dono em 16 out 2026: B** (T-310, recomendação do produto). A baixa encerra a movimentação: a agendada e a iniciada viram `cancelada` (a iniciada com "Veículo baixado: {motivo}"), as despesas das paradas ficam, e na transferência o veículo continua na filial de saída. Regra `MOV-03`, tabela "Decisões de 16 out 2026", critérios CA-246-22 e 23. A recusa provisória da T-288 (A) deixa de valer.
- **Para:** dono do produto, pelo orquestrador · **Contexto:** a baixa vale para qualquer status menos `alugado`, e a movimentação iniciada só termina com a chegada (km e vistoria), que o veículo roubado no caminho não tem. A) a baixa é recusada com movimentação aberta (409 `MOV-03`); B) a baixa encerra a movimentação: a agendada e a iniciada viram `cancelada`, com o motivo "Veículo baixado: {motivo}", as despesas das paradas ficam, e na transferência o veículo continua na filial de saída. **Padrão: B.** Até a resposta, a T-288 recusa (A). Em "Pontos em aberto" das regras; handoff `tarefas/handoffs/T-302-produto.md`.

#### ~~[decisão]~~ Pix Automático: quando cobrar a parcela (AUT-04, levantada na T-029)
- **Respondida (T-283, 16 out 2026): fase 2.** Decisão do dono: no MVP, a parcela da locação segue boleto e Pix comum pela régua (`AUT-03`, `AUT-04`, `LOC-05`); o padrão abaixo fica de base para a fase 2. O fluxo na locação (handoff da T-029, item 1) não entra no MVP.
- **Com o dono (T-261, 16 out 2026):** em "Pontos em aberto" das regras ("Pix Automático nas parcelas da locação"), com o padrão: cobrança criada 5 dias úteis antes; a autorização nasce na 1ª parcela paga na retirada, e a parcela que vencer antes segue a régua comum; só a semanal e a mensal. Até a resposta, vale o padrão.
- **Para:** produto · **Contexto:** o contrato (`docs/api/financeiro.md`, "Cobrança recorrente") diz que `aut_04_cobranca_recorrente` cobra "no vencimento de cada parcela". Pela documentação do Asaas, a cobrança do Pix Automático tem de ser criada **de 2 a 10 dias úteis antes do vencimento**, e a autorização só fica ativa depois que o cliente paga a primeira cobrança pelo QR. Falta decidir: quantos dias antes a tarefa cria a cobrança da parcela, o que acontece com a parcela que vence antes de a autorização ficar ativa, e se a locação diária ou quinzenal pode ter Pix Automático (o Asaas aceita semanal, mensal, trimestral, semestral e anual). O provedor já está pronto (`asaas.py`, T-029); o fluxo na locação espera esta decisão (handoff `tarefas/handoffs/T-029-backend.md`, item 1).

## Dúvidas abertas da T-020 (frontend)

- ~~[decisão]~~ (T-201, Aprovações) A tela `Aprovacoes` mostra "Fornecedor" e "15 out · boleto" no pedido de despesa (`APR-03`), mas a despesa não tem fornecedor (`FIN-05`, `FIN-06`) e só tem forma depois de paga. Padrão do contrato até a resposta: o `resumo` sai com categoria, veículo, valor e vencimento, sem fornecedor nem forma. Produto: a despesa ganha fornecedor (e a forma prevista) ou a tela perde as duas células?

- ~~[decisão]~~ **Respondida na T-261 (produto, 16 out 2026): fica "Nenhuma filial ativa".** Só acontece antes do passo 6 da implantação, porque a última filial ativa não se desativa (`FIL-06`), e o texto vale nos dois casos. (T-181, Configurações) Empresa sem filial ativa: o contrato não diz o resumo do cartão Filiais; o backend usa "Nenhuma filial ativa" (como "Nenhuma categoria cadastrada" em Tabelas de preço). Produto: confirmar ou trocar o texto.

## Fase 2 em diante

#### ~~T-378 · Completo fora da venda (`PLT-11`)~~
- **Feita na T-435** (05 nov 2026): `Plano.a_venda`, o Completo nasce fora (migração `plataforma.0014`), sai de Mudar de plano, de Comparar planos e do cartão do plano acima, e a API recusa a mudança para ele. O texto do Profissional passou ao da fase 1. Falta a resposta do dono sobre o preço e os limites do Profissional ("Pontos em aberto").

#### ~~T-432 · Backend da compra pública~~
- **Feita na T-435** (05 nov 2026), antes da T-431, por pedido do dono. A revisão da segurança continua valendo sobre o código pronto.

#### ~~T-433 · Frontend da compra pública~~
- **Feita na T-435** (05 nov 2026), sem esperar a T-434: as telas seguem o contrato. Falta a conferência lado a lado (`npm run conferencia`) e o E2E, que dependem das telas ajustadas na T-434.

- ~~[decisão] CA-420-12: a tela `Vendas` não existe no frontend.~~ **Resolvida pelo dono em 03 nov 2026 (opção A, PR #476):** a T-420 confere a venda da quitação pela API (detalhe da locação e histórico do veículo); "aparece em `Vendas` com o rótulo" passa para a tarefa da tela `Vendas` (T-418). Critério ajustado em `docs/qa/criterios/T-420.md`.

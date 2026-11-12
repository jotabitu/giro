# Capturas · 12 nov 2026 (T-451, T-452, T-462, T-421, T-436)

Pedido do Orquestrador. Conferido na develop em 557b73c6 (#544), `http://motorapida.localhost:3000`, a 1440 e 390 px, um contexto por vez, com as contas do seed. O relógio é o real (12 nov), não o de 07 out: os casos do seed em 07 out (LOC-2856, CA-451-07) não se reproduzem. Capturas em `tarefas/handoffs/anexos/T-451/`, `T-462/` e `T-421/`.

## Resumo

| Item | Resultado |
| --- | --- |
| T-451 · retirada sozinha (CA-451-03) | Passa |
| T-451 · retirada à mão (CA-451-09, 10, 11, 13, 14) | Passa, com um achado na lista (A1) |
| T-451 · quem pode (CA-451-04, 06) | Passa |
| T-452 · caução (CA-452-01 a 03) | Passa em parte, com o achado A2 |
| T-462 · fotos enviando (VEI-10) | Contador, diálogo e Voltar passam; achado A3 |
| T-421 · campos do CRLV-e | Passa (CA-421-08, 11, 12, 14); leitura do PDF não exercitada |
| T-436 · `/recibo` | Não capturável: o link do recibo está desligado no compose (A4) |

## Achados

- **A1 · Coluna "Pagamento" da lista de locações diz "Pago" com nada pago (`LOC-17`, `FIN-01`).** LOC-2871, retirada à mão pelo gerente com contrato, parcela 1 e caução em aberto ("Vence hoje", total pago R$ 0,00), aparece em "Precisam de ação" com situação "Faltam assinatura e pagamento" e pagamento "Pago". A LOC-2864 (aguardando retirada) diz "Aguardando pagamento". Captura: `T-451/B5-lista-precisam-de-acao-loc-2871-rodrigo-1440.png`. Dono: backend (campo que alimenta a coluna) ou frontend, a definir.
- **A2 · Caução paga aparece como "Devolver na entrega", não "Paga" (`FIN-18`, CA-452-01, 03, 06).** Depois do "Registrar pagamento" da caução em dinheiro (LOC-2870), a linha da ficha passa de "Em aberto" para "Devolver na entrega", sem o selo "Paga". O critério diz "Paga". Pode ser decisão posterior do Produto; peço confirmação. Capturas `A5` e `A8`. Observação menor: em `Receber`, com a caução na lista, o rodapé diz "Mostrando 2 de 1 parcelas" (a caução não conta nos números, `FIN-15`, mas o texto fica sem sentido); a linha de desktop traz "Cobrar" e a de celular "Dar baixa".
- **A3 · Cadastro do veículo não abre a ficha depois de "Ficar" (`VEI-10`, CA-437-05, CA-437-11).** Repro: em `/veiculos/novo`, preencha o mínimo, escolha 2 fotos, atrase os `POST /api/veiculos/{id}/fotos/` (8 s cada), Salvar veículo; durante o envio, clique no link "Veículos" do caminho, toque "Ficar" e espere. O envio termina (o veículo fica com as fotos), mas a tela continua em `/veiculos/novo` com o formulário cheio e sem andamento; sem "Ficar", a ficha abre (CA-437-05 passou em 11 nov). Repetido a 1440 e a 390 px (também depois de Voltar e "Ficar"). Risco: a pessoa salva de novo e leva 409 de placa repetida. Captura do estado final: `T-462/cadastro-depois-de-ficar-nao-abre-a-ficha-390.png`. Dono: frontend (T-462).
- **A4 · `GIRO_RECIBO_PUBLICO` está desligado no compose (T-436).** `settings.GIRO_RECIBO_PUBLICO` vale `False` no `giro-backend-1`; o #533 só mudou os `.env.example`, e o `.env` local não tem a variável. `/recibo#<token>` responde "Link não encontrado". Não mexi no `.env`. Quando ligar, preciso de uma devolução concluída para gerar o link (Copiar link do recibo).
- Observação (não é falha de critério): o financeiro vê "Fazer vistoria de saída" no topo da ficha, mas não dentro do "Para retirar".

## T-451 · retirada (`LOC-17`)

Locações novas pela Bruna na Filial Centro, caixa do dia aberto por ela com R$ 100,00: LOC-2870 (Osvaldo Pimentel, id 56) e LOC-2871 (Nicole Fontenele, id 57), semanal Street R$ 329,00 com caução R$ 300,00, início hoje. LOC-2864 (Tales Gondim, id 50) é a do seed com a vistoria pendente.

| CA | Resultado | Como foi |
| --- | --- | --- |
| 451-01 | Passa | `A1-...-bruna-1440/390`: "Falta a vistoria de saída", "Falta enviar o contrato", "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00" e "Retire até 15 nov. Sem retirada, a locação é cancelada em 16 nov." |
| 451-02 | Passa | Vistoria: "Feita em 12 nov, 11:14". Contrato enviado: "Falta a assinatura do cliente" com "Reenviar" e "Copiar link para assinar". Só a caução paga: "Falta receber R$ 329,00: 1ª semana R$ 329,00" (`A3`, `A5`). |
| 451-03 | Passa (assinatura por último) | Vistoria, contrato, caução, parcela 1 e, por último, a assinatura pelo link no celular (`A7`): a LOC-2870 virou "Ativa" na hora, "Para retirar" sumiu e o Histórico tem "Retirada · Sistema" (`A8`). Pagamento por último não exercitado. |
| 451-04 | Passa, em parte | Mariana e Rodrigo veem "Registrar retirada"; Bruna, João e Lúcia não (`C-...`). API: Bruna 403 `permissao`. Gerente de outra filial e a rota depois da retirada (409 `transicao_locacao`) não exercitados. |
| 451-05 | Não exercitado | |
| 451-06 | Passa | João: só "Fazer vistoria de saída". Bruna: vistoria, "Enviar contrato" e "Registrar pagamento". Lúcia: "Registrar pagamento", sem "Enviar contrato". |
| 451-07, 08 | Não exercitados | Relógio no dia real; o seed de 07 out não vale. |
| 451-09 | Passa | LOC-2864: botão desligado com "Faça a vistoria de saída antes da retirada."; `POST /api/locacoes/50/retirada/` do Rodrigo respondeu 409 `vistoria_saida_pendente`, "Faça a vistoria de saída antes da retirada." Com assinatura e pagamento feitos: não exercitado. |
| 451-10 | Passa, em parte | `B2`: "Registrar retirada?" com "Falta enviar o contrato" e "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00", campo Motivo. `B3`: vazio, "Informe o motivo." API 422 e limite de 200 caracteres não exercitados. |
| 451-11 | Passa, em parte | LOC-2871 com o motivo "Cliente paga amanhã, combinado com a gerência": virou "Ativa", um só evento "Retirada · Rodrigo Pinheiro" no Histórico, contas "Vence hoje". O Histórico não mostra o motivo nem "à mão"; comissão, `retirada_a_mao` e o payload da auditoria não conferidos. |
| 451-12 | Não exercitado | Só o dia da retirada: parcela 1 e caução "Vence hoje". |
| 451-13 | Passa | `B4`: "Pendências da retirada" com "Falta enviar o contrato" e "Falta receber ..."; situação "Faltam assinatura e pagamento"; depois do contrato, "Falta a assinatura do cliente" com "Reenviar" e "Copiar link para assinar" (`B6`); assinado, a situação vira "Falta o 1º pagamento" (`B7`); caução paga, "Falta receber R$ 329,00: 1ª semana R$ 329,00" (`B8`); tudo pago, a seção some (`B9`). Lista: LOC-2871 em "Precisam de ação" (`B5`, ver A1). "Falta a assinatura" sozinha não capturada. |
| 451-14 | Passa, em parte | Depois da pendência cumprida a locação segue "Ativa", com um único evento "Retirada" (Rodrigo), e o botão não reaparece. `AUT-17` e a tarefa de 7 dias não exercitadas. |

## T-452 · caução (`FIN-18`)

| CA | Resultado | Como foi |
| --- | --- | --- |
| 452-01 | Parcial | A ficha tem "Parcela 1" e "Caução" com "Registrar pagamento" para a Bruna; depois de paga, a caução mostra "Devolver na entrega" (A2). |
| 452-02 | Passa | `D-receber-vencem-hoje-com-caucao-lucia-1440/390`: LOC-2864 com "Caução · R$ 300,00 · Vence hoje"; "Vence hoje" segue R$ 329,00 (1 parcela) e a aba "Vencem hoje" conta 1 (ver o rodapé "2 de 1" em A2). |
| 452-03 | Parcial | Baixa em dinheiro pelo diálogo "Dar baixa em Osvaldo Pimentel" (`A4`), "R$ 300,00 recebidos"; a locação continuou aguardando a assinatura. Caixa e receita não conferidos. |
| 452-04 a 06 | Não exercitados | |

## T-462 · fotos enviando (`VEI-10`)

Atraso de 20 a 25 s em cada `POST .../fotos/` (interceptado no navegador). Cadastro: TBC-5H31 (id 98) a 1440 e TBC-5H32 (id 99) a 390. Editar do veículo 98, com 3 fotos novas, a 1440 e a 390.

- **Contador:** "Faltam 3 fotos. Não feche esta tela." junto de "Enviando fotos · 1 de 3" (cadastro) e "Enviando 1 de 3…" (editar). Passa.
- **Link interno:** diálogo "Sair desta tela?", "Ainda faltam 3 fotos. Se sair, elas não serão enviadas.", botões "Sair" e "Ficar". "Ficar" mantém a tela. Passa nos quatro casos.
- **Voltar do navegador:** `history.back()` abre o mesmo diálogo, sem sair; "Ficar" mantém. Passa a 1440 e 390 (cadastro e editar).
- **`beforeunload`:** ao recarregar com fotos por subir, o Chromium abriu o aviso nativo (evento `beforeunload` registrado no Playwright, sem texto), no cadastro a 1440 e no editar a 1440 e 390. Não saiu na captura, como previsto.
- Falha: A3.

## T-421 · campos do CRLV-e

Sem os PDFs de teste (nenhum `crlv-*.pdf` no repositório), a leitura do documento (CA-421-01 a 05, 10) não foi exercitada. O resto:

| CA | Resultado | Como foi |
| --- | --- | --- |
| 421-06 | Parcial | Na tela, os campos de "Dados do documento" e "Rastreador e anotações" não são obrigatórios; cadastro só com o mínimo não testado. |
| 421-08 | Passa em parte | Combustível visível no cadastro, no editar e na ficha (QXA-4B21: Flex). Troca e auditoria não testadas. |
| 421-11 | Passa | Rodrigo, QXA-4B21 a 1440 e 390: Flex; 15 cv; 162 cc; Passageiro · Motocicleta; carroceria "—"; 2 pessoas; 290 kg; motor KC22E1P004401; observações "ALIENACAO FIDUCIARIA"; rastreador 356938035643809 · Rastreia Fácil; anotação "Risco no tanque, lado esquerdo". |
| 421-12 | Passa | Bruna, João e Lúcia veem tudo isso, menos o número do motor e as observações, sem espaço vazio na ficha. |
| 421-14 | Passa | PNB-7C04: todos os campos "—", sem erro. |

Cadastro preenchido à mão (campos novos e salvos corretamente na ficha de TBC-5H31/5H32): potência 8 cv, 109 cc, 2 pessoas, 240 kg, motor, observações, rastreador, anotação.

## T-436 · `/recibo`

Não capturado, ver A4.

## O que ficou no ambiente

Dados de teste, que não se apagam: LOC-2870 (ativa, paga) e LOC-2871 (ativa, paga); caixa do dia aberto pela Bruna com R$ 100,00 e entradas de R$ 629,00 (LOC-2870) e R$ 629,00 (LOC-2871); veículos TBC-5H31 (id 98, 3 fotos do cadastro mais as dos testes do editar), TBC-5H32 (id 99, 3 fotos) e TBC-5H33 (id 100, criado na repetição do A3, 2 fotos). `make seed` devolve o seed.

## Repetição de A1 e A3 · develop em 1dde984b (#549, #550)

Pedido do Orquestrador, a 1440 e 390 px, com as contas do seed (Rodrigo, Bruna, João). Capturas em `tarefas/handoffs/anexos/T-466/` (A1 e A3 desta rodada, arquivos `A1-...` e `A3-...`).

| Item | Resultado |
| --- | --- |
| A1 · coluna "Pagamento" (T-466, `LOC-17`, `FIN-01`) | Corrigido |
| A3 · ficha depois de "Ficar" (T-462, `VEI-10`) | Corrigido |
| A2 · caução paga | Fechado: "Devolver na entrega" (decisão do dono, #548) |
| Voltar depois da ficha | Cai em `/veiculos/novo` (achado A6) |

**A1.** Como a LOC-2871 já estava paga, usei a LOC-2864 (Tales Gondim, do seed): vistoria de saída pelo João e retirada à mão pelo Rodrigo, com motivo, sem nada pago.
- Sem pagamento (total pago R$ 0,00): em "Precisam de ação" a coluna diz "Aguardando pagamento", com a situação "Faltam assinatura e pagamento". 1440 e 390. Capturas `A1-lista-loc-2864-sem-pagamento-rodrigo-*`.
- Com só a caução paga em dinheiro pela Bruna (a ficha mostra "Devolver na entrega"): a coluna diz "R$ 300,00 pago". 1440 e 390. Capturas `A1-lista-loc-2864-caucao-paga-rodrigo-*`. Observação: o valor pago que a lista mostra é a caução, e as duas parcelas seguem abertas. Pelo critério do pedido ("R$ X pago se parte foi paga") está certo; se a caução não deveria entrar nesse número (`FIN-15`), é pergunta para o Produto.
- A LOC-2871 continua "Pago" porque está paga de verdade.

**A3.** Roteiro: `/veiculos/novo` com o mínimo e 2 fotos, `POST .../fotos/` atrasado 8 s, Salvar veículo; durante o envio ("Enviando fotos · 1 de 2", "Faltam 2 fotos. Não feche esta tela."), sair pelo link "Veículos" ou por `history.back()`, diálogo "Sair desta tela?", "Ficar".

| Caminho | 1440 | 390 |
| --- | --- | --- |
| Link "Veículos" e "Ficar" | Ficha abre (`/veiculos/102`), com 2 fotos na galeria | Ficha abre (`/veiculos/105`) |
| Voltar do navegador e "Ficar" | Ficha abre (`/veiculos/104`) | Ficha abre (`/veiculos/106`) |
| Sem sair da tela (controle) | Ficha abre (`/veiculos/103`) | Ficha abre |

Capturas: `A3-cadastro-enviando-*`, `A3-dialogo-sair-ou-ficar-*`, `A3-depois-de-ficar-*`.

- **A6 · Voltar depois da ficha cai no formulário de novo cadastro.** Nos seis casos acima, inclusive no controle sem "Ficar", `history.back()` na ficha leva a `/veiculos/novo` (formulário vazio, "Cadastrar veículo"). Não é regressão do #549 (acontece também sem o diálogo), mas é o que o pedido mandou conferir: o Voltar cai no formulário. Quem salva e aperta Voltar pode cadastrar de novo e levar 409 de placa repetida. Capturas `A3-voltar-depois-da-ficha-*`. Dono: frontend (trocar o `push` da ficha por `replace` depois do salvar, se for essa a intenção).

**O que ficou no ambiente.** LOC-2864 retirada à mão (ativa, sem assinatura, caução paga, parcelas 1 e 2 em aberto) e veículos TBC-6A01 a TBC-6A06 (ids 102 a 107, 2 fotos cada). `make seed` devolve o seed.

## Repetição de A6 · develop em 711a4bf6 (#555)

Mesmo roteiro do A3 (`POST .../fotos/` atrasado 8 s, 2 fotos), a 1440 e 390 px. Capturas em `tarefas/handoffs/anexos/T-462/`, arquivos `A6-...` e `A6b-...`.

| Caminho | Ficha abre | Voltar na ficha |
| --- | --- | --- |
| 1440 · link "Veículos" e "Ficar" | Sim (`/veiculos/108`) | `/inicio`, de onde o teste entrou |
| 1440 · sem sair da tela | Sim (`/veiculos/109`) | `/inicio` |
| 390 · Voltar do navegador e "Ficar" | Sim (`/veiculos/110`) | `/inicio` |
| 1440 · pelo caminho real: lista de veículos, "Cadastrar veículo", salvar (`A6b-...`) | Sim (`/veiculos/111`) | `/veiculos`, a lista |

**A6: corrigido.** O Voltar depois da ficha não cai mais em `/veiculos/novo`: volta à tela de antes do cadastro. O 390 px foi exercitado só no caminho com Voltar e "Ficar".

**No ambiente:** veículos TBC-6B01 a TBC-6B04 (ids 108 a 111, 2 fotos cada). `make seed` devolve o seed.

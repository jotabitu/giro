# Fluxo de venda: estados sobre a `Venda` que existe, assinatura e entrada antes de `vendida`, contas, comissão, funil, meta e as três fases

**Status:** aceita · 18 nov 2026 · T-501 (regras: `VEN-01` a `VEN-18`, `APR-01`, `AUT-19`, `FIN-03`, `FIN-09`, `FIN-10`, `VEI-07`, `LOC-16`, `IMP-04`, `DEV-02`, `CLI-03`, `CLI-05`, `PLT-12`; os 18 pontos em aberto da T-501, PR #628, com o padrão A confirmado pelo dono em 18 nov 2026 e registrados nas regras pelo PR #629) · detalha a 0011, a 0015, a 0019 e a 0024 · **mantém intactos** os itens 4 a 6 da 0037 (venda da quitação, `VEN-11`)

## Contexto

O backend só tem a venda da quitação (`VEN-11`), a transferência no Detran e o cancelamento que recusa a quitação (`backend/apps/vendas/services.py`). O model `Venda` nasceu inteiro na T-420 (modelo de dados, item 17), com os 7 estados, preço de tabela, desconto, forma, entrada, parcelas, troca e os campos do cancelamento, mas sem transições completas, sem as datas do funil, sem aprovação, sem contrato e sem meta. As telas `Vendas`, `Venda` (Negócio → Documentos → Assinatura) e `Vendedor` existem desde o começo.

Os 18 pontos da T-501 decidem o comportamento (padrão A em todos, confirmados pelo dono em 18 nov 2026). O PR #629 do Produto os registra nas regras: `VEN-13` (passagens e vencimento), `VEN-14` (cliente e documentos), `VEN-15` (proposta, contrato e conclusão), `VEN-16` (último contato), `VEN-17` (transferência da venda comum), `VEN-18` (o que fica fora da primeira entrega), os detalhes novos da `VEN-02` à `VEN-09`, a `FIN-09` (venda que não fecha), a `AUT-19` (proposta vencida) e a `IMP-04` (modelo de compra e venda). Esta ADR cita esses códigos. O que é caro de desfazer, e esta ADR fixa: as transições e as datas guardadas (o funil e o ticket médio leem delas), o momento em que a venda vira `vendida` (assinatura e entrada pagas, como a retirada da locação), quem guarda o quê entre `vendas`, `financeiro`, `contratos`, `aprovacoes` e `veiculos`, o ciclo da comissão, a meta e a divisão em fases.

## Decisão

### 1. A ordem dos apps não muda

`vendas` é o nível 12 da ADR 0011: chama direto os serviços de `veiculos`, `clientes`, `contratos`, `aprovacoes`, `financeiro` e `notificacoes`, e guarda FK para `contratos.Contrato` e `financeiro.ContaReceber` (sentido permitido). Nenhum app de baixo importa `vendas`. Os efeitos que vêm de baixo chegam por evento, como na locação:

| Evento | Publica | O que `vendas` faz |
| --- | --- | --- |
| `contratos.contrato_assinado` (`origem_tipo = "venda"`, `tipo = "contrato"`) | contratos | `registrar_contrato_assinado(venda_id, assinado_em)` e `concluir_se_pronto` |
| `financeiro.parcela_paga` (`origem_tipo = "venda"`, `tipo = "entrada"`) | financeiro | `registrar_entrada_paga(venda_id, pago_em)` e `concluir_se_pronto` |
| `aprovacoes.pedido_decidido` (`tipo = "APR-01"`, `origem_tipo = "venda"`) | aprovacoes | `aplicar_decisao_desconto(venda_id, status, motivo)` |
| `locacoes.locacao_quitada` | locacoes | igual a hoje (`VEN-11`) |

O que `veiculos` precisa saber de `vendas` (o veículo com venda em andamento não volta para a frota) vem por registro, como as travas da conta (`financeiro.registrar_trava_da_conta`): `veiculos` ganha `registrar_trava_do_estoque(funcao)`, e `vendas` registra no `ready()` a que recusa `voltar_para_frota` e `baixar` com venda aberta (`VEN-10`): 409 `{"codigo": "VEN-10", "mensagem": "Este veículo tem uma venda em andamento (VEN-0177)."}`. Sem o registro (testes de `veiculos` isolados), não há trava.

### 2. Máquina de estados

Os 7 estados ficam. A tabela `Venda.TRANSICOES` passa a ser esta (só a venda de balcão anda por ela; a da quitação nasce `vendida` e só tem a transferência):

| De | Para | Serviço | Quem |
| --- | --- | --- | --- |
| (nova) | `interessado` | `criar(acao="interessado")` | administrador, gerente, vendedor |
| (nova) | `proposta` | `criar(acao="enviar")`, desconto até o limite | idem |
| (nova) | `aguardando_aprovacao` | `criar(acao="pedir_aprovacao")`, desconto acima do limite | idem |
| `interessado` | `proposta` | `enviar_proposta` | idem |
| `interessado`, `proposta`, `negociacao` | `aguardando_aprovacao` | `pedir_desconto` | idem |
| `proposta` | `negociacao` | `registrar_resposta` | idem |
| `aguardando_aprovacao` | o estado de antes (`interessado` vira `proposta` e a proposta é enviada) | `aplicar_decisao_desconto` (aprovado, recusado ou pedido cancelado) | o gerente decide; o sistema aplica |
| `proposta`, `negociacao` | `vendida` | `concluir_se_pronto` (contrato assinado e entrada paga) | sistema |
| `interessado`, `proposta`, `negociacao`, `aguardando_aprovacao` | `perdida` | `perder` (motivo obrigatório), `vencer_propostas` ("proposta vencida"), `_perder_interessados` ("veículo vendido", `VEN-10`) | administrador, gerente, vendedor (a dele); sistema |
| `vendida` | `cancelada` | `cancelar` (**fase 2**) | administrador, gerente (`VEN-07`) |

- `negociacao` → `proposta` sai da tabela de hoje: reenviar a proposta em negociação manda o PDF de novo e deixa a venda em `negociacao` (`proposta_enviada_em` muda; as datas de entrada no funil, não).
- O estado de antes do pedido fica em `status_antes_aprovacao` (abaixo). A "Nova venda" que já nasce pedindo aprovação grava `interessado` ali, e por isso, aprovada, vira `proposta` e é enviada (`VEN-13`).
- Toda mudança de status sai por `comum.estados.transicionar`, com auditoria e regra (`VEN-13`, `VEN-02`, `VEN-15`, `VEN-07`, `VEN-10`, `APR-01`). A criação grava `venda.criar` com o estado inicial. Erro de passagem: 409 `transicao_venda`, como hoje.

### 3. Campos

Todos em `vendas.Venda`, migration `vendas` 0002, nulos ou com padrão (as vendas da quitação que já existem não mudam).

| Campo | Tipo | Observação |
| --- | --- | --- |
| `cliente` | FK → `Cliente`, **passa a nulo** | o interessado do catálogo pode não ter cadastro (`VEN-14`) |
| `interessado_nome` | texto(150), vazio | quando não há `cliente` |
| `interessado_celular` | texto(13), vazio | idem; só dígitos, como `Cliente.celular` |
| `preco_tabela_centavos` | já existe | copiado de `Veiculo.valor_venda_centavos` ao criar (`VEN-01`); não muda depois |
| `desconto_pct` | já existe | o desconto da proposta (pedido, enquanto `aguardando_aprovacao`) |
| `desconto_centavos` | centavos, padrão 0 | `preco_tabela × desconto_pct ÷ 100`, `ROUND_HALF_UP` no centavo (`VEN-02`) |
| `preco_final_centavos` | já existe | tabela − desconto; com a troca dentro (`VEN-12`) |
| `forma` | já existe | fase 1 e 2: só `a_vista` e `entrada_parcelas`; `financiamento` dá 400 no campo até a fase 3 (`VEN-18`) |
| `entrada_centavos` | já existe | o dinheiro da entrada; à vista = preço final − troca |
| `num_parcelas` | já existe | 2 a 24 (`VEN-04`) |
| `juros_pct` | já existe | juros ao mês da venda parcelada, **copiado** de `ConfiguracaoEmpresa.juros_venda_mes_pct` ao criar a proposta e atualizado a cada edição antes da assinatura |
| `parcela_centavos` | centavos, nulo | a parcela calculada (com juros, a da tabela Price); a diferença de centavos vai para a última conta |
| `troca_veiculo`, `troca_valor_centavos` | já existem | **fase 2** |
| `troca_dados` | json, nulo | **fase 2**: placa, chassi, marca, modelo, ano, km do veículo da troca antes de `vendida` |
| `status_antes_aprovacao` | enum `interessado`, `proposta`, `negociacao`, vazio | |
| `aprovacao` | enum `pendente`, `aprovado`, `recusado`, `cancelado`, vazio | situação do último pedido de desconto |
| `pedido_aprovacao_id` | bigint, nulo | o `PedidoAprovacao` (origem genérica; sem FK, ADR 0019) |
| `desconto_aprovado_pct` | pct, nulo | o maior desconto aprovado; até ele não se pede de novo |
| `motivo_recusa` | texto(300), vazio | à vista na tela até o vendedor refazer (`VEN-13`) |
| `entrou_proposta_em` | momento, nulo | **primeira** entrada em `proposta`; nunca se reescreve (funil, `VEN-08`) |
| `entrou_negociacao_em` | momento, nulo | primeira entrada em `negociacao` ou `aguardando_aprovacao` (funil) |
| `proposta_enviada_em` | já existe | **último** envio; o vencimento conta dele (`VEN-13`, `AUT-19`) |
| `perdida_em` | momento, nulo | |
| `ultimo_contato_em` | momento, nulo | a última mudança da venda: criação, envio, edição e estado, gravada por todo serviço que muda a venda (`VEN-16`) |
| `contrato` | FK → `contratos.Contrato`, nulo | o contrato vigente de compra e venda |
| `contrato_assinado_em` | momento, nulo | copiado do evento |
| `conta_entrada` | FK → `financeiro.ContaReceber`, nulo | a conta da entrada (ou do total à vista) |
| `entrada_paga_em` | momento, nulo | copiado do evento |
| `vendida_em` | já existe | o funil, o ticket médio, a meta, a comissão e o 1º vencimento leem daqui |
| `transferencia_feita_em`, `transferencia_registrada_por` | já existem | agora também na venda de balcão (`VEN-17`) |

**Restrições novas** (as da T-420 ficam):

- `CHECK`: `cliente_id IS NOT NULL OR status IN ('interessado', 'perdida')`; e `cliente_id IS NOT NULL OR interessado_nome <> ''`.
- `CHECK`: `desconto_pct` entre 0 e 100; `forma <> 'entrada_parcelas' OR num_parcelas BETWEEN 2 AND 24`.
- `CHECK` (fase 2): `troca_valor_centavos IS NULL OR troca_valor_centavos <= preco_final_centavos`.
- O índice parcial `venda_transferencia_pendente` muda de condição: `status = 'vendida' AND transferencia_feita_em IS NULL` (as duas origens; a quitação é sempre `vendida`, então nada muda para ela).
- Índices novos: `(filial, vendida_em)` com `origem = 'balcao'` (ticket, meta, funil); `(filial, criado_em)` com `origem = 'balcao'` (interessados e conversão); parcial `(proposta_enviada_em)` com `status = 'proposta'` (a rotina de vencimento).
- `uma_venda_aberta_por_veiculo` fica como está (`VEN-10`).

**Dados pessoais.** `interessado_nome` e `interessado_celular` são dado pessoal sem cadastro: vão mascarados na auditoria (`CAMPOS_AUDITORIA`, como o celular do cliente) e, na venda `perdida` sem cliente, entram na anonimização da `CLI` pela mesma rotina que já apaga os dados do cliente inativo (a Segurança confere na T-502).

**Configuração da empresa** (`empresas` 00NN): `ConfiguracaoEmpresa.juros_venda_mes_pct`, pct, padrão 0.00, `CHECK >= 0` (`VEN-04`). O limite do desconto da venda **não** é campo: é a constante `vendas.services.LIMITE_DESCONTO_PCT = Decimal("5.00")` (`VEN-02`). A comissão usa o `comissao_venda_pct` que já existe (3.00).

#### `vendas.MetaVenda` (`VEN-09`)

| Campo | Tipo | Observação |
| --- | --- | --- |
| `vendedor` | FK → `contas.Usuario` | perfil vendedor |
| `filial` | FK → `Filial` | a pessoa pode estar em mais de uma filial; a meta é por filial |
| `mes` | data (dia 1) | |
| `valor_centavos` | centavos, `CHECK > 0` | |
| `definida_por` | FK → `Usuario` | gerente da filial ou administrador |

Único `(vendedor, filial, mes)`. Mudar o valor é `update` pelo serviço, com auditoria; "sem meta" é não ter linha (apagar a meta é a única exclusão física aceita aqui, porque meta não é registro de negócio com efeito; a auditoria guarda o valor de antes). Meta da filial = soma das metas da filial no mês.

### 4. Contas: cálculo puro e o que a API devolve

`vendas/calculo.py`, módulo puro como `veiculos/precos.py` (ADR 0041), com `Decimal` nas contas e `ROUND_HALF_UP` só no que se grava:

- `desconto_centavos = arredondar(preco_tabela × desconto_pct ÷ 100)`; `preco_final = preco_tabela − desconto`.
- `saldo = preco_final − entrada − troca`; à vista, `saldo = 0` e `entrada = preco_final − troca`.
- Sem juros: `parcela = saldo // n` e a última leva a diferença. Com juros: `parcela = pmt(saldo, juros_pct, n)` arredondada, reaproveitando `veiculos.precos.pmt` (a mesma conta da `VEI-16`); a última fecha `parcela × n` (não o saldo, porque com juros o total é maior que o saldo) e não há diferença a levar.
- `comissao = arredondar(preco_final × comissao_venda_pct ÷ 100)`.
- `precisa_aprovacao = desconto_pct > max(LIMITE_DESCONTO_PCT, desconto_aprovado_pct or 0)`.
- `vencimentos(vendida_em_local, n)`: 1ª um mês depois, no mesmo dia; no mês sem o dia, o último dia do mês (`VEN-04`).

Casos de teste obrigatórios: `test_ven_02_ven_0177_8_pct_21068` (22.900,00 com 8% = 21.068,00, desconto 1.832,00), `test_ven_04_ven_0177_12_x_1339` (16.068,00 ÷ 12 = 1.339,00), `test_fin_09_ven_0177_comissao_63204`.

### 5. Serviços (`vendas/services.py`)

Todos numa transação, com `select_for_update` na venda, auditoria com a regra e `ultimo_contato_em` (`VEN-16`). O vendedor só mexe nas dele (`USR-08`); gerente nas da filial; administrador em todas. Mudança de status só por estes serviços.

| Serviço | O que faz |
| --- | --- |
| `simular(dados)` | só o `calculo`, sem gravar: preço final, saldo, parcelas, comissão, `precisa_aprovacao`, mensagens dos campos. Usado pela tela a cada mudança (ADR 0005). |
| `criar(dados, por, acao)` | veículo `a_venda` na filial (`VEN-01`; 409 `VEN-10` se já tem venda aberta e a ação abre), vendedor = quem cria (`FIN-09`), preço de tabela copiado. `interessado`: aceita cliente incompleto ou só nome e celular. `enviar` e `pedir_aprovacao` pedem cliente cadastrado (CPF, `VEN-14`) e forma completa. |
| `editar(venda, dados, por)` | só antes da assinatura (com contrato vigente: 409 `VEN-06` "Cancele a assinatura para mudar a proposta."). Em `aguardando_aprovacao`, não edita (409 `APR-01`). Desconto acima do limite numa edição não grava: 400 no campo `desconto_pct` com "Acima de 5% precisa do gerente. Use Pedir aprovação." Recalcula a comissão pendente, se houver (`FIN-09`). |
| `enviar_proposta(venda, por)` | `interessado` → `proposta`, ou reenvio em `proposta`/`negociacao`. Grava `proposta_enviada_em` (e `entrou_proposta_em` na primeira vez) e agenda o e-mail com o PDF depois do commit (item 8). |
| `registrar_resposta(venda, por, nota)` | `proposta` → `negociacao`. A nota (texto até 300) vai só para a auditoria nesta fase; "Registrar contato" fica de fora (`VEN-16`). |
| `pedir_desconto(venda, pct, motivo, por)` | abre o `APR-01` por `comum.aprovacoes.pedir` (origem `venda`, `pct`, `valor_centavos` = preço final pedido, `resumo` com veículo, tabela, desconto, final, forma), grava `status_antes_aprovacao`, `aprovacao = pendente`, vai para `aguardando_aprovacao`, e **lança a comissão `pendente`** sobre o preço final pedido (`FIN-09`, `FIN-10`: R$ 632,04 na VEN-0177). |
| `aplicar_decisao_desconto(venda_id, status, motivo)` | assinante de `aprovacoes.pedido_decidido`. Aprovado: `desconto_aprovado_pct = pct`, volta ao estado de antes (de `interessado`, `proposta` e envia). Recusado: `desconto_pct = 0`, recalcula preço e comissão pendente, grava `motivo_recusa`, volta ao estado de antes e avisa o vendedor no sino. Cancelado (o vendedor desistiu do pedido): como recusado, sem motivo. Idempotente por `aprovacao == pendente`. |
| `preparar_assinatura(venda, por)` | a etapa "Assinatura" (item 6). |
| `cancelar_assinatura(venda, por)` | contrato `gerado`/`enviado` → `cancelado` e conta da entrada aberta → `cancelada`, para voltar a negociar. Com a entrada já paga: 409 `VEN-06` "A entrada já foi paga. Para desfazer, marque a venda como perdida." |
| `registrar_contrato_assinado`, `registrar_entrada_paga` | assinantes; gravam a data e chamam `concluir_se_pronto`. |
| `concluir_se_pronto(venda_id)` | com `contrato_assinado_em` e (`entrada_paga_em` ou sem conta de entrada, quando a troca cobre a entrada) e status `proposta`/`negociacao`: conclui (item 7). Idempotente. |
| `perder(venda, motivo, por)` | qualquer estado aberto → `perdida`, motivo obrigatório. Cancela o pedido pendente (`aprovacoes.cancelar_pendentes`), o contrato não assinado e a conta da entrada aberta; estorna a comissão pendente (`FIN-09`). Com a entrada **paga**, só gerente ou administrador (403 para o vendedor), e o valor vira `Reembolso` "a fazer" por `financeiro.devolver_ao_cliente` (forma Pix, motivo "Venda perdida com a entrada paga", `DEV-02`). |
| `vencer_propostas()` | rotina diária (item 9). |
| `cancelar(venda, motivo, por)` | **fase 2** (item 10). Até lá continua recusando a quitação (409 `VEN-11`) e responde 409 `VEN-07` "O cancelamento de venda ainda não está disponível." para a de balcão. |
| `registrar_transferencia` | passa a aceitar a venda de balcão `vendida` (`VEN-17`); o resto igual. |
| `definir_meta(vendedor, filial, mes, valor, por)` | gerente da filial ou administrador; `valor = None` tira a meta. |

`criar_venda_da_quitacao`, `data_da_quitacao`, o aviso da quitação e `destinatarios_da_transferencia` **não mudam** (`VEN-11`).

### 6. Contrato de compra e venda e a etapa "Assinatura"

- **Tipo de modelo:** `contratos.Finalidade.VENDA` já existe (`"venda"`); muda só o rótulo para "Compra e venda" (migration `contratos` 00NN de `choices`, sem dado). `contratos.prontos` ganha o pronto `compra_venda` (finalidade `venda`), com os marcadores da venda e a cláusula de multa e juros (`FIN-03`). O **texto** do pronto é do dono com o advogado (`VEN-15`): o backend escreve um rascunho só com marcadores e cláusulas mínimas, marcado no PR para o dono revisar, e o pronto nunca se publica sozinho.
- **Marcadores `venda.*`** (lista fechada em `contratos.marcadores`, aceitos só na finalidade `venda`): `venda.codigo`, `venda.preco_tabela`, `venda.desconto`, `venda.preco_final`, `venda.forma`, `venda.entrada`, `venda.parcelas` ("12 parcelas mensais de R$ 1.339,00"), `venda.juros_mes`, `venda.primeiro_vencimento` ("um mês depois da conclusão da venda", porque a data só existe em `vendida`) e, na fase 2, `venda.troca`. Os de cliente, veículo, empresa e filial são os que já existem. `vendas` registra o montador em `contratos.origens.registrar("venda", ...)` no `ready()`, o que liga a prévia com dados reais.
- **Sem modelo publicado** (`IMP-04`, `VEN-15`): `contratos.services.sem_modelo_publicado` passa a receber a finalidade; para `venda`: 422 `{"codigo": "IMP-04", "mensagem": "Publique um modelo de contrato de compra e venda antes de concluir a venda.", "link": "/configuracoes/contratos"}`. A trava do "último modelo publicado não se arquiva" continua só para a locação, como diz a `IMP-04`.
- **`preparar_assinatura`** (botão da etapa "Documentos" para "Assinatura"): exige status `proposta` ou `negociacao`, desconto dentro do limite (ou aprovado), cliente sem pendência da `CLI-03` (`clientes.selectors.pendencias` vazio; 422 `CLI-03` "Complete o cadastro do cliente antes da assinatura.") e não bloqueado nem inativo (409 `CLI-05`), veículo ainda `a_venda`. Na mesma transação:
  1. `contratos.services.gerar(DadosDoContrato(origem_tipo="venda", finalidade="venda", ...))`; o PDF e o link saem depois do commit, pelo e-mail, com "Copiar link para assinar", exatamente como na retirada (o envio, o reenvio, o link copiado e a assinatura são os da locação, sem código novo em `contratos` além do item acima);
  2. a conta da entrada por `financeiro.criar_contas`: tipo novo `TipoConta.ENTRADA` ("Entrada"; observação "Pagamento à vista" na forma à vista), valor = `entrada_centavos`, vencimento = hoje no fuso da filial, com `aguarda_retirada = True`. O campo, criado para a locação (ADR 0035), quer dizer "a conta espera o fato que a libera": não fica `vence_hoje` nem `atrasada`, não entra na régua (`AUT-03`) nem no bloqueio (`CLI-05`) e não tem multa nem juros. Assim a entrada de uma venda que não fecha não cobra o cliente. Paga-se por Pix ou boleto do parceiro (`gerar_cobranca`) ou no caixa (`receber`), pelas rotas do financeiro que já existem. Entrada de valor zero (a troca cobre tudo) não gera conta (`criar_contas` já pula), e a condição fica só a assinatura.
- O contrato não muda depois de gerado (`LOC-15`); para mudar a proposta, `cancelar_assinatura` (item 5).

### 7. Ao virar `vendida` (`VEN-06`, `VEN-15`)

`concluir_se_pronto`, na transação do evento que completou a segunda condição:

1. `vendida_em = agora`; `transicionar(venda, VENDIDA, regra="VEN-06")`.
2. Veículo `a_venda` → `vendido` por `veiculos.services.transicionar` com a origem na venda (sai dos indicadores da frota); os outros `interessado` do veículo → `perdida` "veículo vendido" (`_perder_interessados`, `VEN-10`, já existe).
3. Parcelas (forma `entrada_parcelas`): `financeiro.criar_contas` tipo `parcela`, `numero_parcela` 1..n, `total_parcelas = n`, vencimentos do `calculo.vencimentos` a partir da data local de `vendida_em`, valor da `parcela_centavos` (a última com a diferença). Nascem normais (sem `aguarda_retirada`): seguem a régua (`AUT-03`) e a multa e os juros da `FIN-03`, como as da locação; a cláusula de juros vem do contrato.
4. Comissão (item 11): a pendente é recalculada sobre o preço final e confirmada; sem pendente, nasce e é confirmada na hora.
5. Troca (**fase 2**): `veiculos.services.receber_na_troca(chassi, dados)` (item 12).
6. Transferência: `painel.renovar()` e, depois do commit, o aviso aos gerentes ativos da filial e aos administradores ativos, pela mesma função da `VEN-11` (`destinatarios_da_transferencia`), com `tipo = "transferencia_venda"`, chave `venda-transferencia-<id>`, link `/vendas/<id>`. O texto segue o da quitação, com o código e a data da venda: "Fazer a transferência no Detran: RTA-2C55 para Diego Martins. VEN-0177 vendida em 07/10/2026." A `VEN-17` não traz o texto; este é a proposta do arquiteto, e o Produto confirma ou troca na T-502.

Erro em qualquer passo desfaz tudo, inclusive a baixa da entrada ou a assinatura que dispararam o evento (ADR 0011). Por isso o passo 2 confere antes que o veículo ainda está `a_venda`; se não estiver (caso que a trava do item 1 impede), a conclusão não acontece, a venda fica como está e o Sentry recebe o erro, mas a baixa e a assinatura gravam: o assinante captura só esse caso (`VeiculoForaDoEstoque`) e avisa os gerentes, em vez de desfazer o pagamento do cliente.

### 8. Envio da proposta e o "Recibo" (`VEN-15`)

- PDF da proposta montado em `vendas` (texto fixo do sistema, com a marca da locadora, pelo `contratos.pdf.gerar` que já existe): veículo, preço de tabela, desconto, preço final, forma, entrada, parcelas e, na fase 2, troca. Guardado no armazenamento privado, sem versão (o envio novo substitui).
- E-mail ao cliente com o PDF anexo depois do commit (`notificacoes`, só e-mail na fase 1, sem WhatsApp do sistema). Sem e-mail no cadastro, a venda muda de estado do mesmo jeito e a resposta traz `email_enviado: false`, para a tela mostrar "Copiar link".
- "Copiar link": `POST /api/vendas/{id}/proposta/link/` gera um token como o da assinatura (`S-15`: só o hash guardado, 7 dias, um vivo por venda) e a rota pública `GET /api/publico/propostas/{token}/` devolve o PDF. A Segurança revisa na T-502.
- O "Recibo" da venda `vendida` vira "Contrato" e abre o PDF assinado pela rota de contratos que já existe; não há recibo à parte.

### 9. Vencimento da proposta (`VEN-13`, `AUT-19`)

`AUT-19`: tarefa `vendas_vencer_propostas`, no Celery Beat às 02:40 (de madrugada), por empresa com `para_cada_empresa` (ADR 0012), só nas que têm o recurso `vendas_comissoes` (ADR 0024). Leva a `perdida`, com o motivo "proposta vencida", a venda `proposta` cuja data local do último envio + 7 dias ≤ hoje (enviada em 07 out, perdida na rodada de 14 out). `interessado`, `negociacao` e `aguardando_aprovacao` não vencem. O ator é o Sistema; idempotente, e a rodada perdida pega as vencidas na próxima (`AUT-19`).

### 10. Cancelamento (fase 2, `VEN-07`, `VEN-05`)

`cancelar(venda, motivo, por)`, só gerente da filial ou administrador, sem prazo no sistema, numa transação:

- contas abertas da venda → `cancelada` (`financeiro.cancelar_abertas`);
- valor devolvido = entrada e parcelas pagas + avaliação da troca → um `Reembolso` "a fazer" pela `devolver_ao_cliente`, motivo "Venda cancelada" (`DEV-02`); as contas pagas ficam pagas (registro financeiro pago não se edita);
- comissão: `pendente`/`confirmada` → `estornada`; `paga` fica `paga`, e nasce um abatimento (item 11);
- veículo `vendido` → `a_venda` (transição já existe); o veículo da troca fica na frota (`VEN-05`);
- contrato `assinado` → `cancelado`: `contratos` ganha essa passagem, só para `origem_tipo = "venda"`, por `cancelar_assinado(contrato, motivo)`, que guarda o PDF assinado e não mexe no token;
- a tarefa da transferência sai das pendentes (o índice já filtra `status = 'vendida'`);
- `cancelada_em`, `cancelada_por`, `motivo_cancelamento` (já existem).

### 11. Comissão de venda (`FIN-09`)

Fica em `financeiro.Comissao` (origem `venda`, regra `percentual_venda`, `pct` = `comissao_venda_pct`, `base_centavos` = preço final com a troca, sem juros; usuário = `Venda.vendedor`, que é quem criou).

- `financeiro.lancar_comissao` ganha `base_centavos` e `pct` opcionais (hoje grava `base = valor`); a locação continua chamando como hoje.
- Serviço novo `financeiro.recalcular_comissao(origem, *, base_centavos, valor_centavos)`: só a `pendente`, com auditoria; a confirmada não muda.
- Ciclo: pedido de desconto → `pendente`; preço muda (edição ou recusa) → recalculada; `perdida` → `estornada` (`estornar_comissao`, que já existe); `vendida` → recalculada e `confirmada`, paga no dia 5 do mês seguinte (`confirmar_comissao`, já existe); sem pedido, `lancar_comissao` + `confirmar_comissao` na conclusão. `tem_recurso("vendas_comissoes")` já é condição do lançamento (`PLT-12`).
- **Fase 2, abatimento da comissão paga:** `RegraComissao.ABATIMENTO_VENDA` ("Abatimento de venda cancelada"), valor positivo que a tela de pagamento subtrai do mês, nasce `confirmada` com `mes_pagamento` do próximo pagamento. O único `comissao_uma_por_origem` passa a incluir `regra`. O pagamento das comissões (`confirmada` → `paga`) ainda não existe no backend e é da tarefa da tela `Comissoes`.

### 12. Troca (fase 2, `VEN-05`, `VEI-07`, `VEN-05`)

- Antes de `vendida`, a troca é só dado da proposta: `troca_dados` (placa, chassi, marca, modelo, ano, km) e `troca_valor_centavos` (a avaliação digitada pelo vendedor, sem aprovação). O `calculo` a abate do saldo; acima do preço final: 400 no campo, "A troca não pode passar do preço da venda.".
- Na proposta, o chassi é conferido: de um veículo da empresa que não está `vendido` (está na frota): 409 `VEI-07` "Este chassi já está na frota."; `vendido`: será reaproveitado.
- Na conclusão (item 7, passo 5): `veiculos.services.receber_na_troca` (já existe) com a filial da venda, `valor_compra_centavos` = avaliação e data de compra = dia de `vendida`; o veículo entra `indisponivel` até a vistoria; `troca_veiculo` aponta para ele. `receber_na_troca` ganha os dois campos de compra no reaproveitamento (hoje só muda o status).

### 13. Funil, conversão, meta e números da lista (`VEN-08`, `VEN-09`, `VEN-12`)

`vendas/selectors.py`, sempre com `origem = 'balcao'`, por filial (todas, para quem vê todas, `USR-07`), datas no fuso `America/Sao_Paulo`; o vendedor vê só as dele (`USR-08`).

- **Funil do mês:** interessados = criadas no mês; proposta = `entrou_proposta_em` no mês; negociação = `entrou_negociacao_em` no mês; vendido = `vendida_em` no mês e `status = 'vendida'` hoje.
- **Conversão (30 dias):** vendidas (mesma regra, `vendida_em` nos últimos 30 dias) ÷ criadas nos últimos 30 dias, inteiro (33% = 4 ÷ 12).
- **Vendido no mês e ticket médio:** a soma e a conta da `VEN-12`. O selector do ticket médio que a T-487 deixou dizendo "Sem vendas" passa a ler daqui.
- **Em negociação:** soma do preço final e quantidade das vendas `proposta`, `negociacao` e `aguardando_aprovacao`. **Aguardando aprovação:** quantidade.
- **Meta:** do vendedor (a dele na filial) ou da filial (a soma); percentual = vendido ÷ meta, inteiro para baixo (62% de 31.200 ÷ 50.000); `faltam_dias` = dias corridos até o fim do mês; sem meta, `meta: null` e a tela mostra "Sem meta em outubro.".
- **Propostas para retornar:** abertas ordenadas por `ultimo_contato_em` crescente.

### 14. Rotas (em `apps/vendas/api`; contrato em `docs/api/vendas.md`, escrito pelo backend na primeira tarefa a partir daqui)

Todas com o recurso `vendas_comissoes` (403 `PLT-12` sem ele, ADR 0024), exceto a pública e a transferência pela locação, que ficam como estão. Vistoriador: 403. Financeiro: só leitura.

| Rota | Quem | O que faz |
| --- | --- | --- |
| `GET /api/vendas/` | administrador, gerente, vendedor (as dele), financeiro | filtros novos: `status`, `aba` (`abertas`, `minhas`, `aguardando`, `vendidas`), `mes`, `filial`; cada item traz `valor`, `forma_texto` ("entrada + 12×", "Pix à vista"), `situacao_texto` ("Aguardando gerente", "Proposta enviada"), `ultimo_contato_em`, `comissao_centavos` |
| `GET /api/vendas/{id}/` | idem | a venda inteira, com `calculo`, `aprovacao`, `contrato` (id, status, link de assinatura pelas rotas de contratos), `conta_entrada` (id, status, valor) e `acoes` (o que a pessoa pode fazer agora) |
| `POST /api/vendas/simular/` | quem cria venda | corpo da proposta; devolve o `calculo` e `precisa_aprovacao` (ADR 0005) |
| `POST /api/vendas/` | administrador, gerente, vendedor | `{ veiculo_id, cliente_id \| interessado: {nome, celular}, forma, desconto_pct, entrada_centavos, num_parcelas, acao: "interessado" \| "enviar" \| "pedir_aprovacao", motivo }` |
| `PATCH /api/vendas/{id}/` | idem | campos da proposta (item 5) |
| `POST /api/vendas/{id}/enviar/` | idem | envia ou reenvia a proposta; devolve `email_enviado` |
| `POST /api/vendas/{id}/proposta/link/` | idem | o link público da proposta (item 8) |
| `GET /api/publico/propostas/{token}/` | público | o PDF; 404 token desconhecido, 410 vencido |
| `POST /api/vendas/{id}/resposta/` | idem | `{ nota }`: `proposta` → `negociacao` |
| `POST /api/vendas/{id}/pedir-aprovacao/` | idem | `{ desconto_pct, motivo }` |
| (decisão) `POST /api/aprovacoes/{id}/aprovar/` e `/recusar/` | gerente, administrador | as rotas que já existem; o cartão do `Gerente` mostra o `resumo` da venda |
| `POST /api/vendas/{id}/assinatura/` | idem | `preparar_assinatura`; devolve contrato e conta da entrada |
| `DELETE /api/vendas/{id}/assinatura/` | idem | `cancelar_assinatura` |
| `POST /api/vendas/{id}/perder/` | idem (entrada paga: gerente, administrador) | `{ motivo }` |
| `POST /api/vendas/{id}/cancelar/` | gerente, administrador | **fase 2**; até lá, 409 (item 5) |
| `POST /api/vendas/{id}/transferencia/` | administrador, gerente da filial | `{ feita_em }`, para as duas origens; a rota da locação continua |
| `GET /api/vendas/resumo/?filial=&mes=` | administrador, gerente, vendedor (o dele), financeiro | funil, conversão, vendido, ticket, em negociação, aguardando, à venda, meta, transferências pendentes |
| `GET /api/vendas/metas/?filial=&mes=` | administrador, gerente | vendedores da filial com a meta de cada um e a soma |
| `PUT /api/vendas/metas/` | administrador, gerente da filial | `{ filial_id, mes, metas: [{ vendedor_id, valor_centavos \| null }] }` |

Erros de negócio com código: `VEN-01` (veículo fora de `a_venda`), `VEN-02` (desconto acima do limite numa edição), `VEN-06` (proposta com assinatura, entrada paga), `VEN-07`, `VEN-10`, `VEN-11`, `APR-01`, `CLI-03`, `CLI-05`, `IMP-04`, `VEI-07` (fase 2), `transicao_venda`.

### 15. Migrations

1. `vendas` 0002 (schema): campos e restrições do item 3, `MetaVenda`, índice da transferência com a condição nova. Sem dado a migrar (só existem vendas da quitação, que ficam com os campos novos nulos).
2. `financeiro` 00NN: `TipoConta.ENTRADA` (só `choices`). Fase 2: `RegraComissao.ABATIMENTO_VENDA` e o único com `regra`.
3. `empresas` 00NN: `ConfiguracaoEmpresa.juros_venda_mes_pct`.
4. `contratos` 00NN: rótulo da `Finalidade.VENDA`. Fase 2: nada no banco (a passagem `assinado` → `cancelado` é código).
5. Fase 2, `vendas` 0003: `troca_dados` e o `CHECK` da troca.

## Pontos em aberto da T-501: os 18 com o padrão A (confirmados pelo dono em 18 nov 2026)

| Ponto | Regra (PR #629) | Onde está no desenho |
| --- | --- | --- |
| 1 Passagens | `VEN-13`, `VEN-02` | item 2, `status_antes_aprovacao` |
| 2 Quando vira `vendida` | `VEN-15`, `VEN-06` | itens 6 e 7; a frase da tela `Venda` muda |
| 3 Modelo de compra e venda | `VEN-15`, `IMP-04` | item 6 |
| 4 Cliente e documentos | `VEN-14` | `cliente` nulo e `interessado_*` (item 3), `preparar_assinatura` (item 6) |
| 5 Cartão | `VEN-03`, `VEN-18` | fora; nenhuma forma nova |
| 6 Parcelas | `VEN-04` | `calculo` (item 4) e item 7, passo 3; `juros_venda_mes_pct` |
| 7 Limite do desconto | `VEN-02` | `LIMITE_DESCONTO_PCT` |
| 8 Troca | `VEN-05` | item 12 (fase 2) |
| 9 Troca na cancelada | `VEN-05`, `VEN-07` | item 10 (fase 2) |
| 10 Cancelamento | `VEN-07`, `FIN-09` | item 10 (fase 2) |
| 11 Vencimento | `VEN-13`, `AUT-19` | item 9 |
| 12 Último contato | `VEN-16` | `ultimo_contato_em` |
| 13 Funil | `VEN-08` | `entrou_*_em` e item 13 |
| 14 Meta | `VEN-09` | `MetaVenda` e item 13 |
| 15 Transferência | `VEN-17` | item 7, passo 6; índice e `registrar_transferencia` |
| 16 Comissão | `FIN-09` | item 11 |
| 17 Envio e "Recibo" | `VEN-15` | item 8 |
| 18 Financiamento | `VEN-03`, `VEN-18` | fase 3; `forma = financiamento` recusada até lá |

## Consequências

- A ordem dos apps não muda. `veiculos` ganha um registro de travas do estoque; `contratos` ganha a finalidade nos textos do `IMP-04`, os marcadores `venda.*` e, na fase 2, `cancelar_assinado`; `financeiro` ganha o tipo `entrada`, `recalcular_comissao` e os parâmetros de `lancar_comissao`.
- `aguarda_retirada` passa a valer para a entrada da venda. O nome fica (renomear mexeria na locação, no selector e nos testes sem ganho); o significado está documentado no model.
- A venda da quitação continua igual: mesmo serviço, mesmos `CHECK`, fora do funil, da meta, do ticket e da comissão; o índice da transferência continua cobrindo ela.
- O seed (T-504) cria as vendas de setembro e outubro pelos serviços (`criar` → `preparar_assinatura` → assinatura e pagamento pelos serviços de `contratos` e `financeiro`), com a data simulada, e a VEN-0177 parada em `aguardando_aprovacao` com a comissão pendente.

### Riscos

1. **Conclusão por evento.** A venda vira `vendida` dentro da transação da baixa ou da assinatura. Um erro de conclusão desfaria o pagamento do cliente; por isso o caso previsível (veículo fora do estoque) é capturado (item 7) e o resto precisa de teste de ponta a ponta no webhook do Pix e no caixa.
2. **Texto do contrato.** Sem o texto do dono e do advogado, o pronto é rascunho; a empresa que publicar o rascunho assina um contrato não revisado. O PR da T-502 não marca a tarefa como pronta para produção sem o texto.
3. **Link público da proposta.** Superfície nova sem login; mesmo padrão do link de assinatura, com revisão da Segurança.
4. **Downgrade com proposta enviada** já é recusado pela `PLT-12` (venda aberta); o interessado fica guardado e volta ao subir de plano.

## Fases e o que vai para a T-502

**Fase 1: fluxo, vendida, contrato, comissão, funil e meta.** É grande demais para um PR do backend; a quebra proposta (o orquestrador decide números e ordem):

- **1a. Estados, proposta e aprovação** (`vendas`, `financeiro`, `empresas`): migrations 1 a 3, `calculo.py` com os casos da VEN-0177, `simular`, `criar`, `editar`, `enviar_proposta` (só o estado e a data; o e-mail vem na 1c), `registrar_resposta`, `pedir_desconto`, `aplicar_decisao_desconto`, `perder` (sem o caso da entrada paga, que entra na 1b), `vencer_propostas` no Beat, comissão pendente e `recalcular_comissao`, trava do estoque em `veiculos`, rotas de lista, detalhe, simular, criar, editar, enviar, resposta, pedir aprovação e perder, `docs/api/vendas.md` (inteiro, com as rotas da 1b e da 1c marcadas como "a seguir"), OpenAPI. Regras `VEN-01`, `VEN-02`, `VEN-03`, `VEN-04`, `VEN-10`, `VEN-13`, `VEN-14` (a proposta pede o CPF), `VEN-16`, `VEN-18`, `AUT-19`, `APR-01`, `FIN-09`.
- **1b. Assinatura e `vendida`** (`vendas`, `contratos`, `financeiro`, `veiculos`): migration 4, pronto `compra_venda` (rascunho), marcadores e montador, `IMP-04` por finalidade, `TipoConta.ENTRADA`, `preparar_assinatura`, `cancelar_assinatura`, assinantes, `concluir_se_pronto` (parcelas, comissão confirmada, veículo `vendido`, `VEN-10`, transferência generalizada e aviso), `perder` com entrada paga, rotas de assinatura e transferência. Regras `VEN-06`, `VEN-04`, `VEN-14`, `VEN-15`, `VEN-17`, `FIN-09`, `IMP-04`, `CLI-03`, `CLI-05`. Depende da 1a.
- **1c. Envio, funil e meta** (`vendas`, `relatorios`): PDF e e-mail da proposta, link público, `MetaVenda` com as rotas, `resumo` (funil, conversão, meta, em negociação), ticket médio da `VEN-12` lendo as vendas. Regras `VEN-08`, `VEN-09`, `VEN-12`, `VEN-15` (envio). Depende da 1a; pode correr junto com a 1b.

**Fase 2: troca e cancelamento** (um PR do backend): migration 5, item 12, item 10, abatimento da comissão, `cancelar_assinado` em `contratos`, a rota de cancelar. Regras `VEN-05`, `VEN-07`, `VEI-07`, `DEV-02`, `FIN-09`.

**Fase 3: financiamento pelo banco parceiro.** Não há banco definido nem regra de aprovação e pagamento pelo banco (`VEN-18`). Precisa de regra do Produto e de outra ADR (integração externa). Até lá, `forma = financiamento` é recusada e a opção não aparece na tela.

### O que o design-system e o frontend (T-503) recebem

- Textos que mudam: a frase da etapa da tela `Venda` passa a "Depois de assinada e com a entrada paga, a venda gera as parcelas em Contas a receber, lança a comissão e tira o veículo da frota de locação."; "Recibo" vira "Contrato"; a VEN-0170 "cartão em 6×" vira "Pix à vista"; a opção "Financiamento" e a VEN-0176 "Banco analisando" saem (fase 3); a caixa "Cliente vai dar um veículo..." só na fase 2.
- Divergências da `Vendedor` (do PR #628): VEN-0177 com R$ 21.068,00, "Aguardando gerente", "há 1 h", sem troca; "Propostas" com o número de abertas; "faltam 24 dias" em 07 out.
- Estados que faltam desenhar: interessado rápido (nome e celular); a etapa "Assinatura" com contrato enviado, "Copiar link para assinar", entrada aguardando pagamento (Pix, boleto, caixa) e concluída; recusa do desconto com o motivo; "Registrar resposta do cliente"; "Marcar como perdida" com motivo; "Cancelar assinatura"; "Definir metas" (gerente e administrador, na `Vendas`); "Sem meta em outubro."; proposta sem e-mail do cliente ("Copiar link"); na fase 2, a troca e o cancelamento.
- A tela não calcula: preço final, saldo, parcelas, comissão e "precisa do gerente" vêm do `simular`; os textos de forma e situação vêm prontos na lista.

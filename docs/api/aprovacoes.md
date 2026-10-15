# Aprovações

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-236, descrição no pedido de despesa; T-201, números da `APR-12`, `resumo` e "Meus pedidos"); 07 out 2026 (T-043, mínimo para a fase 1), emendas de 09 out 2026 (T-088) · **App:** `aprovacoes` (schema da empresa) · **Regras:** APR-01 a APR-12, CLI-05, LOC-03, LOC-12, DEV-07, FIN-05, FIN-07, MAN-02, USR-07 · **ADR:** 0011 (origem genérica, evento `aprovacoes.pedido_decidido`), 0019 (porta `comum.aprovacoes`) · **Telas:** Aprovacoes (desktop e celular), Gerente (fase 2), e os avisos do sino · **Critérios:** `docs/qa/criterios/aprovacoes.md` (CA-APR-01 a 11)

Convenções gerais em `docs/api/README.md`. Modelo: `PedidoAprovacao` em `docs/decisoes/modelo-de-dados.md`.

> **O que mudou na T-201 (decisões do dono de 14 out 2026, D12, regras na T-190).** (1) A lista ganha os `indicadores` da `APR-12` (Esperando você, Aprovadas e Recusadas no mês, tempo médio, Descontos aprovados) e as contagens das abas; as abas Aprovadas e Recusadas passam a ser **do mês corrente**. (2) Cada pedido ganha o bloco `resumo`, com as células prontas do cartão da tela, montadas pela origem no pedido (seção "Resumo por tipo"). (3) "Meus pedidos" (`?minhas=true`) traz os pedidos da pessoa em qualquer status, com `pode_cancelar`. (4) O `valor_centavos` do `APR-01` passa a ser o desconto do período (preço de tabela − preço com desconto), o que a tela mostra e a `APR-12` soma. (5) O aviso das 4 horas (`APR-08`) é da fase 2: nenhum campo da API fala dele (CA-APR-09). Ver "O que muda para as tarefas" no fim.

Os pedidos **nascem** nos outros módulos (desconto e cancelamento em `locacoes.md`, desbloqueio em `clientes.md`, correção de km em `veiculos.md`, despesa e diferença de caixa em `financeiro.md`), sempre por `comum.aprovacoes.pedir` (ADR 0019). O endpoint da origem responde 202 `{ "pedido_aprovacao": { "id", "tipo", "status": "pendente" } }`; com um pedido igual ainda pendente, 409 `{ "codigo": "pedido_pendente", "detalhes": { "pedido_id" } }`. Aqui ficam só a lista e a decisão. A tela `Gerente` com aprovação de 1 toque (`APR-07`) e o lembrete de 4 horas úteis (`APR-08`) são da fase 2; os endpoints abaixo já servem a eles.

## Quem decide

| Tipo | O que | Quem aprova |
| --- | --- | --- |
| `APR-01` | desconto acima de 5% em locação (venda na fase 2) | gerente, administrador, ou quem tem `aprovar_desconto` |
| `APR-02` | cancelamento de locação | gerente, administrador, ou quem tem `cancelar_contrato` |
| `APR-03` | despesa ou orçamento de OS acima de R$ 500 | gerente, administrador |
| `APR-04` | diferença no fechamento do caixa | gerente, administrador |
| `APR-05` | desbloqueio manual de cliente (pedido do vendedor) | gerente, administrador |
| `APR-06` | correção de km para baixo | gerente, administrador |

- Quem pediu nunca decide o próprio pedido (`APR-09`): 403 `{ "codigo": "APR-09", "mensagem": "Outra pessoa precisa decidir este pedido" }`.
- Gerente decide pedidos das suas filiais; administrador, de todas.

## Representação

```json
{
  "id": 91, "tipo": "APR-03", "status": "pendente",
  "titulo": "Despesa de R$ 1.200,00", "detalhe": "Pneus (2 unidades) · PMZ-3E17",
  "origem": { "tipo": "despesa", "id": 801, "codigo": null },
  "filial": { "id": 1, "nome": "Filial Centro" },
  "solicitante": { "id": 4, "nome": "João Silva" }, "pedido_em": "...", "motivo_pedido": null,
  "valor_centavos": 120000, "pct": null,
  "decidido_por": null, "decidido_em": null, "motivo_recusa": null,
  "resumo": {
    "celulas": [
      { "rotulo": "Categoria", "valor": "Manutenção" },
      { "rotulo": "Veículo", "valor": "Honda Pop 110i · PMZ-3E17" },
      { "rotulo": "Valor", "valor": "R$ 1.200,00" },
      { "rotulo": "Vencimento", "valor": "15 out" }
    ],
    "nota": "Acima de R$ 500 precisa de aprovação. Aprovada, vai para o financeiro pagar."
  },
  "pode_decidir": true,
  "pode_cancelar": false
}
```
`titulo` e `detalhe` são textos prontos da API; o vistoriador nunca vê pedidos com valor.
- `resumo` (T-201): as células do cartão do pedido, na ordem da tela, e uma nota opcional. Textos prontos, com dinheiro, datas e km já formatados: a tela só desenha (CA-APR-10). Montado pela origem no momento do pedido e guardado (`PedidoAprovacao.resumo`): mostra o que valia quando o pedido foi feito, como o `titulo`. Pedido de antes da T-201 vem com `resumo: null`, e a tela mostra só `titulo` e `detalhe`. Células por tipo em "Resumo por tipo".
- `pode_cancelar`: `true` só para quem fez o pedido, com ele `pendente` ("Meus pedidos").

## GET /api/aprovacoes/
Query: `?status=pendente|aprovado|recusado|cancelado` (padrão `pendente`), `?tipo=`, `?minhas=true` (pedidos que eu fiz).
200 (Rodrigo, Filial Centro, 07 out, caso "Números da tela Aprovações em 07 out", CA-APR-01):
```json
{
  "indicadores": {
    "mes": "2026-10",
    "esperando": { "quantidade": 2, "mais_antigo_em": "2026-10-07T11:55:00Z", "contexto": "mais antigo há 2 h" },
    "aprovadas": { "titulo": "Aprovadas em outubro", "quantidade": 2, "tempo_medio_min": 90, "contexto": "tempo médio de 1 h 30 min" },
    "recusadas": { "titulo": "Recusadas em outubro", "quantidade": 0, "contexto": "sempre com motivo" },
    "descontos": { "titulo": "Descontos aprovados", "valor_centavos": 0, "quantidade": 0, "contexto": "em 0 pedidos" }
  },
  "contagens": { "pendente": 2, "aprovado": 2, "recusado": 0, "minhas_pendentes": 0 },
  "resultados": [ ... ]
}
```
A contagem `pendente` continua alimentando o sino do gerente. `indicadores` e `contagens` não dependem do `?status=`, do `?tipo=` nem do `?minhas=` (são da tela inteira); a lista, sim. O `mais_antigo_em` do exemplo é ilustrativo: vale a hora em que o seed grava o pedido mais antigo.

**Escopo (`APR-12`, `USR-07`).** Tudo conta os pedidos que a pessoa decide (tabela "Quem decide": os tipos dela), na filial do `X-Filial` (com `todas`, a soma das filiais do escopo, CA-APR-08), sem os pedidos que ela mesma fez (`APR-09`, CA-APR-05). Pedido `cancelado` não entra em número nenhum (CA-APR-04). Quem não decide nenhum tipo (vendedor sem extra, vistoriador, financeiro) recebe tudo zerado e lista vazia, 200; "Meus pedidos" continua funcionando para essa pessoa.

**Mês (`APR-12`).** O mês corrente em `America/Sao_Paulo`, pelo dia da decisão (`decidido_em`): pedido feito em 30 set e aprovado em 01 out conta em outubro (CA-APR-06). Na virada do mês, Aprovadas e Recusadas voltam a zero; Esperando você não depende do mês.

**`indicadores`:**
- `esperando`: os `pendente` do escopo, de qualquer mês. `mais_antigo_em` é o `pedido_em` do mais antigo; `contexto` é "mais antigo há {tempo}", com o tempo corrido até agora: abaixo de 1 hora "há 40 min", abaixo de 24 horas "há 2 h" (horas inteiras, para baixo), depois "há 3 dias". Sem pendentes: `quantidade` 0, `mais_antigo_em` e `contexto` `null`.
- `aprovadas`: os `aprovado` do escopo decididos no mês. `tempo_medio_min` é a média de (`decidido_em` − `pedido_em`) desses pedidos, em minutos corridos, arredondada para o minuto inteiro mais próximo (meio minuto sobe). `contexto`: "tempo médio de {h} h {mm} min" ("1 h 30 min"; abaixo de 1 hora, "40 min"; hora cheia, "2 h"). Sem aprovados: `tempo_medio_min` e `contexto` `null`, nunca "0 min" (CA-APR-07). Ex.: (40 + 140) ÷ 2 = 90 → "1 h 30 min"; com um terceiro de 40 min, 220 ÷ 3 = 73,3 → 73 → "1 h 13 min" (CA-APR-02). Recusados não entram no tempo médio (CA-APR-03).
- `recusadas`: os `recusado` do escopo decididos no mês. `contexto` fixo "sempre com motivo" (`APR-07`).
- `descontos`: os `APR-01` `aprovado` no mês: `valor_centavos` é a soma dos `valor_centavos` deles (o desconto do período, abaixo) e `quantidade` quantos são; `contexto` "em 1 pedido" ou "em {n} pedidos" ("em 0 pedidos" sem nenhum). Ex.: CA-APR-02 → 2632, "em 1 pedido".
- `titulo` vem com o nome do mês ("Aprovadas em outubro"). Valores em reais a tela formata a partir dos centavos, como em todo contrato.

**`contagens` (as abas):** `pendente` = `esperando.quantidade`; `aprovado` = `aprovadas.quantidade`; `recusado` = `recusadas.quantidade`; `minhas_pendentes` = os pedidos da pessoa ainda `pendente` (a aba "Meus pedidos" não mostra número na tela de referência; o campo fica para o sino de quem pede).

**Lista por aba:**
- `?status=pendente` (padrão, aba Pendentes): os mesmos de "Esperando você", do mais antigo para o mais novo (quem espera há mais tempo primeiro).
- `?status=aprovado` e `?status=recusado` (abas Aprovadas e Recusadas): os decididos **no mês corrente**, do mais recente para o mais antigo (`decidido_em`). Mudou na T-201: antes vinham de qualquer mês. `?status=cancelado` sem `?minhas` continua respondendo (do mês), mas nenhuma aba usa.
- `?minhas=true` (aba Meus pedidos): os pedidos que a pessoa fez, de qualquer mês e em qualquer status, os `pendente` primeiro (do mais antigo), depois os outros pela data da decisão ou do cancelamento, do mais recente; `?status=` filtra, se vier. Vem com `pode_decidir: false` e `pode_cancelar` (`true` no `pendente`); o cancelado aparece aqui como cancelado (CA-APR-04). Escopo de filial: o do `X-Filial`, como o resto.
- Paginação por cursor (25), como hoje. `?tipo=` filtra qualquer aba ("Todos os tipos" na tela).

## POST /api/aprovacoes/{id}/aprovar/
Corpo: `{ motivo? }`. 200: pedido `aprovado`. O `motivo` da aprovação vai para a auditoria e para o evento; o pedido guarda só `motivo_recusa`. Publica `aprovacoes.pedido_decidido`, e o app da origem aplica o efeito na mesma transação (despesa → `a_pagar`; caixa → `fechado` com a diferença; cliente → desbloqueado; km corrigido; desconto aplicado; cancelamento feito).

## POST /api/aprovacoes/{id}/recusar/
Corpo: `{ motivo }` (obrigatório, `APR-07`). 200: `recusado`. A origem volta ao estado anterior (despesa → `recusada`; caixa → `aberto`; desconto → 0) e quem pediu é avisado com o motivo.

## POST /api/aprovacoes/{id}/cancelar/
Quem pediu desiste. 200: `cancelado`; a origem volta ao estado anterior. Outra pessoa: 403 `{ "codigo": "so_quem_pediu", "mensagem": "Só quem fez o pedido pode cancelar" }`. No pedido cancelado, `decidido_por` fica `null` (o `CHECK APR-09` não deixa ser quem pediu).

Erros comuns: 409 `transicao_pedido` em pedido já decidido; 403 `APR-09`; 404 fora do escopo de filial. Todo pedido, aprovação e recusa entra na auditoria (`APR-10`).

## Resumo por tipo (T-201)

As células do cartão de cada pedido, na ordem da tela. A origem monta o `resumo` com os números que ela já calcula para o pedido e passa em `comum.aprovacoes.pedir(..., resumo=...)`; `aprovacoes` só guarda e devolve (ADR 0019: aprovações não lê o model de outro app). Dinheiro em "R$ 1.234,56", datas curtas ("15 out"), km com ponto de milhar ("12.480 km"). Célula sem valor não vem (sem célula vazia). Nenhum CPF, CNH nem dado de contato de cliente vai no `resumo`. Nenhum texto depende do gênero de alguém: os textos usam o nome sem artigo.

| Tipo | Quem monta | Células (`rotulo`: `valor`) | `nota` |
| --- | --- | --- | --- |
| `APR-01` em locação | `locacoes` | "Preço de tabela": preço do período sem desconto ("R$ 329,00"); "Com desconto": o mesmo período com o desconto ("R$ 302,68"); "Desconto": "R$ 26,32 · 8%" | "O limite de {primeiro nome de quem pediu} é 5%." (`LOC-03`; "O limite de Bruna é 5%.", CA-APR-10) |
| `APR-01` em venda · fase 2 | `vendas` | "Preço de tabela", "Com desconto", "Desconto" como acima; "Pagamento" ("R$ 5.000 + 12 × R$ 1.339,00") | o limite, como acima, e "A comissão prevista é {valor} ({pct})." |
| `APR-02` depois da retirada | `locacoes` | "Plano": "{modelo} · {periodicidade} {preço do período}" ("NMax 160 · mensal R$ 1.590,00"); "Dias restantes": "{n} de {dias do período} · até {fim do período}" ("8 de 30 · até 15 out"); "Multa (20%)": "R$ 84,80"; "A devolver" ("R$ 286,20") ou "A cobrar", quando o saldo é contra o cliente (`LOC-13`) | "Valores estimados para {dia pedido}; o acerto final é feito no dia da devolução. Ao aprovar, a locação vai para a devolução: vistoria, acerto e devolução da caução." (`DEV-07`) |
| `APR-02` antes da retirada | `locacoes` | "Plano"; "Multa": "Sem multa, antes da retirada"; "A devolver": o que foi pago | "Ao aprovar, a locação é cancelada e o que foi pago volta." |
| `APR-02` em diária | `locacoes` | "Plano"; "Dias usados": "3 de 5"; "Multa": "Sem multa, diária"; "A devolver": "R$ 89,80" | a mesma nota da estimativa |
| `APR-03` despesa | `financeiro` | "Categoria" ("Manutenção"); "Descrição": a descrição da despesa ("Pneus (2)"); "Veículo": "{modelo} · {placa}" ("Honda Pop 110i · PMZ-3E17"), só com veículo; "Valor" ("R$ 1.200,00"); "Vencimento" ("07 out") | "Acima de R$ 500 precisa de aprovação. Aprovada, vai para o financeiro pagar." (`FIN-05`) |
| `APR-03` orçamento de OS | `manutencao` | "OS" ("OS-118"); "Veículo"; "Orçamento" ("R$ 1.200,00") | "Aprovado, a OS pode ser executada." (`MAN-02`) |
| `APR-04` | `financeiro` | "Esperado" ("R$ 1.203,50"); "Contado" ("R$ 1.200,00"); "Diferença": "falta de R$ 3,50" ou "sobra de R$ 3,50" | "Aprovada, o caixa fecha com a diferença registrada." |
| `APR-05` | `clientes` | "Bloqueio": "Automático · {n} dias de atraso" (os dias do pedido, `CLI-05`) ou "Manual · {motivo do bloqueio}"; "Contas": "Em dia" ou "{n} em atraso · {valor}" ("1 em atraso · R$ 1.347,00") | "Aprovado, o cadastro volta a ativo." |
| `APR-06` | `veiculos` | "Km atual" ("12.480 km", o `km_anterior`); "Km pedido" ("12.408 km"); "Diferença" ("−72 km") | `null` (o motivo de quem pediu já vem em `motivo_pedido`) |

- **Fornecedor e forma na despesa (`APR-03`).** Sem as duas células: a despesa não tem fornecedor (`FIN-05`, `FIN-06`) e só tem forma quando é paga. Decisão do dono de 15 out 2026 (T-235, opção A, CA-APR-11): o cartão mostra categoria, descrição, veículo, valor e vencimento; a tela de referência perde "Fornecedor" e "15 out · boleto" na T-237. A descrição entrou na T-236. Pedido de despesa já aberto com o `resumo` antigo (sem a descrição) continua como foi gravado (valores congelados, abaixo); o seed é recriado. Teste `test_apr_03_resumo_da_despesa` (CA-APR-11): os pneus do seed com Manutenção, "Pneus (2)", PMZ-3E17, R$ 1.200,00 e 07 out, sem fornecedor nem forma.
- **Valores congelados.** O `resumo` é do momento do pedido, como a multa do `APR-02` (já congelada em `dados`). Se a origem muda de forma que o pedido perde o sentido (cliente que quitou e saiu do bloqueio sozinho, `CLI-05`; locação cancelada), a origem cancela o pedido por `cancelar_pendentes`, como já está acima; o `resumo` não é refeito. No `APR-06`, se o km mudou depois do pedido, aprovar continua recusado com 409 `km_mudou` (`APR-11`).
- **Desconto do `APR-01` (`valor_centavos`).** É o desconto de um período: preço de tabela do período − preço com desconto do mesmo período (R$ 329,00 − R$ 302,68 = R$ 26,32), igual à célula "Desconto" e ao que a `APR-12` soma em Descontos aprovados. Antes, a locação mandava o desconto total de todos os períodos. Na venda (fase 2), é o desconto sobre o preço da venda.

## Interface interna para os outros apps (não é HTTP, ADR 0019)

| Função | Uso |
| --- | --- |
| `comum.aprovacoes.pedir(tipo, origem_tipo, origem_id, origem_codigo, filial_id, solicitante, titulo, detalhe, motivo?, valor_centavos?, pct?, dados?, resumo?) -> PedidoRef` | `resumo` (T-201): `comum.aprovacoes.Resumo(celulas: list[tuple[str, str]], nota: str \| None)`, guardado como `{ "celulas": [{ "rotulo", "valor" }], "nota" }`; opcional na assinatura para não quebrar quem chama, mas toda origem passa a mandar (seção "Resumo por tipo"). Abre o pedido na transação de quem chama, com auditoria (`APR-10`) e aviso ao gerente depois do commit. Levanta `PedidoPendente` (409 `pedido_pendente`) se já houver um `pendente` igual. Implementada por `aprovacoes.services.pedir`, registrada no `ready()`. |
| `comum.aprovacoes.pendente(tipo, origem_tipo, origem_id) -> PedidoRef \| None` | Para a representação da origem mostrar o pedido em aberto. |
| `comum.aprovacoes.cancelar_pendentes(origem_tipo, origem_id, motivo) -> int` | A origem deixou de existir ou mudou de forma que o pedido não faz mais sentido (ex.: locação cancelada com desconto pendente). Pedidos ficam `cancelado` e publicam `pedido_decidido`. |
| evento `aprovacoes.pedido_decidido` | `pedido_id`, `tipo`, `status` (`aprovado`, `recusado`, `cancelado`), `origem_tipo`, `origem_id`, `dados`, `decidido_por_id`, `motivo`, `motivo_pedido`. `decidido_por_id` é quem pediu no `cancelar` e `null` em `cancelar_pendentes`. `motivo_pedido` é o motivo de quem pediu (no `APR-06`, vira o motivo da leitura de correção). Cada app de origem assina em `<app>/eventos.py` e aplica o efeito pelo próprio serviço, na mesma transação. |

`dados` por tipo (chaves fixas, sem dado pessoal):

| Tipo | Origem | `dados` |
| --- | --- | --- |
| `APR-01` | `locacao` ou `venda` | `{ "desconto_pct": "8.00" }` (e `pct` preenchido) |
| `APR-02` | `locacao` | `{ "multa_centavos": 8480 }` (congelada no pedido, `LOC-12`) |
| `APR-03` | `despesa` ou `ordem_servico` | `{}` (e `valor_centavos` preenchido) |
| `APR-04` | `caixa` | `{ "diferenca_centavos": -1200 }` |
| `APR-05` | `cliente` | `{}` |
| `APR-06` | `veiculo` | `{ "km_novo": 3400, "km_anterior": 3500 }` |

## O que muda para as tarefas (T-201)

- **T-202 (backend):**
  - `aprovacoes`: campo `PedidoAprovacao.resumo` (JSON, padrão `{}`; `{}` sai `null`) e o índice `(filial, status, decidido_em)`; `Resumo` e o parâmetro `resumo` na porta `comum.aprovacoes.pedir`; `indicadores` e as `contagens` novas no `GET`; Aprovadas e Recusadas do mês corrente; `?minhas=true` em qualquer status, com `pode_cancelar`. Os números ficam em `aprovacoes.selectors` (uma consulta agregada por indicador, sem laço em Python). Testes `test_apr_12_numeros_do_seed` (CA-APR-01), `test_apr_12_desconto_aprovado` (CA-APR-02), `test_apr_12_recusado` (CA-APR-03), `test_apr_12_cancelado_nao_conta` (CA-APR-04), `test_apr_12_sem_os_proprios` (CA-APR-05), `test_apr_12_mes_pela_decisao` (CA-APR-06), `test_apr_12_sem_aprovados` (CA-APR-07), `test_apr_12_filial_do_seletor` (CA-APR-08).
  - Origens: cada `pedir` manda o `resumo` da tabela (`locacoes` no `_pedir_desconto` e no pedido de cancelamento; `financeiro` na despesa e no caixa; `manutencao` no orçamento, quando chamar; `clientes` no desbloqueio; `veiculos` na correção de km). `locacoes._pedir_desconto` passa a mandar em `valor_centavos` o desconto do período. Teste `test_apr_01_resumo_do_desconto` (CA-APR-10).
  - Seed: os dois pedidos aprovados do caso "Números da tela Aprovações em 07 out" com as horas (aluguel do ponto 05 out 08:30 → 09:10; rastreadores 02 out 10:00 → 12:20, aprovados por Rodrigo) e os pendentes, todos com `resumo`, criados pelos serviços (com o relógio do seed), não por `create()` direto.
- **T-203 (frontend):** os quatro indicadores e os números das abas pelo que vier em `indicadores` e `contagens`; as células e a nota do `resumo` (sem conta na tela); "Meus pedidos" com "Cancelar pedido" quando `pode_cancelar`; sem a frase das 4 horas; "Ver proposta" some até a venda ter tela; "Ver locação" e "Ver despesa" pela `origem`. CA-APR-01 a 10.
- **T-204 (qa):** CA-APR-10 com "O limite de Bruna é 5%." (sem artigo: a API não sabe o gênero de ninguém); seed com as horas dos pedidos.

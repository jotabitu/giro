# Referência de preço FIPE pela Parallelum, com rotina mensal

**Status:** aceita · 05 nov 2026 · T-422 · revista pela segurança em 05 nov 2026 (PR #480, `tarefas/handoffs/T-422-seguranca.md`; item 9) e com os textos do produto (PR #481, `tarefas/handoffs/T-422-produto-textos.md`) (regras: `VEN-01`, `VEI-08`; decisões do dono de 29 out 2026) · provisória até o contrato com a FIPE (T-338) · complementa a 0031 (agora com preço e com o servidor chamando a API) e detalha a 0011 e a 0012

## Contexto

A ADR 0031 trouxe da API aberta da Parallelum só a lista de marcas e modelos, gerada fora do servidor e versionada num CSV. O veículo já tem `referencia_fipe_centavos`, preenchido à mão ao colocar à venda (`VEN-01`), e o cadastro mostra "A consulta FIPE ainda não está disponível".

O dono decidiu em 29 out 2026: o servidor consulta a Parallelum **sem token**, uma vez por mês, e atualiza a referência de todos os veículos ativos; o veículo guarda o código FIPE e o mês do preço; a consulta por placa fica pronta, desligada por padrão. O risco de licença é o mesmo aceito na 0031, agora com preço.

Medido em 05 nov 2026, sem token (poucos pedidos, à mão):

- `GET https://fipe.parallelum.com.br/api/v2/references` → `[{ "code": "339", "month": "novembro/2026" }, ...]`.
- `GET /motorcycles/811134-0/years` → `[{ "code": "2016-5", "name": "2016 Flex" }, { "code": "2017-5", "name": "2017 Flex" }]`.
- `GET /motorcycles/811134-0/years/2017-5?reference=338` → `{ "price": "R$ 13.023,00", "brand": "HONDA", "model": "CG 160 FAN ESDi FLEXONE", "modelYear": 2017, "fuel": "Flex", "codeFipe": "811134-0", "referenceMonth": "outubro de 2026", ... }`.
- As listas de modelos (`/brands/{id}/models`) trazem o id do modelo (`7329`), não o código FIPE; o código FIPE só vem na resposta do preço.
- Cabeçalhos `x-ratelimit-limit`, `x-ratelimit-remaining` e `x-ratelimit-reset` (segundos até zerar). O limite visto foi 500 na maioria das respostas e 1.000 numa delas: a rotina lê o cabeçalho e não confia num número fixo.

Os pontos caros de desfazer: onde fica o preço que vale para todas as empresas, como a rotina passa pelas empresas sem quebrar o isolamento e a ordem dos apps, e o que o veículo guarda.

## Decisão

### 1. O cliente, sem dependência nova

`backend/integracoes/fipe/`, no padrão do `cep` e do `whatsapp`: um `Protocol` com `referencias()`, `anos_do_modelo(tipo, marca_id, modelo_id)`, `anos_do_codigo(tipo, codigo_fipe)`, `preco(tipo, codigo_fipe, ano_codigo, referencia)` e `placa(placa)`; `parallelum.py` com `urllib` da biblioteca padrão, tempo limite de 10 s; `falso.py` com os modelos do seed, para desenvolvimento e testes.

- `GIRO_PROVEDOR_FIPE`: `falso` (padrão, desenvolvimento, testes e CI) ou `parallelum` (homologação e produção). Nenhum teste chama a API real.
- `GIRO_FIPE_URL_BASE`, padrão `https://fipe.parallelum.com.br/api/v2` (o endereço da decisão do dono; o `parallelum.com.br/fipe/api/v2` da 0031 responde igual).
- `GIRO_FIPE_TOKEN`, vazio por padrão. Quando houver (plano Pro), vai no cabeçalho `X-Subscription-Token`, vem do cofre de segredos (ADR 0033) e nunca entra no repositório nem no log.
- Preço `"R$ 13.023,00"` vira centavos por texto (tira `R$`, ponto e vírgula), nunca por `float` (ADR 0003). Resposta fora do formato é erro do provedor, não preço zero.
- Os tipos são os da 0031: `moto` → `motorcycles`, `carro` → `cars`.

### 2. O preço é público e fica no schema `public`

O preço da Tabela FIPE para um código, um ano e um mês é igual para todas as empresas. Ele fica num cache durável no app `plataforma` (o único só do `public`), sem nada da empresa:

| `plataforma.PrecoFipe` | |
| --- | --- |
| `tipo` | enum `moto`, `carro` |
| `codigo_fipe` | texto(10), "811134-0" |
| `ano_codigo` | texto(10), "2017-5" |
| `referencia_codigo` | texto(6), "339" |
| `referencia_mes` | data, dia 1 do mês |
| `valor_centavos` | centavos |
| `modelo_nome`, `ano_nome` | texto(120), texto(30): "CG 160 FAN ESDi FLEXONE", "2017 Flex" |
| `consultado_em` | momento |

Único `(tipo, codigo_fipe, ano_codigo, referencia_codigo)`. Mais `plataforma.AnosFipe` (`tipo`, `chave`: o código FIPE ou `marca_id/modelo_id`, `anos` json `[{code, name}]`, `consultado_em`; único `(tipo, chave)`, renovado a cada 6 meses) e `plataforma.RodadaFipe` (`referencia_codigo` único, `referencia_mes`, `aberta_em`, `concluida_em`, `pedidos` int, `parada_ate` momento nulo, `ultimo_erro` texto(200)).

- Escrita só por `plataforma.services` (`guardar_preco_fipe`, `guardar_anos_fipe`, `abrir_rodada_fipe`, ...); leitura por `plataforma.selectors`. `veiculos` está abaixo de `plataforma` e pode chamar os dois (ADR 0011). Nenhum dado de empresa (placa, veículo, schema) vai para essas tabelas.
- Um pedido por código e ano em cada mês, qualquer que seja o número de empresas e de veículos com aquele código ("consulta uma vez cada código e ano repetido").

### 3. O que o veículo guarda

`veiculos.Veiculo` ganha (modelo de dados, item 9):

| Campo | Tipo | Observação |
| --- | --- | --- |
| `fipe_codigo` | texto(10), vazio | "811134-0" |
| `fipe_ano_codigo` | texto(10), vazio | "2017-5"; escolhido pelo ano do modelo e o combustível |
| `fipe_marca_id`, `fipe_modelo_id` | int, nulo | ids da Parallelum, quando a versão veio da lista e o código ainda não é conhecido |
| `fipe_versao` | texto(120), vazio | o nome da versão na FIPE |
| `fipe_situacao` | enum `sem_versao`, `escolher_versao`, `aguardando`, `ok`, `nao_encontrado`, padrão `sem_versao` | |
| `fipe_versoes` | json, `[]` | as versões candidatas, para a pessoa escolher |
| `referencia_fipe_mes` | data, nula | dia 1 do mês do preço |
| `referencia_fipe_origem` | enum `fipe`, `manual`, nulo | |

- `referencia_fipe_centavos` continua. Com `fipe_situacao = ok`, ele é da rotina (`origem = fipe`), e o valor informado em "Colocar à venda" é ignorado. Sem versão, continua aceitando o valor à mão (`origem = manual`), como hoje: nada que já funciona deixa de funcionar.
- Escolher a versão ou digitar o código no cadastro e no editar (junto com a T-415) grava os campos e põe `fipe_situacao = aguardando`. O preço chega na próxima rodada, que atende os `aguardando` primeiro. Não há chamada à API durante o pedido da pessoa.
- Mudar marca, modelo, ano do modelo ou combustível limpa os campos FIPE e o veículo volta ao casamento (item 5).

### 4. O catálogo ganha os ids da Parallelum

O script da 0031 (item 2) passa a gravar também `marca_id` e `modelo_id` (os `code` das listas, sem pedido a mais). O CSV versionado fica `marca,modelo,tipo,marca_id,modelo_id`; as 29 linhas da lista própria ficam com os ids vazios. `GET /api/veiculos/modelos/` devolve os ids para a tela guardar com a escolha. Continua sem preço e sem código FIPE no CSV.

### 5. Casamento dos veículos já cadastrados

Local, sem pedido, em `veiculos.services.casar_fipe(veiculo)`: procura no catálogo, pela marca e pelo tipo, as linhas com id cujo nome normalizado começa pelo modelo normalizado do veículo ("CG 160 Fan" casa "CG 160 FAN Flex" e "CG 160 FAN ESDi FLEXONE").

- Nenhuma: `nao_encontrado` (a pessoa pode escolher à mão ou digitar o código).
- Uma: grava `fipe_marca_id` e `fipe_modelo_id`, `aguardando`.
- Até 5: `aguardando` com as candidatas em `fipe_versoes`; a rotina busca os anos de cada uma (um pedido por modelo, guardado em `AnosFipe`) e fica com as que têm o ano do modelo e o combustível do veículo. Sobrou uma: segue. Sobrou mais de uma: `escolher_versao` (como o Cruze), sem referência até alguém escolher. Nenhuma: `nao_encontrado`.
- Mais de 5: `escolher_versao` direto, para não gastar a cota.

### 6. A rotina

Uma tarefa do Celery Beat por dia, `fipe_rodada_do_dia`, às 04:30 de `America/Sao_Paulo`, no `public`, com trava (`cache.add`, sempre no `public`, item 9.3) para não correr duas ao mesmo tempo:

1. `referencias()` (1 pedido). Se o mês mais novo não tem `RodadaFipe` concluída, abre ou continua a rodada desse mês. Não há dia fixo: a tabela vira nos primeiros dias úteis, e a rodada começa no primeiro dia em que o mês novo aparece ("depois da virada").
2. Para cada empresa que opera (`STATUS_OPERANDO`, pela mesma conferência de `comum.tarefas.na_empresa`), dentro do schema dela, `veiculos.selectors.pendencias_fipe(referencia_mes)` devolve só chaves, sem dado da empresa: os pares `(tipo, codigo_fipe, ano_codigo)` dos veículos ativos (fora `vendido` e `baixado`) cujo `referencia_fipe_mes` é anterior ao mês da rodada, e os modelos `aguardando` que ainda pedem anos. A rotina junta tudo e tira o que já está em `PrecoFipe` e `AnosFipe`.
3. Busca, **um pedido por segundo**, nesta ordem: anos dos `aguardando` (para os veículos novos terem preço logo), preços dos veículos `a_venda` (os que mostram a referência, `VEN-01`), o resto.
4. Para no menor destes: o orçamento do dia (`GIRO_FIPE_PEDIDOS_POR_DIA`, padrão 400, abaixo dos 500 do plano sem token, com folga para a carga do catálogo da 0031); `x-ratelimit-remaining` abaixo de 20; um **429** (grava `parada_ate` com `x-ratelimit-reset` e para na hora); três erros seguidos (tempo esgotado, 5xx, resposta fora do formato). O que faltou continua no dia seguinte, sem ordem nova: a fila é recalculada a cada dia, então "repartir entre os dias" sai sozinho.
5. Depois dos pedidos, `para_cada_empresa(fipe_aplicar_referencias)` (ADR 0012): em cada schema, os veículos pendentes recebem, do `PrecoFipe`, o valor, o mês e a versão, sem pedido à API. Veículo cujo código não tem preço no mês (a FIPE tirou a versão) fica com o último valor e o mês antigo.
6. Rodada sem pendências: `concluida_em`. Até a próxima virada, a tarefa diária só faz o pedido do item 1.

Com 20 empresas de 86 veículos, a conta fica perto de 15 a 30 códigos e anos distintos por empresa, menos com repetição entre empresas: algumas centenas de pedidos no mês, dentro de um ou dois dias.

### 7. Se a API sair do ar

- O veículo **fica com o último valor e o mês dele**. A ficha mostra "Referência FIPE · outubro de 2026". Com o mês do preço dois ou mais meses antes do mês corrente, a API manda também o aviso "Esta referência é de agosto de 2026 e não foi atualizada." (texto do produto; um mês de atraso é normal, porque a rodada leva dias). Nada some, nada vira zero, nenhum erro chega à pessoa.
- A rodada não concluída até o dia 15 do mês manda um aviso ao Sentry (sem placa nem dado de empresa), uma vez por dia.
- Se a Parallelum fechar de vez ou mudar as rotas, os valores guardados continuam, e `GIRO_PROVEDOR_FIPE=falso` desliga as chamadas sem mudar o resto.

### 8. Consulta por placa, desligada por padrão

`GIRO_FIPE_PLACA_ATIVA=false` por padrão. Ligada, o cadastro pode chamar `POST /api/veiculos/consulta-placa/` (`placa(placa)` → `GET /plates/{placa}`, em Alpha), que devolve marca, modelo, ano e as versões com o código FIPE para a pessoa conferir, sem gravar nada.

- A cota é global (15 por mês sem token, 30 com token gratuito, somando todas as empresas). O cliente lê `X-Plate-Quota-Remaining` e guarda no cache do `public` só o fato de a cota ter acabado (`fipe:placa:cota`, item 9.3); quem conta é o cabeçalho, não um contador local. Sem cota, com a rota fora do ar ou desligada: 200 `{ "disponivel": false }`, e a tela segue pelo CRLV-e e pela escolha da versão, sem mensagem de erro.
- Só quem cadastra veículo (administrador e gerente) e com limite por empresa (`comum.limites`, 3 por dia), para uma empresa não gastar a cota de todas.
- A placa é da frota da locadora, não dado pessoal; mesmo assim, vai para um terceiro, e a revisão de segurança da T-422 confere antes de ligar.

### 9. Revisão de segurança (M-01, M-02, M-04 e B-04 da T-422)

**9.1 Formato fechado antes da URL (M-01).** Tudo o que entra no caminho ou na consulta da URL tem formato fechado, conferido no serializer (400 `validacao`) e de novo no cliente, antes de montar a URL:

| Valor | Formato |
| --- | --- |
| `fipe_codigo` | `^\d{6}-\d$` ("811134-0") |
| `fipe_ano_codigo` | `^\d{4,5}-\d$` ("2017-5"; "32000-1" do zero km) |
| `referencia` | `^\d{1,4}$` ("339") |
| `fipe_marca_id`, `fipe_modelo_id` | inteiro positivo |
| placa | `^[A-Z]{3}\d[A-Z0-9]\d{2}$`, depois de tirar o hífen e passar para maiúsculas |
| `tipo` | só pelo mapa `moto` → `motorcycles`, `carro` → `cars`; nunca o texto recebido |

- Escolher uma versão de `fipe_versoes` aceita só uma linha que está na lista guardada no veículo; escolher da lista do catálogo, só ids que existem nele, do mesmo tipo.
- Mesmo validada, cada parte do caminho passa por `urllib.parse.quote(parte, safe="")`. O cliente recusa, sem pedido, qualquer valor fora do formato que chegue a ele.

**9.2 Resposta limitada e validada (M-02).** O cliente:
- lê no máximo **256 KB** (`resposta.read(LIMITE + 1)`; passou, é erro do provedor), recusa `Content-Type` que não seja `application/json` e usa `json.loads(..., parse_float=Decimal)`;
- aceita o preço só se casar inteiro com `^R\$ \d{1,3}(\.\d{3})*,\d{2}$`, maior que zero e até R$ 20.000.000,00; senão, erro;
- confere que `codeFipe` é o código pedido e que `referenceMonth` é o mês da rodada (comparados normalizados: "outubro de 2026" e "outubro/2026"); diferente, erro, e nada é gravado;
- limita `brand`, `model` e `name` ao tamanho do campo (120 e 30) e recusa caractere de controle; maior, erro, sem cortar em silêncio;
- aceita no máximo 60 itens em `anos` e 5 em `fipe_versoes`, cada um só com os campos usados (`{code, name}` e `{marca_id, modelo_id, versao}`), conferidos pelo 9.1;
- nunca guarda o JSON cru da resposta.

Os nomes da FIPE que vão para PDF não usam `|safe`; em CSV, valem as defesas da exportação contra fórmula.

**9.3 Cota e trava no `public` (M-04).** O cache usa `django_tenants.cache.make_key`, que põe o schema na chave. Por isso a marca de cota esgotada da placa e a trava da rotina são lidas e gravadas sempre no `public`, por uma função só em `integracoes/fipe` (`schema_context(get_public_schema_name())` em volta de `cache.get/set/add`, ou um alias de cache sem `KEY_FUNCTION`). O limite de 3 consultas por dia **por empresa** (`comum.limites`) continua por empresa, de propósito. Teste: `test_vei_08_cota_da_placa_e_unica_entre_empresas`.

**9.4 Situação e origem só pelo servidor (B-04).** `fipe_situacao`, `referencia_fipe_origem`, `referencia_fipe_mes` e, com `fipe_situacao = ok`, `referencia_fipe_centavos` são só de leitura na API; o valor ignorado em "Colocar à venda" volta no 200 com o valor que vale. `fipe_situacao` é status: muda só em `veiculos.services`, com auditoria. Na rotina, o autor é o Sistema, com **um evento de lote por empresa a cada aplicação** (`veiculo.referencia_fipe_rotina`, objeto: a empresa), com a lista dos veículos que mudaram e, para cada um, a situação, o valor e o mês de antes e de depois. A escolha feita pela pessoa gera o evento de edição do veículo, como os outros campos.

**Fica para a implementação** (listado no handoff do arquiteto): M-03 (placa fora dos breadcrumbs do Sentry e do log), B-01, B-02, B-03 e B-06. O B-05 é decisão do dono antes de ligar a consulta por placa e não segura o resto.

## Consequências

- Uma chamada externa nova no servidor, sem biblioteca nova. A Parallelum fica no caminho só da madrugada; o cadastro e a ficha nunca esperam por ela.
- Três tabelas pequenas no `public`, com dados públicos da FIPE e nada de empresa. Saem junto quando a FIPE licenciada substituir a fonte (a 0031, item 4, vale igual).
- `referencia_fipe_centavos` passa a ter dono: a rotina, quando há versão; a pessoa, quando não há.
- A tarefa diária passa por todas as empresas lendo só chaves; o isolamento continua, porque nenhum dado de uma empresa sai do schema dela.
- O contrato da API (o bloco `referencia_fipe` na ficha, escolher a versão, a consulta por placa) e o modelo de dados saem na parte do contrato, a partir desta ADR.

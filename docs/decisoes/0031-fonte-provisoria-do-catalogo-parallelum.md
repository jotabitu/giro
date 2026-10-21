# Fonte provisória do catálogo de modelos: API aberta da Parallelum

**Status:** aceita · 20 out 2026 · T-342 (decisão do dono depois da T-337 e da T-338) · provisória até haver contrato com a FIPE · detalha a 0026 (item 7); a 0030 continua proposta para o caso do contrato

## Contexto

A ADR 0026 (item 7) fixou como a leitura do CRLV-e usa o catálogo de marcas e modelos e deixou a origem da lista para outra tarefa. A T-257 entregou o catálogo local (`backend/apps/veiculos/dados/catalogo_modelos.csv`, 29 modelos escolhidos à mão) e o comando `atualizar_catalogo_modelos`, que não consulta a internet.

Na T-337, o dono escolheu a FIPE licenciada (opção B). A T-338 mostrou que só a FIPE dá uma licença limpa, com preço só por contato. O pedido à FIPE ainda não foi feito. Até lá, o dono decidiu usar uma fonte aberta e aceitar o risco da opção A da T-337 enquanto isso for provisório.

## Decisão

### 1. A fonte

- API aberta da Parallelum: `https://parallelum.com.br/fipe/api/v2` (código em `github.com/parallelum/fipe-go`, licença MIT). Rotas `GET /{tipo}/brands` e `GET /{tipo}/brands/{id}/models`, sem token. As respostas são listas de `{ "code", "name" }`.
- Os tipos da API são `cars`, `motorcycles` e `trucks`. O catálogo usa `cars` → `carro` e `motorcycles` → `moto`. `trucks` fica de fora (`VEI-08` só tem moto e carro).
- Os dados são da Tabela FIPE, extraídos pela Parallelum, **sem licença própria**. O código é MIT, mas os dados não são. Esse é o risco que o dono aceitou em 20 out 2026, enquanto a fonte for provisória. O catálogo guarda só marca, modelo e tipo, sem preço nem código FIPE.
- Medida em 20 out 2026: 108 marcas de carro e 103 de moto, 9.424 modelos (7.386 carros e 2.038 motos), 404 KB em CSV. Sem token, a API permite 500 pedidos por dia (`x-ratelimit-limit: 500`, que volta a zero em 24 h). Uma carga completa usa cerca de 213 pedidos.

### 2. Como a lista é gerada

- Fora do servidor, na máquina de alguém da equipe, por um script que usa só a biblioteca padrão do Python (`urllib`, `json`, `csv`), sem dependência nova. Ele faz um pedido por segundo, para ao receber 429 e respeita o limite do dia. A saída é um CSV `marca,modelo,tipo`.
- O comando `atualizar_catalogo_modelos` continua sem acesso à internet e passa a aceitar mais de um arquivo. Ele junta a lista da Parallelum com a lista própria da equipe e regrava o CSV versionado. A lista própria é a de hoje, com os 29 modelos de nome genérico ("CG 160 Fan", "Kwid"), que o seed e os testes usam.
- A lista própria fica porque a FIPE tem uma linha por versão ("CG 160 FAN Flex", "CG 160 FAN ESDi FLEXONE", "MOBI LIKE 1.0 Fire Flex 5p."), e os nomes do seed ("CG 160 Fan", "Factor 150", "Kwid", "Biz 125", "Mobi") não existem iguais na FIPE. O nome genérico também ajuda a leitura: "HONDA/CG 160 FAN" do CRLV-e acha "CG 160 Fan" sozinho, em vez de duas versões.
- Uma só grafia por marca normalizada no CSV inteiro: a da lista própria; senão, a da lista de carros ("Honda"); senão, a que vier ("YAMAHA"). A API escreve "Honda" nos carros e "HONDA" nas motos. O nome do modelo fica como vem.
- Nada disso roda em produção nem a cada pedido. A rota `GET /api/veiculos/modelos/` e a leitura do CRLV-e continuam lendo o CSV versionado, uma vez por processo (ADR 0026, item 7).

### 3. O CSV no repositório

- O CSV completo é versionado no repositório público, com a fonte citada em `backend/apps/veiculos/dados/README.md` e na docstring de `veiculos/catalogo.py`: "Marcas e modelos da Tabela FIPE, obtidos pela API aberta da Parallelum (provisório, ADR 0031), mais a lista própria da equipe."
- Atualização a cada trimestre, por PR, com o mês de referência da FIPE na descrição do PR.

### 4. Quando a fonte troca

- Se houver contrato com a FIPE (T-338), a fonte passa a ser a entrega da FIPE, pelo mesmo comando. Se o contrato proibir publicar a lista, a ADR 0030 passa a aceita, e o CSV completo sai do git, inclusive do histórico novo. Nesse caso, a lista da Parallelum também sai do repositório.
- Se a Parallelum sair do ar ou mudar as rotas, o catálogo versionado continua valendo até a próxima atualização. Nada no uso depende da API.

## Consequências

- A lista completa chega sem custo e sem contrato, com o tipo certo, e a T-339 não espera mais a FIPE.
- O repositório público passa a guardar nomes da Tabela FIPE sem licença. O risco é do dono e dura enquanto a fonte for provisória.
- O texto da tela "Da lista FIPE" (`Veiculo-Novo`, `NovoVeiculoForm`) continua certo, porque os nomes são os da Tabela FIPE. As 29 linhas da lista própria são nomes genéricos dos mesmos modelos. Não muda texto de tela nem regra.
- No carro, o CRLV-e costuma achar mais de uma versão e vai para a dica (CA-247-05, T-337). Na moto, acerta mais.

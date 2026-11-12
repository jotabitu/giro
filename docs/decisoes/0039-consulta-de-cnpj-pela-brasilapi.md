# Consulta de CNPJ da compra pública pela BrasilAPI

**Status:** aceita · 05 nov 2026 · T-435 (decisão do dono em 05 nov 2026, que troca a D-430-03) · detalha a 0011 (integrações atrás de interface)

## Contexto

A tela `Compra-Checkout` mostra a razão social e a cidade preenchidas a partir do CNPJ ("Moto Rápida Locações Ltda · Fortaleza, CE · CNPJ ativo"). Na T-430, a D-430-03 tinha decidido não consultar a Receita: a pessoa digitava razão social, cidade e UF. Em 05 nov 2026, o dono trocou essa decisão: a compra consulta o CNPJ num serviço público e preenche os campos.

## Decisão

1. **Fonte:** BrasilAPI, `GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}`. É pública, sem chave e sem custo, com os dados abertos da Receita. Lê `razao_social`, `nome_fantasia`, `municipio`, `uf` e `descricao_situacao_cadastral`.
2. **Onde mora:** `backend/integracoes/cnpj`, como o CEP (`integracoes/cep`). Usa `consultar_cnpj(cnpj)` com o provedor escolhido por `GIRO_PROVEDOR_CNPJ` (`falso` em desenvolvimento e testes, com o CNPJ fictício da Moto Rápida; `brasilapi` em homologação e produção). Usa só a biblioteca padrão (`urllib`), com 5 s de limite. **Nenhuma dependência nova.**
3. **Cache:** 7 dias no Redis por CNPJ, inclusive para "não achado". Falha do provedor não entra no cache.
4. **A consulta só preenche.** Ela vem na resposta de `POST /api/publico/compra/cnpj/` (campo `dados`) apenas quando o CNPJ pode comprar (`PLT-16`). A tela preenche razão social, nome, cidade e UF, e a pessoa confere e edita. O pedido continua recebendo os quatro campos digitados, e a compra nunca depende da consulta: se o provedor cair ou não achar o CNPJ, `dados` vem nulo e a pessoa digita.
5. **Situação na Receita:** `ativo` vai para a tela, mas não recusa a compra. Nenhuma regra recusa CNPJ inativo. Se o produto quiser recusar, é regra nova.
6. **Limite:** a rota já tem 20 consultas por hora por IP (`compra.md`). Isso também protege a BrasilAPI de uso em massa por meio do Giro.

## Consequências

- O checkout fica como a tela, sem custo e sem contrato.
- A BrasilAPI não tem SLA. Por isso a consulta é só ajuda: a compra funciona sem ela.
- O CNPJ consultado vai a um serviço de terceiros. O CNPJ é dado público de pessoa jurídica, e nenhum dado pessoal da pessoa que compra sai do Giro.

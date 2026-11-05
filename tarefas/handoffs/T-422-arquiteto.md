# T-422 (ADR do arquiteto) · Referência FIPE pela Parallelum, com rotina mensal · arquiteto → orquestrador, segurança

**O que foi feito:** a ADR 0038, que complementa a 0031 com o preço e a chamada pelo servidor, a partir das decisões do dono de 29 out 2026. As rotas foram conferidas na API real em 05 nov 2026, com poucos pedidos e sem token.

**Onde:** `docs/decisoes/0038-referencia-fipe-pela-parallelum.md`; o índice em `docs/decisoes/README.md` (a ordem da 0036 e da 0037 também foi acertada).

**Decisões:**
1. Cliente em `backend/integracoes/fipe/` com `urllib`, sem dependência nova; `GIRO_PROVEDOR_FIPE=falso` em desenvolvimento, testes e CI; `GIRO_FIPE_URL_BASE`; `GIRO_FIPE_TOKEN` só pelo cofre.
2. Preço, anos e rodada em tabelas do `public` (`plataforma.PrecoFipe`, `AnosFipe`, `RodadaFipe`), sem nenhum dado de empresa: um pedido por código e ano no mês, para todas as empresas.
3. Veículo com `fipe_codigo`, `fipe_ano_codigo`, ids da Parallelum, `fipe_versao`, `fipe_situacao`, `fipe_versoes`, `referencia_fipe_mes` e `referencia_fipe_origem`. Com versão, a referência é da rotina; sem versão, continua à mão em "Colocar à venda".
4. O CSV do catálogo ganha `marca_id` e `modelo_id` da Parallelum, pelo mesmo script da 0031, sem pedido a mais.
5. Casamento local dos veículos já cadastrados: uma versão grava; até 5 candidatas, a rotina busca os anos e filtra pelo ano e combustível; mais de uma sobrando, ou mais de 5, "escolher versão".
6. Rotina diária às 04:30: abre o mês quando a tabela vira, junta as chaves de todas as empresas, um pedido por segundo, orçamento de 400 por dia, para no 429, com `remaining` abaixo de 20 ou em três erros seguidos, e continua no dia seguinte; depois aplica os preços em cada empresa sem pedido.
7. API fora do ar: o último valor fica, com o mês; aviso ao Sentry se a rodada não fechar até o dia 15.
8. Consulta por placa desligada por padrão (`GIRO_FIPE_PLACA_ATIVA`), com a cota global lida de `X-Plate-Quota-*`, só administrador e gerente, 3 por dia por empresa, e 200 `{ "disponivel": false }` quando não dá.

**Achado na API real:** o `x-ratelimit-limit` veio 500 na maioria das respostas e 1.000 numa delas. A rotina lê o cabeçalho e não confia num número fixo; o orçamento de 400 cabe nos dois.

**Regras cobertas:** `VEN-01`, `VEI-08` (no desenho).

**O que ficou de fora:** o contrato (`docs/api/veiculos.md`: o bloco da referência na ficha, escolher a versão ou digitar o código, a consulta por placa) e o modelo de dados (item 9 e as tabelas do `public`). Ficam para a próxima parte do arquiteto.

**Próximo passo:**
- **Orquestrador:** liberar a parte do contrato e do modelo de dados.
- **Segurança:** revisar a chamada externa (tempo limite, resposta fora do formato, token só no cofre) e a consulta por placa antes de alguém ligá-la.
- **Backend e frontend:** só depois do contrato.

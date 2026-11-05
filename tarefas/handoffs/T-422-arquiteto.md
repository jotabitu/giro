# T-422 (parte do arquiteto) · Referência FIPE pela Parallelum, com rotina mensal · arquiteto → orquestrador, segurança, backend, frontend

**O que foi feito:** (1) a ADR 0038 (PR #477) e (2) o contrato e o modelo de dados (PR empilhado no #477, que leva a ADR junto). A ADR 0038, que complementa a 0031 com o preço e a chamada pelo servidor, a partir das decisões do dono de 29 out 2026. As rotas foram conferidas na API real em 05 nov 2026, com poucos pedidos e sem token.

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

**Contrato (parte 2, `docs/api/veiculos.md`, seção "Referência FIPE"):**
- Bloco `referencia_fipe` na lista e no detalhe (`valor_centavos`, `mes`, `rotulo` "Referência FIPE · outubro de 2026", `origem`, `situacao`, `aviso`, `versao`, `codigo_fipe`, `ano`, `versoes`); `referencia_fipe_centavos` continua. Vistoriador sem o valor. `acoes.escolher_versao_fipe`. Frota com `?fipe_situacao=`.
- Bloco `fipe` no `POST` e no `PATCH` do veículo (`{marca_id, modelo_id}`, `{codigo_fipe}` ou `null`) e o atalho `POST /api/veiculos/{id}/fipe/`. Nenhuma chamada externa: a escolha fica `aguardando` até a próxima rodada.
- `GET /api/veiculos/modelos/` com `marca_id` e `modelo_id`.
- "Colocar à venda": com referência da rotina, o valor mandado é ignorado.
- `GET` e `POST /api/veiculos/consulta-placa/`: `{ativa}` e `{disponivel: false}` em toda falha, sem erro para a pessoa.
- Interface interna, tarefas e configurações; seed sem código FIPE (o provedor falso precifica os modelos do seed com números fictícios).

**Modelo de dados:** item 9 (campos `fipe_*`, `referencia_fipe_mes`, `referencia_fipe_origem`, `CHECK` do código, índice parcial da situação) e "Apoio do public" (`PrecoFipe`, `AnosFipe`, `RodadaFipe`).

**Para o produto confirmar:** os textos propostos para o `aviso` ("A referência FIPE chega na próxima atualização.", "Escolha a versão FIPE para ver a referência.", "Versão FIPE não encontrada. Escolha a versão ou digite o código."), "Referência FIPE · informada à mão" e as mensagens de validação do bloco `fipe`.

**Próximo passo:**
- **Segurança:** revisar a ADR 0038 e o contrato: a chamada externa (tempo limite, resposta fora do formato, token só no cofre), a passagem por todas as empresas só com chaves e a consulta por placa antes de alguém ligá-la. Ajustes entram no mesmo PR.
- **Backend (quando o dono liberar):** `integracoes/fipe` (falso e Parallelum), as três tabelas do `public`, os campos do veículo, o script e o CSV com os ids (0031, item 2), `casar_fipe`, a rotina e a tarefa por empresa, o bloco na representação, o bloco `fipe` no cadastro, a consulta por placa desligada. OpenAPI e `npm run api:gerar`. Testes com respostas gravadas, nunca com a API real.
- **Frontend (quando o dono liberar):** o campo "Referência FIPE" do cadastro vira a escolha da versão (lista com os ids, junto com a T-415) ou o código; a ficha mostra `rotulo`, valor e `aviso` como vêm, com "Escolher versão" pelas `acoes`; "Buscar pela placa" só com `ativa`.

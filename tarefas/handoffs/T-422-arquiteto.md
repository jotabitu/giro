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

**Textos fechados pelo produto** (PR #481, `tarefas/handoffs/T-422-produto-textos.md`), já no contrato: os dois rótulos; o `aviso` de `aguardando` e `sem_versao` ("... feita de madrugada."); a variante de `escolher_versao` e `nao_encontrado` para quem não escolhe a versão (pela `acoes.escolher_versao_fipe`); o aviso de valor antigo só com dois ou mais meses de atraso; "Digite o código FIPE no formato 811134-0."; "Escolha uma versão da lista FIPE.". Na placa indisponível, preferi mandar o texto na resposta (`{ "disponivel": false, "mensagem": "A busca pela placa não está disponível agora. ..." }`), para o texto ficar num lugar só, como a opção que o produto deixou aberta.

**Revisão da segurança** (PR #480, `tarefas/handoffs/T-422-seguranca.md`). Nenhum achado alto. Entraram na ADR 0038 (item 9) e no contrato:
- **M-01:** formato fechado do código FIPE, do ano, da referência, dos ids, da placa e do tipo, validado no serializer e de novo no cliente antes da URL, com `quote(parte, safe="")`; a escolha só entre as versões guardadas ou do catálogo.
- **M-02:** resposta de até 256 KB, só JSON, preço pelo formato e com teto de R$ 20 milhões, código e mês iguais ao pedido, textos e listas limitados, sem guardar o JSON cru.
- **M-04:** trava da rotina e marca de cota esgotada da placa sempre no `public` (o `make_key` do django-tenants põe o schema na chave); o limite de 3 por dia continua por empresa.
- **B-04** (estava como do contrato no parecer): campos FIPE só de leitura; escolhi **um evento de auditoria de lote por empresa** a cada aplicação da rotina (`veiculo.referencia_fipe_rotina`), em vez de um por veículo, para não encher a auditoria todo mês; o B-04 deixava a escolha para o arquiteto.
- Também a ordem da consulta por placa do B-05 (perfil, formato, limite, chamada) e o descarte dos campos que a rota de placa trouxer além dos usados.

Não discordo de nenhum achado.

**Próximo passo:**
- **Segurança:** revisar a ADR 0038 e o contrato: a chamada externa (tempo limite, resposta fora do formato, token só no cofre), a passagem por todas as empresas só com chaves e a consulta por placa antes de alguém ligá-la. Ajustes entram no mesmo PR.
- **Backend (quando o dono liberar):** `integracoes/fipe` (falso e Parallelum), as três tabelas do `public`, os campos do veículo, o script e o CSV com os ids (0031, item 2), `casar_fipe`, a rotina e a tarefa por empresa, o bloco na representação, o bloco `fipe` no cadastro, a consulta por placa desligada. OpenAPI e `npm run api:gerar`. Testes com respostas gravadas, nunca com a API real. Além do contrato, os achados da segurança que são da implementação (detalhes e testes no parecer):
  - **M-03:** `before_breadcrumb` em `comum/sentry.py` que tira o caminho das chamadas `httplib` à Parallelum (fica host e status; teste `test_sentry_breadcrumb_sem_placa`); `x-subscription-token` em `CABECALHOS_SECRETOS` e `CHAVES_SECRETAS`; o cliente loga só o tipo do erro e o status, nunca a URL nem o corpo; `RodadaFipe.ultimo_erro` só com "HTTPError 503", "TimeoutError" ou "formato: price"; o aviso do dia 15 leva só o mês e o número de pendências.
  - **B-01:** `build_opener` com um `HTTPRedirectHandler` que recusa todo redirecionamento; base conferida no arranque (`https://` e o host configurado).
  - **B-02:** prazo total por pedido (20 s, no laço de leitura); `soft_time_limit` de 60 min e `time_limit` de 65 min na tarefa; trava de 70 min solta num `finally`; o orçamento do dia contado por data num lugar que sobrevive a duas execuções, no `public`.
  - **B-03:** `x-ratelimit-reset` com `int()` em `try`, fora de `0..86400` vale 24 h no 429; `remaining` inválido vale "não sei" e fica só o orçamento.
  - **B-05:** a lista fechada de campos da resposta da placa e a ordem perfil → formato → limite → chamada já estão no contrato; declarar a Parallelum como terceiro na política de privacidade é **decisão do dono antes de ligar** a placa e não segura o resto.
  - **B-06:** variação acima de 50% contra o mês anterior do mesmo código e ano não é aplicada: o preço fica guardado, o veículo com o valor antigo, e vai um aviso ao Sentry só com código, ano e mês.
  - Fora da T-422: o mesmo bloqueio de redirecionamento e o limite de tamanho no `viacep.py` (tarefa pequena à parte).
- **Frontend (quando o dono liberar):** o campo "Referência FIPE" do cadastro vira a escolha da versão (lista com os ids, junto com a T-415) ou o código; a ficha mostra `rotulo`, valor e `aviso` como vêm, com "Escolher versão" pelas `acoes`; "Buscar pela placa" só com `ativa`.

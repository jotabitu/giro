# T-422 · Revisão de segurança da ADR 0038 (FIPE pela Parallelum) · seguranca → arquiteto, depois backend

**Data:** 05 nov 2026 · **Agente:** segurança · **Regras:** VEN-01, VEI-08, AUD-01, AUD-09, ADR 0003, 0011, 0012, 0033
**Base:** PR #477 (branch `t-422-adr-fipe-parallelum`): `docs/decisoes/0038-referencia-fipe-pela-parallelum.md` e `tarefas/handoffs/T-422-arquiteto.md`. Conferido contra o código atual da `develop`: `integracoes/cep/viacep.py` e `integracoes/pagamentos/asaas.py` (os clientes `urllib` que já existem), `comum/sentry.py`, `comum/limites.py`, `config/settings/base.py` (cache com `django_tenants.cache.make_key`) e `scripts/baixar_catalogo_parallelum.py`.
**Método:** leitura da ADR e do código. Não rodei testes; é revisão de documento.

## Resumo

O desenho está certo no que mais importa:
- nenhuma chamada externa durante o pedido da pessoa, só na rotina da madrugada;
- endereço base fixo, por configuração, sem host vindo do usuário;
- tabelas do `public` só com dado público da FIPE, e a rotina lê só chaves de cada schema;
- token só no cofre, preço em centavos por texto, resposta fora do formato vira erro e não zero;
- parada no 429 e no `remaining` baixo, com orçamento diário;
- placa desligada por padrão, com cota global, perfil e limite por empresa.

**Nenhum achado alto.** O contrato e o backend podem seguir, desde que os achados médios entrem no contrato (`veiculos.md`) ou na própria ADR antes do backend começar. Nenhum muda o desenho; são regras de validação e de log que a ADR não escreveu.

| # | Gravidade | Achado | Quem muda |
| --- | --- | --- | --- |
| M-01 | média | O código FIPE e o ano digitados pela pessoa entram no caminho da URL sem validação de formato | arquiteto (contrato), backend |
| M-02 | média | A resposta da Parallelum não tem limite de tamanho nem validação dos campos que vão para o banco e para a tela | arquiteto (ADR), backend |
| M-03 | média | A placa vai para o Sentry pelo rastro de chamadas HTTP (breadcrumb do `urllib`) e pode ir para o log | backend |
| M-04 | média | A chave de cache `fipe:placa:cota` fica por empresa (o cache usa `make_key` do django-tenants), e a cota "global" vira uma por empresa | arquiteto (ADR), backend |
| B-01 | baixa | `urlopen` segue redirecionamento, inclusive para outro host | backend |
| B-02 | baixa | O tempo limite de 10 s é por operação de socket, não por pedido; a rotina não tem teto de duração, e a trava pode vencer no meio | backend |
| B-03 | baixa | Cabeçalhos de cota lidos sem limite: `x-ratelimit-reset` enorme ou negativo para a rotina por tempo errado | backend |
| B-04 | baixa | Campos de situação e origem da referência não podem ser aceitos do cliente; a troca em lote precisa de auditoria | arquiteto (contrato), backend |
| B-05 | baixa | Consulta por placa: o que precisa estar pronto antes de alguém ligar (LGPD e terceiro) | dono, produto, backend |
| B-06 | baixa | Um preço errado da Parallelum chega a todas as empresas de uma vez | backend |

## Os pontos pedidos

| Ponto | Parecer |
| --- | --- |
| SSRF | O host não vem do usuário: `GIRO_FIPE_URL_BASE` é configuração. O risco que sobra é o caminho: `fipe_codigo` e `fipe_ano_codigo` podem ser digitados no cadastro e no editar (item 3) e vão para `/{tipo}/{codigo}/years/{ano}` (M-01). O redirecionamento seguido pelo `urlopen` é o B-01. Conferir no arranque que a base começa com `https://`, como o `transporte_urllib` do Asaas já faz. |
| Tempo limite | 10 s está bom por pedido. Falta o teto da rotina e a relação com a trava (B-02). |
| Validação da resposta | O preço por texto e o "fora do formato é erro" estão certos. Faltam o limite de bytes, o formato exato do preço, a faixa de valor, o código da resposta igual ao pedido e o tamanho dos textos (M-02). |
| Tamanho | Não há limite hoje nem no `viacep.py` (`json.load(resposta)` lê tudo). M-02. |
| Isolamento no `public` | Certo. `PrecoFipe`, `AnosFipe` e `RodadaFipe` não têm schema, placa nem veículo; `pendencias_fipe` devolve só `(tipo, codigo_fipe, ano_codigo)`; a aplicação volta por `para_cada_empresa`. Dois cuidados: (1) **nenhuma rota de empresa lista `PrecoFipe` ou `AnosFipe`** nem expõe `consultado_em`, senão uma empresa descobre, pela presença no cache, que código outra empresa tem na frota; a ficha lê só o preço do próprio veículo, já copiado para ele; (2) a rotina volta ao `public` num `finally` depois de cada empresa, como `na_empresa` já faz. O único vazamento real entre empresas é o do cache (M-04). |
| Placa como dado pessoal | Concordo que a placa da frota da locadora não é, sozinha, dado pessoal do cliente. Mas ela identifica um veículo, e, na revenda, o veículo pode ter acabado de sair de uma pessoa física. A ANPD trata a placa como dado pessoal quando dá para chegar ao dono. Tratamento: não vai para log nem Sentry (M-03), e o terceiro precisa estar declarado antes de ligar (B-05). |
| O que vai ao terceiro | Na rotina, só código FIPE, ano e mês: nada da empresa. Na consulta por placa, só a placa e o IP do servidor. O token, quando houver, no `X-Subscription-Token`. Nenhum nome da empresa, subdomínio ou `User-Agent` com dado da empresa. O `User-Agent` deve ser genérico (`Giro/1.0`), sem e-mail de ninguém. |
| Logs | M-03 (placa) e B-03. O `ultimo_erro` da `RodadaFipe` deve guardar só o tipo do erro e o código HTTP (`"HTTPError 503"`, `"TimeoutError"`, `"formato: price"`), sem URL com placa, sem corpo e sem cabeçalho, como o `ParceiroIndisponivel(str(type(erro).__name__))` do Asaas. |
| Cabeçalhos de cota | Ler e não confiar num número fixo está certo. Falta tratar valor inválido e limitar a espera (B-03). |

## Achados

### M-01 · Código FIPE e ano digitados entram na URL sem validação · média

**Onde:** item 3 ("Escolher a versão ou digitar o código no cadastro e no editar") e o cliente (`anos_do_codigo`, `preco`). `fipe_versoes` também traz códigos que a pessoa escolhe.

**Problema:** a rotina monta o caminho com o que está gravado no veículo. Um `fipe_codigo` como `811134-0/../../references` ou `x?reference=1#` muda o caminho e a consulta no mesmo host. Não troca o host, mas faz a rotina gastar a cota de todas as empresas com pedidos que a pessoa escolheu, grava no `public` uma resposta de outra rota e abre caminho para erro de parse. A mesma coisa vale para a placa em `/plates/{placa}`.

**O que mudar:**
- No contrato (`veiculos.md`), formato fechado, conferido no serializer e de novo no cliente:
  - `fipe_codigo`: `^\d{6}-\d$` ("811134-0");
  - `fipe_ano_codigo`: `^\d{4,5}-\d$` ("2017-5"; o "32000-1" do zero km cabe);
  - `referencia`: `^\d{1,4}$`;
  - `fipe_marca_id` e `fipe_modelo_id`: inteiro positivo;
  - placa: `^[A-Z]{3}\d[A-Z0-9]\d{2}$`, depois de tirar o hífen e passar para maiúsculas;
  - `tipo`: só pelo mapa `moto`/`carro`, nunca o texto recebido.
- Escolher uma versão de `fipe_versoes` aceita só um código que está na lista guardada no veículo.
- No cliente, cada parte do caminho passa por `urllib.parse.quote(parte, safe="")` mesmo depois da validação.
- Testes: `test_vei_08_codigo_fipe_fora_do_formato_recusado` (400 no editar) e um teste do cliente que recusa `../` antes de montar a URL.

### M-02 · Resposta sem limite de tamanho e sem validação dos campos · média

**Onde:** item 1 (cliente), item 2 (`PrecoFipe.modelo_nome` texto 120, `AnosFipe.anos` json) e item 3 (`fipe_versoes` json, `fipe_versao` texto 120).

**Problema:** o que vem da Parallelum vai para o `public` e, de lá, para todas as empresas. Sem limite, uma resposta grande (por erro ou por alguém no meio do caminho) enche a memória do worker. Um `anos` com milhares de itens ou textos longos vai para o JSON do veículo e para a tela. Um `price` como `"R$ 1.302.300.000,00"` passa no "tira R$, ponto e vírgula".

**O que mudar (escrever na ADR, item 1):**
- Ler no máximo 256 KB (`resposta.read(LIMITE + 1)`; passou, é erro do provedor). Recusar `Content-Type` que não seja `application/json`. Usar `json.loads` com `parse_float=Decimal`, como o Asaas.
- Preço: casar `^R\$ \d{1,3}(\.\d{3})*,\d{2}$` inteiro; valor maior que zero e abaixo de um teto (por exemplo, R$ 20 milhões). Fora disso, erro do provedor.
- `codeFipe` da resposta igual ao pedido, e `referenceMonth` igual ao mês da rodada. Diferente, erro: não grava preço de outro código ou outro mês.
- Textos: `brand`, `model`, `name` limitados ao tamanho do campo e sem caractere de controle; maior, erro (não cortar em silêncio, que pode juntar duas versões com o mesmo nome).
- Listas: `anos` com no máximo 60 itens; `fipe_versoes` com no máximo 5 (a ADR já para em 5), cada item só com `{code, name}`, conferidos pelo M-01. O JSON cru da resposta nunca é guardado.
- Os nomes vindos da FIPE aparecem na tela (React escapa) e podem sair em PDF e CSV. No PDF, o template não usa `|safe`. No CSV, vale o que a exportação já faz contra fórmula (`=`, `+`, `-`, `@` no começo).

### M-03 · A placa vai para o Sentry e para o log · média

**Onde:** item 8 (`GET /plates/{placa}`) e `comum/sentry.py`.

**Problema:** o `sentry_sdk` liga a `StdlibIntegration` por padrão. Ela grava um breadcrumb para cada chamada do `http.client`, com a URL. Com `traces_sample_rate=0` não há span, mas o breadcrumb vai junto de qualquer erro do mesmo pedido ou da mesma tarefa. A URL `/plates/QXA4B21` chegaria ao Sentry. O `limpar_evento` só olha o pedido de entrada, não os breadcrumbs. E um `logger.warning("... %s", erro)` como o do `viacep.py` pode levar a URL na mensagem.

**O que mudar:**
- `comum/sentry.py`: um `before_breadcrumb` que, para `category == "httplib"`, troca a URL pelo host e por um caminho sem a placa (`/plates/[Filtrado]`). Melhor ainda: tirar o caminho de todos os breadcrumbs da Parallelum e deixar só o host e o status. Teste: `test_sentry_breadcrumb_sem_placa`.
- Incluir `x-subscription-token` em `CABECALHOS_SECRETOS` e `CHAVES_SECRETAS`, para o dia em que houver token.
- O cliente loga só o tipo do erro e o status, nunca a URL nem o corpo, como `_caminho_sem_consulta` no Asaas. O aviso do dia 15 ao Sentry (item 7) leva só o mês e o número de pendências.
- O evento de auditoria da consulta por placa, se houver, fica no schema da empresa. Ali a placa pode ir, porque é da frota dela.

### M-04 · A cota "global" da placa fica por empresa no cache · média

**Onde:** item 8 ("guarda o que resta no cache (`fipe:placa:cota`)") e item 6 (trava por `cache.add`).

**Problema:** `CACHES["default"]["KEY_FUNCTION"]` é `django_tenants.cache.make_key`, que põe o `connection.schema_name` na chave. A consulta por placa roda no pedido da empresa. Então cada empresa lê e grava a própria `fipe:placa:cota`. A cota de 15 por mês, que é de todas, fica sem controle: cada empresa acha que ainda tem cota, e a primeira resposta 429 da Parallelum é o único freio. A trava da rotina não tem o problema enquanto a tarefa rodar no `public`, mas quebra se alguém a chamar de dentro de uma empresa. O limite "3 por dia por empresa" em `comum.limites`, ao contrário, **deve** ficar por empresa, e fica, pelo mesmo `make_key`.

**O que mudar:**
- ADR, item 8: a cota global e a trava da rotina são lidas e gravadas sempre no `public` (`schema_context(get_public_schema_name())` em volta do `cache.get/set/add`), ou num alias de cache sem `KEY_FUNCTION`. Uma função só em `integracoes/fipe` faz isso, para não espalhar.
- Contar a cota pelo cabeçalho `X-Plate-Quota-Remaining`, não por contador local. O cache é só para não chamar quando já se sabe que acabou.
- Teste com duas empresas: `test_vei_08_cota_da_placa_e_unica_entre_empresas` (a empresa B vê `disponivel: false` depois que a A esgotou).

### B-01 · `urlopen` segue redirecionamento · baixa

**Problema:** o `HTTPRedirectHandler` padrão segue 301, 302, 307 e 308 para qualquer host em `http`, `https` ou `ftp`. Uma resposta de redirecionamento da Parallelum (por erro dela, por domínio vencido ou por alguém no meio) levaria o servidor a pedir um endereço interno, como `http://169.254.169.254/` dos metadados da nuvem ou um serviço da rede do Compose. Também levaria o `X-Subscription-Token` para outro host: o `urllib` repassa os cabeçalhos no redirecionamento.

**O que mudar:** um `build_opener` com um `HTTPRedirectHandler` que recusa todo redirecionamento (`redirect_request` devolve `None`), e redirecionamento vira erro do provedor. Base conferida no arranque: `https://` e host igual ao configurado. Vale a pena fazer o mesmo no `viacep.py` numa tarefa pequena do backend (fora da T-422).

### B-02 · Sem teto de duração na rotina; a trava pode vencer no meio · baixa

**Problema:** o `timeout=10` do `urlopen` é por operação de socket. Uma resposta que chega um byte a cada 9 s nunca estoura. Com 400 pedidos e 1 por segundo, a rotina já dura uns 7 minutos no caso bom. Se a trava do `cache.add` vencer antes do fim, uma segunda rodada começa junto e o orçamento dobra.

**O que mudar:**
- Prazo total por pedido (por exemplo, 20 s, conferido no laço de leitura do M-02).
- `soft_time_limit` de 60 min e `time_limit` de 65 min na tarefa.
- Trava com prazo maior que o `time_limit` (70 min), solta num `finally`.
- O orçamento do dia contado num lugar que sobrevive a duas execuções: um contador por data no `public`. `RodadaFipe.pedidos` é do mês, não do dia.

### B-03 · Cabeçalhos de cota sem limite · baixa

**Problema:** `x-ratelimit-reset` vira `parada_ate`. Um valor negativo, não numérico ou de 10 anos para a rotina por tempo errado, ou nunca para.

**O que mudar:** ler com `int()` dentro de `try`. Fora de `0..86400`, usar 24 h no 429 e ignorar no resto. `x-ratelimit-remaining` inválido vale como "não sei" e mantém só o orçamento. Os cabeçalhos vão para o log como números, sem o resto da resposta.

### B-04 · Situação e origem só pelo servidor; a troca em lote audita · baixa

**O que mudar (contrato):**
- O serializer do cadastro e do editar aceita só `fipe_codigo`, `fipe_ano_codigo`, `fipe_marca_id`, `fipe_modelo_id` e a escolha entre as `fipe_versoes`. `fipe_situacao`, `referencia_fipe_origem`, `referencia_fipe_mes` e, com `fipe_situacao = ok`, `referencia_fipe_centavos` são só de leitura ("a API decide"). O valor de "Colocar à venda" ignorado (item 3) volta no 200 com o valor que vale, para a tela não mostrar o digitado.
- `fipe_situacao` é status: muda só por serviço em `veiculos.services`, com evento de auditoria. Na rotina, o autor é o sistema. Um evento por veículo ou um evento de lote por empresa, com a lista de veículos, antes e depois; escolha do arquiteto.
- O bloco da referência na ficha segue as permissões que já valem para valores: o vistoriador não recebe `referencia_fipe_centavos`. O vendedor recebe, porque é preço público, não custo nem margem.
- Escolher a versão e digitar o código: os mesmos perfis que editam o veículo.

### B-05 · Consulta por placa: o que precisa estar pronto antes de ligar · baixa

Desligada por padrão está certo, e nada aqui segura o contrato. Antes de alguém pôr `GIRO_FIPE_PLACA_ATIVA=true`:
- **Terceiro declarado.** A Parallelum entra na lista de suboperadores e na política de privacidade da plataforma, com a finalidade ("conferir marca, modelo e versão pela placa"). Sem contrato com ela, o plano sem token não tem garantia nenhuma sobre o uso da placa. Onde ficam os servidores dela é desconhecido; se for fora do Brasil, é transferência internacional (LGPD, art. 33). Decisão do dono, com o produto.
- **Só o que se pede.** Da resposta de `/plates`, guardar e devolver só marca, modelo, ano e as versões com o código FIPE (lista fechada de campos). Chassi, município, cor ou qualquer outro campo que a rota em Alpha traga hoje ou passe a trazer é descartado e não chega à tela.
- **Nada gravado.** A consulta não grava a resposta (a ADR já diz). Também não guarda a placa no cache da cota.
- **Perfil e limite antes do pedido**, na ordem da T-252: permissão primeiro (403 para o vendedor e para o suporte Giro, `AUD-09`; o suporte não tem por que gastar a cota), depois o limite de 3 por dia, e só então a chamada. Um 403 não gasta o limite, e um 429 do limite não chama a Parallelum.
- **Resposta igual em todos os casos sem dado** (desligada, sem cota, fora do ar, placa não achada): 200 `{ "disponivel": false }`, como está. Não diz a uma empresa que a cota acabou por causa de outra.

### B-06 · Preço errado da Parallelum chega a todas as empresas · baixa

**Problema:** o preço é um só para todas. Se a Parallelum devolver um valor errado, ou alguém no caminho trocar a resposta, a referência muda em todas as empresas na mesma madrugada. Hoje é só referência na ficha e em `VEN-01`, sem conta em cima, por isso é baixa.

**O que mudar:** na aplicação (item 6.5), variação maior que 50% contra o mês anterior do mesmo código e ano não é aplicada. O preço fica guardado, o veículo fica com o valor antigo, e vai um aviso ao Sentry (só código, ano e mês). Se a referência passar a entrar em cálculo (financiamento, margem), a gravidade sobe e isso vira obrigatório.

## O que está certo e não precisa mudar

- Nenhum teste chama a API real; `falso` é o padrão.
- O token vem do cofre (ADR 0033), vai num cabeçalho, nunca na URL.
- Centavos por texto, sem `float` (ADR 0003).
- O `public` sem dado de empresa e a rotina lendo só chaves.
- Último valor fica com o mês, sem zero e sem erro para a pessoa.
- Nenhuma dependência nova.

## Próximo passo

- **Arquiteto:** M-01, M-02, M-04 e B-04 no contrato (`veiculos.md`) ou num adendo da ADR 0038, na parte do contrato que já está prevista.
- **Backend:** M-03 (o `before_breadcrumb` pode entrar junto da T-422) e os baixos B-01, B-02, B-03 e B-06 na implementação, com os testes citados.
- **Dono e produto:** B-05 antes de ligar a consulta por placa. Não segura o resto.
- **Segurança:** conferir o PR do backend da T-422 quando abrir.

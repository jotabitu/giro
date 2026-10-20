# T-338 · Cotação da FIPE licenciada · arquiteto → orquestrador, dono, backend

**O que foi feito:** comparei a própria FIPE com três APIs pagas de terceiros, pelo que cada uma publica no site em 20 out 2026. Não criei conta, não assinei nada e não mandei dado do Giro a ninguém. Como o contrato com a FIPE provavelmente proíbe publicar a lista, deixei pronta a ADR 0030 (proposta) com o CSV fora do git.
**Onde:** este handoff, `docs/decisoes/0030-catalogo-de-modelos-fora-do-git.md`, `docs/decisoes/README.md`, `tarefas/backlog.md` (estado da T-338 e a `[decisão]` para o dono).
**Regras cobertas:** `VEI-08` e `VEN-01` (nenhuma regra muda).

## O achado principal

Só a FIPE pode dar uma licença limpa. O site oficial diz: "Todos os direitos reservados à Fipe", "NÃO disponibilizamos download de qualquer tipo de arquivo" e "NÃO disponibilizamos serviço de API". As APIs pagas pegam os dados do site da FIPE e revendem. Nenhuma publica termos de licença nem diz ter autorização da FIPE. Pagar uma delas compra o acesso técnico, não o direito de usar a lista. Juridicamente, é o mesmo risco da opção A da T-337.

## Comparação

| | FIPE (oficial) | fipe.api.br (Parallelum, comunidade) | Tabela Fipe API (ZeroBugs) | fipeapi.site |
| --- | --- | --- | --- | --- |
| Preço mensal | só por contato. Referência: os estados pagam a FIPE por pesquisa sob encomenda para o IPVA (MG, 2020: R$ 41.834,28 por 12 meses, outro serviço) | Pro: R$ 59 para assinante novo (era R$ 49); grátis com limite | Básico: R$ 46,99 com 1.000 pedidos por mês; Custom por contato | R$ 50 (500 por dia) ou R$ 100 (1.000 por dia) |
| Licença da lista | a do contrato; é a única que vale | nenhum termo publicado; código aberto, dado sem licença; sem vínculo com a FIPE | nenhum termo publicado; diz que é "sincronizada com os valores oficiais" | nenhum termo publicado |
| Repositório público | depende do contrato; o provável é não | não dá para afirmar | não dá para afirmar | não dá para afirmar |
| Motos e carros com tipo | sim (a consulta oficial separa carro, moto e caminhão) | sim (`vehicleType`; carros, motos e caminhões) | carros, motos e caminhões; o campo do tipo não está descrito | não descrito |
| Preço para a `VEN-01` | sim, se o contrato incluir | sim, com histórico | sim (por consulta) | sim (por consulta) |
| Entrega | a combinar (pedir CSV mensal) | JSON pela API; CSV completo no Pro; mensal, até 48 h depois da FIPE | JSON por consulta; 1.000 pedidos por mês não bastam para os milhares de modelos | JSON por consulta |
| Contato | formulário em fipe.org.br/pt-br/institucional/contato | fipe.api.br | contato@zerobugs.com.br, WhatsApp (35) 99243-2218 | fipeapi.site |

Também olhei a KBB Brasil (Kelley Blue Book), que tem preço próprio. Ela não publica API nem licença, e a tela diz "Da lista FIPE", então ficou de fora.

## Recomendação para o dono

1. **Pedir a proposta à FIPE**, pelo formulário de contato, em nome da empresa do Giro. Peça por escrito:
   1. licença da lista de marcas e modelos de carros e motos, com o código FIPE e o tipo, para um SaaS que mostra a lista às locadoras clientes no cadastro de veículos;
   2. licença do preço médio mensal, para mostrar como referência ao lado do preço de venda (`VEN-01`), também às locadoras clientes;
   3. se a lista pode ficar num repositório de código público ou só em servidor privado;
   4. entrega em arquivo (CSV ou Excel) todo mês, com a data de publicação;
   5. preço mensal ou anual, reajuste, prazo mínimo e o que acontece com os dados se o contrato acabar;
   6. a forma de citar a fonte ("Fonte: Fipe") nas telas;
   7. se o preço muda com o número de locadoras clientes.
2. **Não assinar uma API de terceiro como se fosse licença.** Se a FIPE recusar ou cobrar caro demais, a escolha volta para a T-337. Uma API paga é a forma mais barata de ter o CSV pronto (fipe.api.br Pro, R$ 59/mês, dá para assinar um mês por trimestre), mas o dono assume o mesmo risco da opção A.
3. **Se a proposta proibir publicar**, a ADR 0030 passa a aceita. Se permitir, a ADR 0030 é descartada, e a T-339 segue como está, com o CSV completo no repositório.

## O que fica para a T-339 (backend)

- Nos dois casos: a carga com `atualizar_catalogo_modelos` e a chave normalizada calculada na leitura do CSV.
- Se a ADR 0030 valer: `GIRO_CATALOGO_MODELOS`, `--destino armazenamento`, a volta à lista curta com o Sentry, a exigência em `prod.py`, o evento `catalogo.atualizar`, o `.gitignore` e o teste de no máximo 200 linhas no CSV versionado.
- A rota `GET /api/veiculos/modelos/` e o formato do CSV não mudam.

**O que ficou de fora:** preço real da FIPE (só por contato) e os termos de uso das APIs, que não estão publicados. A página de termos da fipe.api.br respondeu 404.

**Próximo passo para quem recebe:** orquestrador leva a `[decisão]` ao dono, que manda o pedido à FIPE. Quando a resposta chegar, o arquiteto confere a licença contra a ADR 0030 e marca aceita ou descartada. Só então a T-339 começa. Branch `t-338-cotacao-fipe`, empilhada sobre a `t-337-catalogo-completo` (PR #364), sem PR.

Fontes: [FIPE, Tabela Fipe](https://www.fipe.org.br/pt-br/indices/veiculos), [consulta FIPE](https://veiculos.fipe.org.br/), [fipe.api.br, planos](https://fipe.api.br/pricing), [fipe.api.br, documentação](https://fipe.api.br/docs/comece-aqui), [Tabela Fipe API](https://tabelafipeapi.com.br/), [fipeapi.site](https://www.fipeapi.site/), [contrato de Goiás com a FIPE (2026)](https://goias.gov.br/economia/wp-content/uploads/sites/45/2026/09/CT-027-2026-FIPE.pdf), [inexigibilidade de MG (2020)](https://liferay.meioambiente.mg.gov.br/documents/d/ief/publicacao_doe_divulga_autorizados_pmi_2020_08_20-pdf), [KBB no Brasil](https://www.meioemensagem.com.br/marketing/kelley-blue-book-inicia-operacao-no-brasil).

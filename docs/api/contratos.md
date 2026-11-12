# Contratos: modelos, geração e assinatura

**Dono:** arquiteto · **Versão:** 03 nov 2026 (T-411, copiar o link para assinar); 07 out 2026 (T-038) · **App:** `contratos` (schema da empresa, ADR 0011) · **Regras:** IMP-04, LOC-08, LOC-15, FIN-03, AUD-05, fluxo da retirada (passo 3) · **Segurança:** S-09, S-15 (`docs/seguranca/2026-10-07-fundacao.md`) · **Telas:** Contratos-Modelos, Onboarding-Contrato, Locacao (passo 3)

Convenções gerais em `docs/api/README.md`. Modelo: itens 15 e 16 em `docs/decisoes/modelo-de-dados.md`. O app não conhece a origem do contrato: usa origem genérica (`locacao`; `venda` na fase 2).

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Modelos de contrato (criar, editar, publicar) | sim | — | — | — | — |
| Gerar, enviar e reenviar contrato de uma locação | sim | sim | sim | — | — |
| Assinar | o cliente final, pelo link | | | | |

---

## Modelos (tela `Contratos-Modelos`)

### Marcadores (lista fechada, S-09)

O texto do modelo só aceita marcadores desta lista, escritos como `{{grupo.campo}}`. Cada um é trocado por texto já escapado; não há motor de template sobre o texto da locadora (nada de laços, condições, filtros ou acesso a atributos).

| Grupo | Marcadores |
| --- | --- |
| `empresa` | `nome`, `razao_social`, `cnpj`, `endereco`, `cidade` |
| `filial` | `nome`, `cnpj`, `endereco`, `telefone` |
| `cliente` | `nome`, `cpf` (ou CNPJ), `nascimento`, `endereco`, `celular`, `email`, `cnh_numero`, `cnh_categoria`, `cnh_validade`, `responsavel_nome`, `responsavel_cpf` |
| `veiculo` | `marca`, `modelo`, `placa`, `chassi`, `renavam`, `ano`, `cor`, `km_saida` |
| `locacao` | `codigo`, `inicio`, `fim_previsto`, `periodicidade`, `plano`, `valor` (por período), `caucao`, `diaria_atraso`, `extras`, `forma_pagamento`, `parcelas` (tabela pronta de vencimentos), `tolerancia_atraso` |
| `cobranca` | `multa_atraso_pct`, `juros_mes_pct` |
| `compra` | `plano`, `parcelas` (número), `valor_parcela`, `ultima_parcela` (já com a caução abatida), `prazo` ("24 meses", "104 semanas"). Só no modelo de `finalidade = locacao_compra` (`LOC-16`, T-420); em outro modelo, 400 `marcador_invalido` |
| `contrato` | `data`, `cidade_assinatura` |

- Valores em dinheiro saem formatados ("R$ 329,00"); datas, no fuso da filial ("07/10/2026").
- `FIN-03`: o contrato só permite cobrar juros e multa por atraso se o modelo usar `{{cobranca.multa_atraso_pct}}` e `{{cobranca.juros_mes_pct}}`. O contrato gerado grava `clausula_juros = true` nesse caso; sem os dois, `financeiro` não cobra juros daquela locação.
- Marcadores de venda (`venda.*`) entram na fase 2.

### HTML permitido (S-09)

O texto é HTML sanitizado no servidor ao salvar, com lista branca: `p`, `h1`, `h2`, `h3`, `strong`, `em`, `u`, `ol`, `ul`, `li`, `br`, `hr`, `table`, `thead`, `tbody`, `tr`, `th`, `td`. Sem atributos, exceto `colspan` e `rowspan`. Tudo o mais (`img`, `style`, `link`, `script`, `iframe`, `a`, atributos `style` e `on*`) é removido. O logo da locadora entra pelo cabeçalho fixo do PDF, não pelo texto.

### GET /api/contratos/modelos/
200: `{ "resultados": [ { "id": 10, "grupo": "uuid", "nome": "Locação semanal", "finalidade": "locacao", "versao_publicada": 3, "tem_rascunho": false, "status": "publicado", "contratos_gerados": 38, "editado_em": "..." } ] }`. `status`: `publicado` (tem versão publicada) ou `rascunho` (nunca publicado).

### GET /api/contratos/modelos/{id}/
200: `{ ..., "texto": "<p>...</p>", "marcadores_usados": ["cliente.nome", "..."], "versoes": [ { "versao": 3, "publicado_em": "...", "contratos_gerados": 38 } ] }`.

### GET /api/contratos/marcadores/
A lista acima, com rótulo e exemplo para o painel "Campos automáticos": `{ "resultados": [ { "chave": "cliente.nome", "rotulo": "Nome do cliente", "exemplo": "Lucas Ferreira" } ] }`.

### GET /api/contratos/modelos-prontos/
Modelos prontos para o passo 9 da implantação (`Onboarding-Contrato`) e para "Novo modelo": locação diária, semanal e mensal de moto e de carro. `POST /api/contratos/modelos/` com `{ "a_partir_de": "locacao_semanal_moto" }` cria um rascunho com o texto pronto.

### POST /api/contratos/modelos/
Corpo: `{ nome, finalidade: "locacao", texto }` ou `{ nome, a_partir_de }`. 201: rascunho, versão 1.
`finalidade`: `locacao`, `locacao_compra` (locação com intenção de compra, `LOC-16`, T-420, ADR 0037) ou `venda`. O modelo pronto do Giro "Locação com intenção de compra" traz o prazo, as parcelas, a caução e o abatimento, a transferência na quitação sem valor extra, a perda do que foi pago no encerramento antes do fim e os custos com a locadora. `contratos.selectors.modelo_publicado(finalidade)` serve às duas finalidades de locação; a locação pede a do seu `tipo`.
400 `{ "codigo": "marcador_invalido", "mensagem": "Campo desconhecido: {{cliente.salario}}", "campos": { "texto": [...] } }` (`S-09`).

### PATCH /api/contratos/modelos/{id}/
Corpo: `{ nome?, texto? }`. Editar um modelo publicado cria um rascunho da versão seguinte; a publicada não muda (`LOC-15`: contrato assinado mantém o texto da versão em que foi assinado). 200.

### POST /api/contratos/modelos/{id}/previa/
"Ver com dados reais". Corpo: `{ "locacao_id": 2836 }` (opcional; sem ele, usa os dados de exemplo da tela de marcadores). 200: `{ "html": "<...>" }` renderizado e sanitizado, sem gerar PDF nem gravar nada.

### POST /api/contratos/modelos/{id}/publicar/
200: versão nova publicada; a anterior deixa de ser usada em contratos novos. 400 `marcador_invalido`. Publicar o primeiro modelo de locação marca o passo `contrato` da implantação e libera a `IMP-04`.

### POST /api/contratos/modelos/{id}/arquivar/
Tira o modelo do uso (não apaga). 422 `{ "codigo": "IMP-04", "mensagem": "A empresa precisa de ao menos um modelo de locação publicado" }` se for o último.

---

## Contrato de uma locação

### POST /api/locacoes/{id}/contrato/
Perfis: quem cria locação. Locação `aguardando_retirada`, sem pedido de desconto pendente.
202: `{ "contrato_id": 77, "status": "gerado" }`. Em segundo plano:
1. Monta o HTML do modelo publicado de `locacao` com os marcadores e a versão atual (`versao_modelo`).
2. Gera o PDF numa task Celery com tempo limite de 60 s e memória limitada (S-09). O `url_fetcher` do WeasyPrint só entrega o logo da própria empresa, lido do storage do schema atual; qualquer outra URL (`http`, `https`, `file`, `data` externa, IP interno) é recusada.
3. Grava o `hash_pdf` (SHA-256) e cria o link de assinatura.
4. Envia o link por e-mail, se houver, com a marca da locadora; `status = enviado`. Na fase 1, nada vai ao cliente pelo WhatsApp (ADR 0034; o envio guardado só volta com `GIRO_WHATSAPP_CLIENTE_FINAL`).
422 `IMP-04` sem modelo publicado; 409 `{ "codigo": "contrato_existente" }` se já há contrato vigente não cancelado (use reenviar); 409 `contrato_fora_de_hora` fora de `aguardando_retirada`; 409 `desconto_pendente` com o pedido de desconto aguardando decisão; 409 `{ "codigo": "cancelamento_em_curso", "mensagem": "A locação tem um cancelamento em andamento." }` com pedido de cancelamento pendente ou aprovado (T-263). O detalhe da locação diz antes se o `POST` passa: `acoes.gerar_contrato` (`locacoes.md`).

### Estados e transições do contrato

`contratos.Contrato.TRANSICOES` (T-411). A troca de status é sempre por `contratos.services`, com evento de auditoria:

| De | Para | Quando |
| --- | --- | --- |
| `gerado` | `enviado` | a tarefa de envio manda o link por e-mail (`marcar_enviado`) |
| `gerado` | `assinado` | o cliente assina por um link copiado (`POST .../contrato/link/`) de um contrato com o PDF pronto e nada enviado |
| `gerado` | `cancelado` | `cancelar(contrato, motivo)`, por exemplo no cancelamento da locação (`LOC-12`); o link deixa de valer na hora |
| `enviado` | `assinado` | o cliente assina pelo link enviado ou por um copiado depois |
| `enviado` | `cancelado` | `cancelar(contrato, motivo)` |
| `assinado`, `cancelado` | nenhum | estados finais |

- Copiar o link **não muda o status** (`copiar-link.md`, `locacoes.md`): o `gerado` com o PDF continua `gerado`, e por isso a assinatura também pode sair de `gerado`.
- O `gerado` sem PDF não abre o link (404 no consultar e no assinar) e não deixa copiar (409 `contrato_em_preparo`).
- O contrato pode ficar `gerado`, com o PDF e um link copiado vivo, sem WhatsApp: a tarefa de envio (`contratos_preparar_e_enviar`) não troca um token mais novo que o momento em que entrou na fila (B-02 da T-411) e termina sem enviar. "Reenviar" (`POST /api/locacoes/{id}/contrato/reenviar/`) manda o link de novo, leva o contrato a `enviado` e invalida o link copiado.

### Link de assinatura (S-15)

- Token aleatório de 32 bytes; o banco guarda só o hash (`token_assinatura_hash`).
- Vale **7 dias** (`token_assinatura_expira_em`) e é de **uso único**: depois de assinado, ou ao reenviar, o token anterior deixa de valer.
- O link é `https://<subdominio>.<dominio>/assinar#<token>`: o token vai no fragmento, que não chega a logs de servidor nem a cabeçalho `Referer`. A página lê o fragmento, apaga da barra e chama a API com o token no corpo.
- Rate limit dos endpoints públicos: 10 requisições por minuto por IP e 20 por token.
- **Copiar o link** (T-411, `copiar-link.md`): `POST /api/locacoes/{id}/contrato/link/` (`locacoes.md`) chama `contratos.services.gerar_link(contrato, por)`, que gera um token novo na hora, sem enviar, e devolve o link uma vez. É o único caminho em que o token sai do serviço fora da tarefa de envio. Vale a mesma validade, o mesmo uso único e a mesma página `/assinar`. Copiar e reenviar invalidam um ao outro, porque o banco guarda um hash só.
- **Titular anonimizado** (`AUD-06`): a anonimização anula `token_assinatura_hash` e `token_assinatura_expira_em` dos contratos do titular ainda não assinados (o link deixa de abrir, 404).

### POST /api/publico/assinaturas/consultar/
Público. Corpo: `{ token }`.
200:
```json
{ "empresa": { "nome_exibicao": "Moto Rápida", "logo_url": "...", "cor_marca": "#0E7C66" },
  "contrato": { "codigo": "LOC-2856", "titulo": "Contrato de locação semanal", "cliente_nome": "Lucas Ferreira",
                "pdf_url": "...", "pdf_url_expira_em": "...", "status": "enviado" } }
```
Mostra só o contrato daquele token. `pdf_url` assinada de 15 minutos. Abre o contrato `enviado` ou o `gerado` com o PDF (link copiado antes de qualquer envio, T-411). O `status` vem `enviado` ou `gerado`, e a página mostra os dois do mesmo jeito. O `gerado` sem PDF e o `cancelado` respondem 404.
410 `{ "codigo": "link_expirado", "mensagem": "Este link venceu. Peça um novo à locadora." }`; 410 `{ "codigo": "contrato_ja_assinado" }`; 404 para token desconhecido.

### POST /api/publico/assinaturas/assinar/
Público. Corpo: `{ token, aceite: true, nome_completo }`. Aceita o mesmo contrato que o consultar (`enviado`, ou `gerado` com o PDF) e o leva a `assinado` pelas transições acima. `nome_completo` precisa conferir com o nome do cliente (sem diferenciar maiúsculas e acentos).
200: `{ "status": "assinado", "assinado_em": "..." }`. Grava `assinado_em`, `assinado_ip`, `assinatura_aparelho` e o hash do PDF assinado; o PDF final ganha uma página de registro (data, hora, IP mascarado /24, aparelho, hash).
- **Como o link chegou** (`LOC-15`, T-411, M-02 da revisão de segurança): a página de registro e o evento `contratos.contrato_assinado` levam o canal do token usado (`token_assinatura_canal`): "Link enviado por WhatsApp ou e-mail ao cliente" ou "Link entregue por cópia, gerado por Carla Mendes em 03/11/2026, 10:12". Com `copiado` e o IP da assinatura igual a `token_assinatura_gerado_ip`, o evento marca `mesmo_ip_de_quem_copiou: true` (o PDF não mostra; serve à auditoria e a uma disputa). Nada é bloqueado. Os três campos do canal não são anulados ao assinar, para a prova ficar; `token_assinatura_gerado_ip` fica fora da auditoria. Teste: `test_loc_15_assinatura_por_link_copiado_registra_canal`. Publica `contratos.contrato_assinado`, que grava `contrato_assinado_em` na locação e pode ativá-la.
400 `{ "codigo": "nome_nao_confere", "mensagem": "Digite seu nome completo como está no cadastro" }`; 410 como acima.

### Aditivo de renovação (LOC-08)

`locacoes.services.renovar` chama `contratos.services.gerar_aditivo(locacao)`: mesmo fluxo, `tipo = aditivo`, com o texto padrão de aditivo (novo fim, novo valor e parcelas). A renovação vale na hora; aditivo não assinado em 7 dias (o prazo do link) gera tarefa para os gerentes da filial.

### Interface interna

| Item | Uso |
| --- | --- |
| `contratos.selectors.modelo_publicado(finalidade)` | `IMP-04` (locações recusam confirmar sem modelo). |
| `contratos.services.gerar(origem, dados)` / `gerar_aditivo(...)` / `cancelar(contrato, motivo)` | chamados por `locacoes` (e `vendas` na fase 2). |
| `contratos.services.gerar_link(contrato, por)` | copiar o link para assinar (T-411); devolve `(link, expira_em)`. |
| evento `contratos.contrato_assinado` | assinado por `locacoes` (e `vendas`). |
| `CAMPOS_AUDITORIA` | `token_assinatura_hash` omitido; `assinado_ip` mascarado (/24). |

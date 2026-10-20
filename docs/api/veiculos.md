# Veículos, categorias e preços

**Dono:** arquiteto · **Versão:** 16 out 2026 (T-293, valor do dia na linha Pagamentos; T-286, movimentações; T-275, blocos da ficha); 15 out 2026 (T-247, leitura do CRLV-e); 07 out 2026 (T-036), emendas de 09 out 2026 (T-088) · **App:** `veiculos` (schema da empresa) · **Regras:** VEI-01 a VEI-08, MAN-03, VIS-01, FIN-01, MOV-01 a MOV-06, LOC-01, LOC-02, LOC-15, PLT-03, APR-06, AUD-05 · **ADRs:** 0011, 0015, 0026 · **Telas:** Frota, Veiculo, Veiculo-Novo, Precos · **Critérios:** `docs/qa/criterios/T-247.md` (CA-247-01 a 07)

Convenções gerais em `docs/api/README.md`. Modelo: itens 8 a 10 e apoio (`PrecoCategoria`, `Extra`, `HistoricoStatusVeiculo`, `LeituraKm`, `TransferenciaVeiculo`) em `docs/decisoes/modelo-de-dados.md`.

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver frota e ficha (filiais da pessoa, `USR-07`) | sim | sim | sim | sim | sim |
| Cadastrar e editar veículo, documentos, transferir | sim | sim | — | — | — |
| Registrar km (só para cima) | sim | sim | — | sim | — |
| Corrigir km para baixo | sim | sim (direto, com motivo) | — | pede (`APR-06`) | — |
| Bloquear, desbloquear, colocar à venda, voltar para a frota | sim | sim | — | — | — |
| Baixar | sim | — | — | — | — |
| Categorias, preços e extras | sim | — | — | — | — |

Ver é liberado a todos os perfis no escopo das suas filiais porque toda a operação (nova locação, vistoria, caixa) consulta o veículo; dados de compra (`valor_compra_centavos`) só saem para administrador e gerente. Rendimento e custo de manutenção (`indicadores_financeiros`, `VEI-05`) só saem para administrador, gerente e financeiro; para vendedor e vistoriador a chave vem ausente, não `null` (`USR-09`, T-156). O vistoriador recebe a frota, a ficha e as categorias sem valor em dinheiro: sem nenhum campo `_centavos`, sem `preco_vigente`, `proximo_preco`, `indicadores_financeiros` e `data_compra` (as chaves vêm ausentes); o histórico de preços da categoria e os extras respondem 403 para ele (`USR-09`, T-136).

## Representação do veículo

```json
{
  "id": 501,
  "placa": "SAK1D39",
  "chassi": "9C2KC2210RR004417",
  "renavam": "01289934410",
  "marca": "Honda", "modelo": "CG 160 Fan", "ano_fabricacao": 2025, "ano_modelo": 2025, "cor": "vermelha", "combustivel": "gasolina",
  "tipo_veiculo": "moto",
  "categoria": { "id": 2, "nome": "Street 150–160" },
  "filial": { "id": 1, "nome": "Filial Centro" },
  "status": "disponivel",
  "motivo_status": null,
  "km_atual": 3120, "km_atualizado_em": "2026-10-07T11:00:00Z", "capacidade_tanque_litros": "16.0",
  "preco_vigente": { "diaria_centavos": 5490, "semanal_centavos": 32900, "mensal_centavos": 119000, "caucao_centavos": 30000 },
  "valor_venda_centavos": null, "referencia_fipe_centavos": null,
  "valor_compra_centavos": 1390000, "data_compra": "2025-03-10",
  "entrou_na_frota_em": "2025-03-12",
  "situacao": { "codigo": "disponivel", "rotulo": "Disponível", "tom": "sucesso" },
  "locacao_atual": null,
  "manutencao": { "proxima": { "servico": "Troca de óleo", "km": 5000 }, "os_aberta": null },
  "documentos_resumo": { "pior_situacao": "em_dia" },
  "acoes": { "editar": true, "colocar_a_venda": true, "voltar_para_frota": false, "bloquear": true,
             "desbloquear": false, "transferir": true, "baixar": false, "registrar_km": true, "corrigir_km": true,
             "movimentar": true, "motivo_movimentar": null },
  "movimentacao_aberta": null
}
```

- `placa` sai sem hífen; aceita padrão antigo (`ABC1234`) e Mercosul (`ABC1D23`). `chassi` com 17 letras e números.
- `preco_vigente`: preço da categoria vigente hoje (`LOC-15`). A coluna "Diária" da Frota usa `diaria_centavos`; veículo `a_venda` mostra `valor_venda_centavos`.
- `situacao`: a API decide. Base no `status` do veículo; um bloco com `alerta` (ADR 0015) sobrepõe, ex.: "Atrasado" (`perigo`) quando a locação atual está `devolucao_atrasada`.
- `acoes`: combina perfil, `status` e a tabela de transições; o frontend mostra só o que vier `true`. `corrigir_km` vem `true` também para o vistoriador, que pede a correção (`APR-06`).
- `situacao.tom` pelo `status`: `sucesso` (`disponivel`), `info` (`reservado` e `em_movimentacao`, rótulo "Em movimentação"), `solido` (`alugado`), `alerta` (`em_manutencao`) e `neutro` (`indisponivel`, `a_venda`, `vendido`, `baixado`).
- `valor_compra_centavos` e `data_compra` vêm `null` para quem não é administrador ou gerente.
- `combustivel` (T-247, `VEI-08`): `gasolina`, `etanol`, `flex`, `diesel`, `eletrico`, `hibrido` ou `null` (veículo cadastrado antes). A tela `Veiculo-Novo` já tem o campo.

### Veículo em movimentação (`MOV-03`, T-286, T-300)

O status `em_movimentacao` entra no enum `status` do veículo (e no `?status=`, nas `contagens` e no `historico_status`). Só o veículo `disponivel` passa a ele, ao iniciar a movimentação. O `indisponivel`, o `em_manutencao` e o `a_venda` mantêm o status, e o que mostra a movimentação é o bloco `movimentacao_aberta`.

Veículo `disponivel` depois de iniciar a MOV-0002:
```json
"status": "em_movimentacao", "motivo_status": null,
"situacao": { "codigo": "em_movimentacao", "rotulo": "Em movimentação", "tom": "info" },
"movimentacao_aberta": { "id": 2, "codigo": "MOV-0002", "status": "em_transito", "rotulo": "Em movimentação", "tom": "info" },
"acoes": { "editar": true, "colocar_a_venda": false, "voltar_para_frota": false, "bloquear": false, "desbloquear": false,
           "transferir": false, "baixar": true, "registrar_km": false, "corrigir_km": true,
           "movimentar": false, "motivo_movimentar": "O veículo já está na MOV-0002.",
           "aviso_baixar": "A MOV-0002 será cancelada." }
```

Veículo `indisponivel` (CRLV vencido) com a ida ao despachante agendada:
```json
"status": "indisponivel", "motivo_status": "CRLV vencido",
"situacao": { "codigo": "indisponivel", "rotulo": "Indisponível", "tom": "neutro" },
"movimentacao_aberta": { "id": 1, "codigo": "MOV-0001", "status": "agendada", "rotulo": "Movimentação agendada", "tom": "neutro" }
```

- `situacao` continua pelo `status` (tabela acima). A movimentação não sobrepõe a situação do veículo `indisponivel`, `em_manutencao` ou `a_venda`: a Frota mostra o `situacao` e, ao lado, o `movimentacao_aberta.rotulo` quando o bloco vem.
- `movimentacao_aberta.rotulo` e `tom` são da API: `agendada` → "Movimentação agendada", `neutro`; `em_transito` → "Em movimentação", `info`; `no_local` → "No local de apoio", `info`. A tela não monta o texto a partir do `status`.
- `acoes` com o veículo `em_movimentacao`: nenhuma transição manual (`bloquear`, `colocar_a_venda`, `transferir` e `movimentar` em `false`), porque ele volta pela chegada (`MOV-05`). `registrar_km` também vem `false`, porque o km entra na chegada (`VEI-01`). `baixar` segue a regra de sempre (qualquer status menos `alugado`); com a movimentação aberta, ela é cancelada na baixa, e `acoes.aviso_baixar` traz "A MOV-0002 será cancelada." (T-311).
- `historico_status`: as passagens por `em_movimentacao` vêm com `origem_tipo: "movimentacao"` e `origem_codigo: "MOV-0002"`.
- Vistoriador e financeiro recebem `movimentacao_aberta` como os demais: é o estado do veículo, sem valor em dinheiro.

### Blocos de outros apps (ADR 0015)

| Bloco | Fornecedor | Conteúdo | Antes do fornecedor existir |
| --- | --- | --- | --- |
| `locacao_atual` | `locacoes` | `{ "id", "codigo": "LOC-2841", "status", "cliente_nome": "Carlos Menezes", "inicio", "fim_previsto", "alerta"? }` para locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada` do veículo | `null` |
| `manutencao` | `manutencao` | `{ "proxima": { "servico", "km" } \| null, "os_aberta": { "id", "codigo": "OS-118", "status" } \| null, "alerta"? }` | `null` |
| `locacao_atual.plano` e `locacao_atual.pagamento` (só no detalhe, T-275) | `locacoes` (com `financeiro.selectors`) | ver "Blocos da ficha" | ausentes |
| `manutencao.proxima`, campos novos (só no detalhe, T-275) | `manutencao` | ver "Blocos da ficha" | `null`, como o bloco |
| `vistoria_recente` (só no detalhe, T-275) | `vistorias` | ver "Blocos da ficha" | `null` |
| `movimentacoes` (só no detalhe, T-275) | `movimentacoes` (ADR 0028) | ver "Blocos da ficha" | `null` |
| `movimentacao_aberta` (lista e detalhe, T-286; formato fechado na T-300) | `movimentacoes` | `{ "id", "codigo": "MOV-0001", "status", "rotulo", "tom" }` da movimentação `agendada`, `em_transito` ou `no_local` do veículo; ver "Veículo em movimentação", acima | `null` |
| `indicadores_financeiros` (só no detalhe) | `financeiro` | `{ "rendeu_no_ano_centavos", "custo_manutencao_ano_centavos" }` (`VEI-05`) | `null` |

---

## Frota

### GET /api/veiculos/
Perfis: todos (escopo de filial).
Query: `?status=`, `?tipo_veiculo=moto|carro`, `?categoria=<id>`, `?busca=` (placa, modelo, chassi), `?ordem=placa|-km_atual|modelo`. A filial vem do `X-Filial` (`filiais.md`).
200:
```json
{
  "contagens": { "todos": 86, "disponivel": 16, "alugado": 42, "reservado": 9, "em_manutencao": 7, "a_venda": 12, "indisponivel": 0,
                 "em_movimentacao": 0,
                 "motos": 80, "carros": 6 },
  "resultados": [ { ...representação, sem "indicadores_financeiros"... } ],
  "proximo": "...", "anterior": null
}
```
- `contagens` respeitam os filtros de filial e tipo, não o de status (para as abas). `em_movimentacao` conta só o status (`MOV-03`, T-286).
- `?em_movimentacao=true`: os veículos com movimentação `agendada`, `em_transito` ou `no_local`, em qualquer status (o bloco `movimentacao_aberta`, acima; ADR 0028).
- `?movimentavel=true` (T-300): a escolha do veículo na Nova movimentação. Só os veículos para os quais `acoes.movimentar` viria `true`: `disponivel` sem locação `aguardando_retirada`, `indisponivel`, `em_manutencao` ou `a_venda`, sem movimentação aberta, nas filiais em que o usuário cria movimentação (`MOV-02`, `MOV-03`). Combina com `?busca=` e `?tipo_veiculo=`. A tela não filtra por conta própria, e o 409 `MOV-03` do `POST` continua como última palavra (o veículo pode mudar entre a lista e o envio). Para vendedor, vistoriador e financeiro, a lista vem vazia.
- `vendido` e `baixado` só aparecem com `?status=vendido` ou `?status=baixado` (histórico).
- Exportar: `POST /api/veiculos/exportar/` `{ formato: "planilha" | "csv", filtros }`, só administrador (exportar é da Administração), → 202 `{ "exportacao_id" }`; o arquivo sai pela exportação em segundo plano (`AUD-07`), não na resposta.

### GET /api/veiculos/{id}/
200: representação completa, com `indicadores_financeiros` (só administrador, gerente e financeiro; ausente para os demais) e:
```json
"ocupacao": { "pct": "86.00", "periodo_dias": 90 },
"historico_status": [ { "de": "disponivel", "para": "alugado", "em": "...", "origem_tipo": "locacao", "origem_codigo": "LOC-2841", "motivo": null } ]
```
- `ocupacao` (`VEI-06`): dias `alugado` ÷ dias na frota nos últimos 90 dias, a partir do `HistoricoStatusVeiculo`, excluindo os dias em `a_venda`, `vendido` e `baixado`. Calculada pelo app `veiculos`, pelo tempo exato entre as mudanças de status: conta a fração de dia (`VEI-06`), e um veículo alugado às 14:00 conta 0,42 daquele dia. Com mudanças em dias inteiros, dá o mesmo que contar dias.
- Locações e manutenções da ficha vêm das listas dos outros módulos: `GET /api/locacoes/?veiculo=<id>` e `GET /api/manutencao/ordens/?veiculo=<id>` (contratos de locações e manutenção). O "14 no total" é o `total` da lista de locações; as linhas são as que a lista devolve.

#### Blocos da ficha (T-275, telas `Veiculo-Desktop` e `Veiculo-Mobile`)

O que a ficha de referência mostra e a representação não trazia. Tudo só no `GET /api/veiculos/{id}/`; a lista da Frota não muda. Caso do QXA-4B21 em 07 out (dados de referência das regras):

```json
"locacao_atual": { "id": 2841, "codigo": "LOC-2841", "status": "ativa", "cliente_nome": "Carlos Menezes",
  "inicio": "2026-09-23T12:00:00Z", "fim_previsto": "2026-10-28T12:00:00Z",
  "plano": { "periodicidade": "semanal", "plano_especial": null, "valor_periodo_centavos": 29940 },
  "pagamento": { "situacao": "atrasado", "rotulo": "Parcela 2 atrasada", "conta_id": 28412,
                 "valor_centavos": 30609, "atrasadas": 1, "cobrar": true } },
"manutencao": { "proxima": { "servico": "Troca de óleo", "km": 19900, "faltam_km": 950, "intervalo_km": 1000,
                             "progresso_pct": "5.00", "dias_estimados": null,
                             "depois": { "servico": "Revisão 20 mil", "km": 20000, "faltam_km": 1050 },
                             "nota": "Faltando 500 km, abre uma OS agendada para a devolução." },
                "os_aberta": null },
"vistoria_recente": { "id": 3120, "tipo": "saida", "concluida_em": "2026-09-23T12:10:00Z",
  "vistoriador": { "id": 4, "nome": "João Silva" }, "locacao_codigo": "LOC-2841", "total_fotos": 12,
  "fotos": [ { "id": 901, "posicao": "frente", "url": "https://...assinada...", "url_expira_em": "..." } ],
  "avarias": [ { "id": 51, "descricao": "Risco no tanque, lado esquerdo", "registrada_em": "2026-07-12T14:00:00Z",
                 "preexistente": true, "locacao_codigo": null, "foto_id": 9 },
               { "id": 77, "descricao": "Retrovisor direito trincado", "registrada_em": "2026-09-23T12:05:00Z",
                 "preexistente": false, "locacao_codigo": "LOC-2841", "foto_id": 905 } ] },
"movimentacoes": { "total": 0, "ultimas": [], "em_andamento": null },
"acoes": { "...": "...", "movimentar": false, "motivo_movimentar": "Veículo alugado não se movimenta. O botão volta quando a LOC-2841 for devolvida." }
```

**`locacao_atual.plano`** (`LOC-01`, `LOC-15`): a periodicidade, o nome do plano especial (ou `null`) e o preço do período congelado na locação. A tela monta "Semanal R$ 299,40" com o rótulo da periodicidade e o valor formatado, sem conta. O vistoriador recebe `plano` sem `valor_periodo_centavos` (`USR-09`).

**`locacao_atual.pagamento`** (`FIN-01`, `CLI-07`): a situação das contas a receber da locação (parcelas e caução), de `financeiro.selectors`, com o mesmo status calculado do detalhe da locação.
- `situacao`: `atrasado` (alguma conta vencida e não paga, o sinal `pagamento_atrasado` da locação), senão `vence_hoje`, senão `em_dia`. Locação `aguardando_retirada` sem nenhuma conta vencida também é `em_dia`.
- `conta_id`: a conta mais antiga da situação (a atrasada mais antiga; a que vence hoje); `null` em `em_dia`. `atrasadas`: quantas contas estão atrasadas.
- `valor_centavos` (T-293, decisão do produto na T-290): o **valor do dia** da conta, com multa e juros (`FIN-03`), o mesmo `valor_hoje.total_centavos` do Receber (`financeiro.md`) e da mensagem do Cobrar; nunca o principal. No QXA-4B21 em 07 out: 29940 + 599 de multa + 70 de juros = **30609** ("Parcela 2 atrasada · R$ 306,09"; a referência mostra R$ 299,40, que é o principal). Na conta que vence hoje, o valor do dia é o principal. Com mais de uma atrasada, a soma dos valores do dia delas. `null` em `em_dia`.
- `rotulo`, montado pela API: "Parcela 2 atrasada" (uma parcela), "Caução atrasada", "2 contas atrasadas" (mais de uma), "Parcela 3 vence hoje", "Em dia" (textos confirmados pelo produto na T-290).
- `cobrar`: `true` com `situacao` `atrasado` ou `vence_hoje` e o perfil que cobra (`financeiro.md`: administrador, gerente, vendedor, financeiro). O botão "Cobrar" chama `POST /api/financeiro/contas-receber/{conta_id}/cobrar/` (com mais de uma atrasada, `cobrar-em-lote` com as contas da locação fica para a tela de Contas a receber; a ficha cobra a mais antiga). As recusas silenciosas (conta já cobrada hoje, cliente sem contato) são as de lá.
- O vistoriador não recebe `pagamento` (a chave vem ausente), como não vê os pagamentos no histórico da locação.

**`manutencao.proxima`**, campos novos (`MAN-03`; o fornecedor é o app `manutencao`, que ainda não existe, e até lá o bloco inteiro vem `null` e a tela esconde a Próxima manutenção):
- `servico` e `km`: a preventiva que vence primeiro pelo km. `faltam_km` = `km` − `km_atual` (negativo quando passou). `intervalo_km`: o da regra da empresa para esse serviço (1.000 no óleo, 5.000 na revisão).
- `progresso_pct`: (`intervalo_km` − `faltam_km`) ÷ `intervalo_km`, de 0 a 100 com 2 casas, para a barra. No QXA: (1.000 − 950) ÷ 1.000 = 5,00.
- `depois`: a preventiva seguinte (outro serviço ou o mesmo no próximo intervalo), ou `null`.
- `nota`: o texto do gatilho da `MAN-03` ("Faltando 500 km, abre uma OS agendada." ou, com o veículo alugado, "... agendada para a devolução."); `null` quando a OS agendada já existe (aí vem `os_aberta`).
- `dias_estimados` ("cerca de 6 dias de uso"): `null` até o produto dizer como se calcula o uso médio (`[decisão]` da T-275 no backlog). Com `null`, a tela não mostra o trecho.

**`vistoria_recente`** (`VIS-01`; fornecedor `vistorias`): a última vistoria concluída do veículo (saída ou chegada; `descartada` nunca), que no veículo alugado é a saída da locação atual. `null` se o veículo nunca teve vistoria.
- `tipo`: `saida` ou `devolucao` (a chegada), os mesmos valores de `vistorias.md`. `vistoriador`: o responsável pela vistoria, ou `null` se ela não tem um.
- `fotos`: só as posições fixas (`frente`, `traseira`, `lado_esquerdo`, `lado_direito`, `painel`), na ordem; `total_fotos` conta todas, com as de avaria. URL assinada de 15 minutos (`AUD-05`), gerada a cada `GET`. "Ver as 12 fotos" abre `GET /api/vistorias/{id}/`.
- `avarias`: as avarias abertas do veículo (as de `GET /api/vistorias/avarias/?veiculo=<id>&abertas=true`), da mais antiga para a mais nova. `preexistente: true` é o "já existia, não cobrar"; `locacao_codigo` é a locação em que foi registrada ("registrado na saída da LOC-2841"). Não há campo de lado: o lado faz parte da `descricao`, como na vistoria. Sem valor em dinheiro.
- Perfis: os que fazem vistoria (administrador, gerente, vendedor, vistoriador). O financeiro recebe a chave ausente.
- "As vistorias anteriores" do link não têm lista por veículo neste contrato; a tela abre a vistoria recente. Uma lista `GET /api/vistorias/?veiculo=` fica para quando a tela pedir.

**`movimentacoes`** (`MOV-01` a `MOV-06`, no MVP pela decisão do dono de 16 out 2026; fornecedor: o app `movimentacoes`, contrato em `movimentacoes.md`): `total` de movimentações do veículo, `ultimas` (até 3, mais nova primeiro: `{ "id", "codigo": "MOV-0043", "status", "destino_nome", "paradas": ["Lava Rápido Aldeota"], "iniciada_em", "concluida_em" }`) e `em_andamento` (a movimentação não concluída e não cancelada, com o mesmo formato, ou `null`; no máximo uma, `MOV-03`). "Ver todas" abre `GET /api/movimentacoes/?veiculo=<id>`. Até o app existir, o bloco vem `null`, e `acoes.movimentar` vem `false` com `motivo_movimentar` `null`. O vistoriador e o financeiro não recebem o bloco (a chave vem ausente).

**`acoes.movimentar`** (`MOV-02`, `MOV-03`): `true` para administrador e gerente com acesso à filial do veículo, com o veículo `disponivel`, `indisponivel`, `em_manutencao` ou `a_venda` e sem movimentação `agendada`, `em_transito` ou `no_local`. `motivo_movimentar`: quando o perfil pode movimentar mas o veículo não, o motivo, para a tela mostrar o botão desativado com ele: "Veículo alugado não se movimenta. O botão volta quando a LOC-2841 for devolvida.", "Veículo reservado não se movimenta.", "Veículo vendido não se movimenta.", "Veículo baixado não se movimenta.", "O veículo já está na MOV-0043."; `null` quando `movimentar` é `true` ou quando o perfil não movimenta (aí a tela não mostra o botão).

**`acoes.transferir`** (`MOV-06`, T-286): continua `true` para administrador e gerente com o veículo que pode ser movimentado, mas agora abre a Nova movimentação com o destino em outra filial e a vistoria rápida marcada (CA-246-16); a transferência só vale na chegada. A rota `POST /api/veiculos/{id}/transferir/` saiu (ADR 0028, item 6; removida na T-288 parte 2).

### POST /api/veiculos/
Perfis: administrador, gerente.
Corpo: `{ placa, chassi, renavam?, marca, modelo, ano_fabricacao, ano_modelo, cor, combustivel?, km_atual, categoria_id, filial_id, capacidade_tanque_litros?, valor_compra_centavos?, data_compra?, entrou_na_frota_em? }`. Com o CRLV lido (`VEI-08`), o mesmo corpo vai em `multipart/form-data`, com o bloco do documento ("Preencher pelo CRLV-e", abaixo). Sem `capacidade_tanque_litros`, o combustível do acerto é informado à mão (`DEV-01`).
201: representação (status `disponivel`).
400 `validacao`: placa ou chassi fora do formato, categoria de outra filial, ano inválido.
409 `{ "codigo": "VEI-01", "mensagem": "Já existe um veículo com esta placa", "detalhes": { "campo": "placa", "veiculo_id": 77 } }`; o mesmo para `chassi`. Vale para veículo em qualquer estado, inclusive `vendido` e `baixado`.
422 `PLT-03`: limite de veículos do plano.
Efeitos: grava a primeira `LeituraKm` e o `HistoricoStatusVeiculo` inicial; `atualizar_uso("veiculos", +1)`.
Recompra numa troca (`VEN-05`, `VEI-07`) não passa por aqui: a venda chama `veiculos.services.receber_na_troca(chassi, ...)`, que acha o cadastro pelo chassi e leva o veículo de `vendido` para `indisponivel`.
Regras: VEI-01, PLT-03.

### PATCH /api/veiculos/{id}/
Perfis: administrador, gerente. Corpo: `renavam`, `marca`, `modelo`, `ano_fabricacao`, `ano_modelo`, `cor`, `combustivel`, `categoria_id`, `capacidade_tanque_litros`, `valor_compra_centavos`, `data_compra`.
Não mudam por aqui: `placa` e `chassi` (corrigir é ação do administrador, abaixo), `status`, `km_atual`, `filial`.
Mudar a categoria vale para locações novas; locação em andamento mantém o preço congelado (`LOC-15`).

### POST /api/veiculos/{id}/corrigir-identificacao/
Perfil: administrador. Corpo: `{ placa?, chassi?, motivo }`. Para erro de digitação. 409 `VEI-01` se colidir. Auditoria `operacao`, com antes e depois.

## Ações de status

Todas `POST /api/veiculos/{id}/<acao>/`, respondem 200 com a representação. Transição fora da tabela da seção "Veículos" das regras → 409 `{ "codigo": "transicao_veiculo", "mensagem": "Não é possível <ação> um veículo <status>", "detalhes": { "de": "alugado", "para": "a_venda" } }`.

| Ação | Corpo | De → para | Perfis |
| --- | --- | --- | --- |
| `bloquear` | `{ motivo }` | `disponivel` → `indisponivel` | administrador, gerente |
| `desbloquear` | `{ motivo? }` | `indisponivel` → `disponivel`. 422 `VEI-03` se ainda há CRLV ou seguro vencido | administrador, gerente |
| `colocar-a-venda` | `{ valor_venda_centavos, referencia_fipe_centavos? }` | `disponivel` → `a_venda` (`VEN-01`) | administrador, gerente |
| `voltar-para-frota` | `{}` | `a_venda` → `disponivel`. 409 `VEN-10` se houver venda aberta do veículo | administrador, gerente |
| `baixar` | `{ motivo: "perda_total" \| "roubo" \| "sucata" \| "outro", descricao }` | qualquer, exceto `alugado` → `baixado`, inclusive `em_movimentacao` e com movimentação aberta (abaixo) | administrador |

As transições de locação, vistoria, OS e venda não têm endpoint aqui: acontecem pelos serviços desses módulos.

**Baixa com movimentação aberta** (`MOV-03`, decisão do dono em 16 out 2026, T-310; contrato na T-311): não há 409. A baixa leva o veículo a `baixado` e, na mesma transação, cancela a movimentação `agendada`, `em_transito` ou `no_local` dele com o motivo "Veículo baixado: {motivo}". As despesas das paradas ficam, a transferência não acontece e o veículo fica na filial em que está, que é a de saída. O detalhe está em `movimentacoes.md`, "Baixa do veículo com a movimentação aberta". 200: a representação, com `movimentacao_aberta: null`.
- `acoes.aviso_baixar`: com `acoes.baixar` `true` e `movimentacao_aberta`, o texto para o diálogo da baixa, "A MOV-0001 será cancelada."; senão `null`. A tela mostra o texto como vem.

### POST /api/veiculos/{id}/transferir/ (saiu)
**Saiu do contrato com as movimentações (T-286, ADR 0028, item 6; rota removida na T-288 parte 2).** "Transferir" na ficha abre a Nova movimentação (`MOV-06`), e a transferência acontece na chegada, por `veiculos.services.transferir` com a origem `movimentacao`. O `POST` responde 404. O serviço segue com as regras da `VEI-04` (categoria no destino, `TransferenciaVeiculo`, auditoria com a categoria de antes e a de depois) para a chegada, a importação e o seed.

## Km

### POST /api/veiculos/{id}/km/
Perfis: administrador, gerente, vistoriador. Corpo: `{ km }`.
200: representação. 422 `{ "codigo": "VEI-01", "mensagem": "O km informado é menor que o atual (18.950). Para corrigir, use Corrigir km.", "detalhes": { "km_atual": 18950 } }`.
Vistoria e OS atualizam o km pelos próprios serviços (`VEI-02`); este endpoint é para leitura avulsa. Cada leitura dispara o recálculo das preventivas (`MAN-03`, pelo evento `veiculos.km_atualizado`).

### POST /api/veiculos/{id}/corrigir-km/
Corpo: `{ km, motivo }`.
- Administrador ou gerente: aplica na hora, com `LeituraKm` de correção e auditoria. 200: representação.
- Vistoriador: cria o pedido `APR-06` por `comum.aprovacoes.pedir` (ADR 0019), com origem `veiculo` e `dados` `{ km_novo, km_anterior }`. 202: `{ "pedido_aprovacao": { "id": 88, "tipo": "APR-06", "status": "pendente" } }`. Se o `km` não for menor que o atual, 400 `validacao` em `km`: o vistoriador usa Registrar km. O km muda só quando o gerente aprovar (assinante de `aprovacoes.pedido_decidido` em `veiculos/eventos.py`). Outro pedido igual pendente → 409 `pedido_pendente`.
Regras: VEI-01, APR-06.

## Documentos (VEI-03)

### GET /api/veiculos/{id}/documentos/
200:
```json
{ "resultados": [
  { "id": 9, "tipo": "seguro", "validade": "2026-10-25", "situacao": "vence_em_breve", "dias_para_vencer": 18,
    "arquivo": { "nome": "apolice.pdf", "url": "https://...assinada...", "url_expira_em": "..." } }
] }
```
- Só os documentos ativos (um por tipo). `situacao`: `em_dia`, `vence_em_breve` (30 dias ou menos), `vencido`.
- `arquivo.url` é assinada e vale 15 minutos (`AUD-05`); cada `GET` gera outra.

### POST /api/veiculos/{id}/documentos/
Perfis: administrador, gerente. `multipart/form-data`: `tipo`, `validade`, `exercicio?` (só no `crlv`: o ano do licenciamento, T-247), `arquivo?` (PDF, JPG ou PNG, até 10 MB).
201. Se já existe documento ativo do mesmo tipo, ele fica inativo (renovação). Renovar CRLV ou seguro de veículo `indisponivel` por vencimento não libera sozinho: o gerente usa `desbloquear`.

### GET /api/veiculos/{id}/documentos/historico/
Todos os documentos, inclusive inativos.

---

## Categorias e preços (Precos)

### GET /api/categorias/
Perfis: todos (para escolher na locação e no cadastro). Query: `?filial=<id>` (categorias da empresa + as dessa filial), `?tipo_veiculo=`, `?ativo=`.
200:
```json
{ "resultados": [
  { "id": 2, "nome": "Street 150–160", "tipo_veiculo": "moto", "filial": null, "ativo": true,
    "modelos_resumo": "CG 160, Factor 150", "veiculos": 32,
    "preco_vigente": { "vigente_desde": "2026-10-01", "diaria_centavos": 5490, "semanal_centavos": 32900, "mensal_centavos": 119000, "caucao_centavos": 30000 },
    "proximo_preco": null }
] }
```
`modelos_resumo` e `veiculos` contam só veículos fora de `vendido` e `baixado`. `proximo_preco` mostra um preço já agendado para o futuro.

### POST /api/categorias/ · PATCH /api/categorias/{id}/
Perfil: administrador. Corpo: `{ nome, tipo_veiculo, filial_id? }` e, no `POST`, o primeiro preço em `preco: { diaria_centavos, semanal_centavos, mensal_centavos, caucao_centavos }`.
409 `{ "codigo": "categoria_nome_em_uso" }` (único por nome e filial).
`tipo_veiculo` não muda se a categoria já tem veículos (422 `{ "codigo": "categoria_com_veiculos" }`), porque ele define a CNH exigida (`CLI-02`). Pelo mesmo código, `filial_id` também não muda com veículos na categoria, para nenhum veículo ficar com categoria de outra filial.
`POST /api/categorias/{id}/desativar/` e `/reativar/`: desativada some da escolha em cadastros novos; 422 `categoria_com_veiculos` se ainda houver veículos ativos nela.

### GET /api/categorias/{id}/precos/
Perfis: todos menos o vistoriador (403). Histórico (`LOC-15`), do mais novo ao mais velho: `{ "resultados": [ { "vigente_desde": "2026-10-01", "diaria_centavos": 5490, "semanal_centavos": 32900, "mensal_centavos": 119000, "caucao_centavos": 30000, "alterado_por": "Mariana Costa", "alterado_em": "..." } ] }`.

### POST /api/categorias/{id}/precos/
Perfil: administrador. Corpo: `{ vigente_desde, diaria_centavos, semanal_centavos, mensal_centavos, caucao_centavos }`.
- `vigente_desde` ≥ hoje (o passado não se reescreve). Padrão: hoje.
- Preço novo vale só para contratos novos; contrato assinado mantém o preço da assinatura (`LOC-15`). A resposta traz `"locacoes_em_andamento_mantidas": 12` para a tela avisar.
- 409 `{ "codigo": "preco_ja_definido", "mensagem": "Já existe preço a partir desta data" }` quando a data já tem preço vigente; preço agendado para o futuro pode ser trocado com `PUT /api/categorias/{id}/precos/{vigente_desde}/` até a data chegar. O `PUT` tem o mesmo corpo e responde 200 como o `POST` (com `locacoes_em_andamento_mantidas`); se a data já chegou, 409 `{ "codigo": "preco_ja_vigente" }`.
Caso do seed: Street semanal 29940 até 30 set e 32900 a partir de 01 out; LOC-2841, assinada em 23 set, continua com 29940 (`LOC-15`).

### GET /api/precos/historico/
Perfil: administrador. Todas as mudanças de preço da empresa, para "Histórico de preços": `{ "resultados": [ { "categoria", "vigente_desde", "campo", "antes_centavos", "depois_centavos", "alterado_por", "alterado_em" } ] }`.

## Extras (LOC-02)

`GET /api/extras/` (todos os perfis menos o vistoriador, 403; só os ativos, e `?ativo=false` mostra os desativados) → `{ "resultados": [ { "id", "nome": "Capacete extra", "valor_centavos": 1500, "cobranca": "por_periodo" | "unica", "ativo": true } ] }`.
`POST /api/extras/`, `PATCH /api/extras/{id}/`, `POST /api/extras/{id}/desativar/` · administrador. Mudar o valor vale para locações novas.

Planos especiais (`Entregador`, `Mensal fidelidade`) aparecem na tela `Precos`, mas são do app `locacoes` e ficam no contrato de locações (T-015). As "Regras de cobrança" da mesma tela vêm de `ConfiguracaoEmpresa` (contrato de empresas).

---

## Eventos e interface interna

| Item | Uso |
| --- | --- |
| `veiculos.services.transicionar(veiculo, novo_status, *, origem, motivo=None)` | único caminho para os outros apps mudarem o status (locações, vistorias, manutenção, vendas). Valida a tabela de transições, grava histórico e auditoria. |
| `veiculos.services.atualizar_km(veiculo, km, *, origem)` | vistoria e OS (`VEI-02`). Recusa km menor (`VEI-01`). |
| `veiculos.services.receber_na_troca(chassi, dados)` | venda com troca (`VEN-05`, `VEI-07`). |
| `veiculos.selectors.preco_vigente(categoria, data)` | `LOC-01`, `LOC-15`. |
| evento `veiculos.veiculo_baixado(veiculo_id, motivo_texto)` | publicado por `baixar` dentro da transação, síncrono; assinado por `movimentacoes`, que cancela a movimentação aberta (`MOV-03`, T-311). Falha no assinante desfaz a baixa. |
| evento `veiculos.km_atualizado` | assinado por `manutencao` (preventivas, `MAN-03`). |
| evento `veiculos.documento_vencendo` / tarefa `aut_06_vencimento_de_documentos` | `VEI-03`, `AUT-06`: 30 dias antes avisa; no dia, CRLV ou seguro vencido leva `disponivel` → `indisponivel`; veículo `alugado`, `reservado` ou `em_manutencao` não muda e gera tarefa urgente para os gerentes da filial (`FIL-02`). |
| anotações de leitura fornecidas | `indicadores` de `Filial` (`veiculos`, `ocupacao_pct`), ver `filiais.md`. |

## Preencher pelo CRLV-e (`VEI-08`, ADR 0026, T-247)

Decisão técnica na ADR 0026. A leitura não grava nada; só o `POST /api/veiculos/` grava, depois da conferência da pessoa. Critérios CA-247-01 a 07.

### POST /api/veiculos/leitura-crlv/
Perfis: administrador e gerente (quem cadastra veículo, `pode.veiculos = editar`); os outros perfis, 403 `permissao` (CA-247-07). Token de suporte: só com o acesso "ver e editar"; em "só ver", 403 `PLT-07` (confirmado pela segurança na T-247).
`multipart/form-data`: `arquivo` (o PDF do CRLV-e, até **2 MB**).

200, com `Cache-Control: no-store`:
```json
{ "documento": "crlv",
  "campos": { "placa": "TBC5H21", "chassi": "9C2JC7510SR000123", "renavam": "01234567890",
              "marca": "Honda", "modelo": "Pop 110i ES", "ano_fabricacao": 2025, "ano_modelo": 2026,
              "cor": "vermelha", "combustivel": "gasolina" },
  "lidos": ["placa", "chassi", "renavam", "marca", "modelo", "ano_fabricacao", "ano_modelo", "cor", "combustivel"],
  "quantidade": 9,
  "rotulo": "CRLV-e lido · 9 campos preenchidos",
  "exercicio": 2026,
  "dicas": { "marca_modelo": null },
  "leitura": "<comprovante assinado>" }
```
- `campos` traz só os 9 da `VEI-08`. Campo não lido vem `null` e fica fora de `lidos`. `quantidade` é o tamanho de `lidos`, e a tela usa o `rotulo` como vem ("1 campo preenchido", no singular). Nunca vêm o nome, o CPF ou o CNPJ do proprietário, nem campo fora da lista (CA-247-02).
- `marca` e `modelo` só vêm quando o texto acha um modelo único no catálogo do cadastro (ADR 0026, item 7). Senão, os dois vêm `null`, ficam fora de `lidos`, e `dicas.marca_modelo` traz o texto lido ("HONDA/POP 110I ES") para a tela mostrar como dica (CA-247-05: 7 campos).
- `cor` vem no texto do cadastro, em minúsculas ("vermelha"). `combustivel` vem no enum: `ALCOOL/GASOLINA` vira `flex`, e um valor fora do enum fica fora de `lidos`.
- `exercicio`: o ano do licenciamento, para o documento CRLV; não conta nos 9. A validade do CRLV não vem (`VEI-08`): a pessoa informa.
- `leitura`: comprovante assinado, válido por 30 minutos, sem os valores (ADR 0026, item 8). A tela o guarda junto com o arquivo e manda os dois ao salvar.
- A tela troca os campos lidos pelo que veio e os marca "lido do documento"; os outros campos não mudam.

422 `{ "codigo": "VEI-08", "mensagem": "Não conseguimos ler este documento. Preencha os campos à mão." }`: a mesma resposta para toda falha de leitura (CA-247-06). Isso vale para arquivo que não começa como PDF, acima de 2 MB, com senha, sem texto, com mais de 3 páginas, com tempo ou memória estourados, ou sem nenhum dos 9 campos reconhecido. A causa fica só no log, por código (ADR 0026, item 9).
400 `{ "codigo": "validacao", "campos": { "arquivo": "Envie o PDF do CRLV-e." } }`: arquivo que não é PDF nem pela extensão nem pelos primeiros bytes, como a foto `foto-crlv.jpg`. O seletor da tela já aceita só `.pdf`.
429 `muitas_requisicoes`: acima de 30 por hora por usuário ou de 200 por hora por empresa, somando a leitura da CNH-e (`comum.limites`); as recusas 400 e 422 também contam.
503 `{ "codigo": "leitura_ocupada", "mensagem": "Muitas leituras ao mesmo tempo. Tente de novo em instantes." }` com `Retry-After`: as 2 leituras simultâneas do processo estão ocupadas (ADR 0026, item 6).

### Salvar com o CRLV lido: POST /api/veiculos/ em `multipart/form-data`
O corpo leva os campos do veículo, como no JSON, e mais o bloco do documento:
- `crlv_arquivo`: o mesmo PDF lido (até 2 MB);
- `crlv_validade`, obrigatória quando vem o arquivo (400 `validacao`, "Informe a validade do CRLV."), e `crlv_exercicio?`;
- `leitura?`: o comprovante da leitura.

O serviço faz tudo numa transação só: cria o veículo, com as validações de sempre (`VEI-01`, `PLT-03`), e o `DocumentoVeiculo` `crlv` com o arquivo, a validade e o exercício. No CA-247-04, a placa e o chassi do QXA-4B21 recebem o 409 `VEI-01` de sempre, e nada é criado. O arquivo só vai para o armazenamento privado nesse momento (`AUD-05`); se a transação falhar, o arquivo gravado é apagado, como no logo (`empresas.md`). O nome no armazenamento é gerado pelo backend, nunca o nome enviado.
- Com o `leitura` válido e o SHA-256 do arquivo igual ao do comprovante, o evento `veiculo.cadastrar` leva `preenchido_pelo_documento: { "tipo": "crlv", "campos": [...], "corrigidos": ["cor"] }`, sem valores. A tela da auditoria mostra "Campos preenchidos pelo CRLV-e" (CA-247-03). `campos` são todos os lidos do documento, e `corrigidos`, os que a pessoa mudou antes de salvar. O documento CRLV grava `arquivo_nome` "CRLV-e.pdf", nunca o nome enviado (ADR 0026, item 9).
- Sem comprovante, ou com ele vencido, de outra empresa, de outro usuário ou de outro arquivo: o veículo e o documento são salvos do mesmo jeito, só sem a marca (ADR 0026, item 8).
- O `crlv_arquivo` passa de novo pelos primeiros bytes (`%PDF-`) e pelos 2 MB, sem confiar na leitura, e é gravado com `Content-Type: application/pdf` fixado pelo backend.

### GET /api/veiculos/modelos/ (catálogo, T-257)
É a lista "Da lista FIPE" da tela, local e sem consulta externa. Perfis: todos (quem vê veículos, `pode.veiculos` ≠ `nao`); o suporte em "só ver" também. Query `?tipo=moto|carro`, `?marca=` (igual, sem diferenciar maiúsculas e acento), `?busca=` (cada palavra em marca e modelo) → `{ "resultados": [ { "marca": "Honda", "modelo": "Pop 110i ES", "tipo": "moto" } ] }`, até 50, em ordem de marca e modelo. `tipo` fora da lista: 400 `validacao`.
O catálogo é o arquivo versionado `backend/apps/veiculos/dados/catalogo_modelos.csv`, igual para todas as empresas, atualizado por PR com `python manage.py atualizar_catalogo_modelos <arquivo>` (a tabela FIPE baixada pela equipe, em CSV com `marca`, `modelo` e `tipo`). A leitura do CRLV-e usa `veiculos.catalogo.achar_modelo(texto)`: um modelo só quando o texto normalizado é igual a um `marca + modelo`, ou o começo de um só (ou um só é o começo dele); só a marca não basta.
Catálogo completo (T-337): a fonte está em decisão do dono (backlog, "Levantada pelo arquiteto em T-337"). A rota, o formato do CSV e o comando não mudam. Com milhares de linhas, a tela busca pela rota (`tipo` e `busca`, até 50) e nunca carrega a lista inteira. Na FIPE, o carro tem uma linha por versão ("ARGO DRIVE 1.3 8V Flex" e "... Flex Aut."), então o texto do CRLV-e de carro ("FIAT/ARGO DRIVE 1.3") costuma achar mais de um modelo e vai para `dicas.marca_modelo`, como manda o CA-247-05.

### O que muda para as tarefas (T-247)
- **Backend (sem número):**
  - a dependência `pypdf`, com o motivo no PR;
  - `integracoes/leitura_documentos/`: o processo filho, o parser do CRLV-e e os limites;
  - a rota de leitura e o `POST` em multipart com o documento;
  - `Veiculo.combustivel` e `DocumentoVeiculo.exercicio` (`modelo-de-dados.md`);
  - testes `test_vei_08_le_os_9_campos` (CA-247-01), `test_vei_08_nao_le_o_proprietario` (CA-247-02), `test_vei_08_salva_com_o_documento` (CA-247-03), `test_vei_08_validacoes_de_sempre` (CA-247-04), `test_vei_08_modelo_fora_da_lista` (CA-247-05), `test_vei_08_nao_da_para_ler` (CA-247-06), `test_vei_08_quem_pode` (CA-247-07) e os do processo filho da ADR 0026.
- **Frontend (sem número):** "Preencher pelo documento" para quem tem `pode.veiculos = editar`; os campos marcados, o `rotulo` e as `dicas` como vierem; o arquivo e o `leitura` guardados até o salvar; a mensagem da 422 como vem.
- **Qa:** os arquivos de teste de `docs/qa/criterios/T-247.md`.

# Veículos, categorias e preços

**Dono:** arquiteto · **Versão:** 24 nov 2026 (T-507, aluguel ligado ou desligado, `VEI-21`); 18 nov 2026 (T-494, preços do veículo, `VEI-12` a `VEI-17`, ADR 0041); 05 nov 2026 (T-422, referência FIPE, ADR 0038); 03 nov 2026 (T-414, fotos do veículo, `VEI-10`, ADR 0036; T-421, dados do CRLV-e, rastreador e anotações, `VEI-09`, e leitura do CRLV-e no editar; T-410, "Reservado na LOC-x" e bloco `reserva`); 16 out 2026 (T-293, valor do dia na linha Pagamentos; T-286, movimentações; T-275, blocos da ficha); 15 out 2026 (T-247, leitura do CRLV-e); 07 out 2026 (T-036), emendas de 09 out 2026 (T-088) · **App:** `veiculos` (schema da empresa) · **Regras:** VEI-01 a VEI-10, MAN-03, VIS-01, FIN-01, MOV-01 a MOV-06, LOC-01, LOC-02, LOC-15, PLT-03, APR-06, AUD-05 · **ADRs:** 0011, 0015, 0026, 0036, 0038 · **Telas:** Frota, Veiculo, Veiculo-Novo, Precos · **Critérios:** `docs/qa/criterios/T-247.md` (CA-247-01 a 07), `docs/qa/criterios/T-421.md` (CA-421-01 a 14)

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
| Excluir o veículo sem histórico (`VEI-22`) | sim | sim (sua filial) | — | — | — |
| Categorias, preços e extras | sim | — | — | — | — |
| Ver os preços do veículo (`GET .../precos/`) | sim | sim | sim | — | sim |
| Salvar e simular os preços do veículo, ligar e desligar plano | sim | — | — | — | — |

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
  "situacao": { "codigo": "disponivel", "rotulo": "Disponível", "tom": "sucesso", "desde": null },
  "locacao_atual": null,
  "manutencao": { "proxima": { "servico": "Troca de óleo", "km": 5000 }, "os_aberta": null },
  "documentos_resumo": { "pior_situacao": "em_dia" },
  "acoes": { "editar": true, "colocar_a_venda": true, "voltar_para_frota": false, "bloquear": true,
             "desbloquear": false, "transferir": true, "baixar": false, "registrar_km": true, "corrigir_km": true,
             "movimentar": true, "motivo_movimentar": null },
  "movimentacao_aberta": null,
  "aviso_preco": null,
  "aluguel_ligado": true
}
```

- `aviso_preco` (T-494, `VEI-15`, ADR 0041): na lista e na ficha, em qualquer status, `"A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda."` quando o veículo não tem nenhum plano ligado (de aluguel ou a locação com compra); senão `null`. Não é status: o veículo `disponivel` sem plano vai para `indisponivel` com `motivo_status` "Sem preço · ligue um plano" (seção "Preços do veículo").
- `aluguel_ligado` (T-507, `VEI-21`): o "Oferecer aluguel" do veículo. `false` não é status: a Frota e a ficha mostram o selo neutro "Aluguel desativado" ao lado do status, que continua o dele (seção "Aluguel desligado").

- **Dias em estoque** (T-486, `VEI-18`, `VEI-19`): na lista e na ficha, `a_venda_desde` (data da última entrada no estoque, em `America/Sao_Paulo`), `dias_em_estoque` (inteiro, 0 = colocado à venda hoje) e `parado` (`dias_em_estoque` acima do limite da empresa). Exemplo do PVE-1A07 em 07 out: `"a_venda_desde": "2026-08-15", "dias_em_estoque": 53, "parado": true`.
  - A entrada é a última passagem para `a_venda` no histórico de status, vinda de qualquer estado menos `vendido`: a venda cancelada (`VEN-07`) não recomeça a contagem; voltar para a frota e ser colocado à venda de novo recomeça do zero.
  - Fora de `a_venda`, ou sem entrada no histórico: `a_venda_desde` e `dias_em_estoque` `null`, `parado` `false`; a tela mostra "—".
  - Para o vistoriador, os três campos ficam **ausentes** (não nulos), como os valores.
  - A tela só mostra: "53 dias", "1 dia", "Hoje" com 0, e o tom de alerta quando `parado`.
- `placa` sai sem hífen no campo, e a tela põe o hífen; dentro de um texto montado pela API, sai com hífen (`docs/api/README.md`, Convenções, T-340). Aceita padrão antigo (`ABC1234`) e Mercosul (`ABC1D23`). `chassi` com 17 letras e números.
- `preco_vigente`: preço da categoria vigente hoje (`LOC-15`). A coluna "Diária" da Frota usa `diaria_centavos`; veículo `a_venda` mostra `valor_venda_centavos`.
- `situacao`: a API decide. Base no `status` do veículo; um bloco com `alerta` (ADR 0015) sobrepõe, ex.: "Atrasado" (`perigo`) quando a locação atual está `devolucao_atrasada`.
- `situacao.desde` (T-449, `LOC-10`, "Data e dias do atraso na tela"): data (`"2026-10-14"`, em `America/Sao_Paulo`) do "desde" do card "Agora" da ficha, copiada de `locacao_atual.desde`. Na devolução atrasada, é a data do fim previsto ("Atrasado desde 14 out"); com a locação `ativa` ou `aguardando_retirada`, a do início ("Alugado desde 30 set", "Reservado na LOC-2856 desde 05 nov"). Sem locação aberta, `null`, e a tela mostra só o `rotulo`. A tela não usa `inicio` nem `fim_previsto` para montar esse texto.
- `acoes`: combina perfil, `status` e a tabela de transições; o frontend mostra só o que vier `true`. `corrigir_km` vem `true` também para o vistoriador, que pede a correção (`APR-06`).
- `situacao.tom` pelo `status`: `sucesso` (`disponivel`), `info` (`reservado` e `em_movimentacao`, rótulo "Em movimentação"), `solido` (`alugado`), `alerta` (`em_manutencao`) e `neutro` (`indisponivel`, `a_venda`, `vendido`, `baixado`).
- **Veículo reservado** (T-410, tabela de transições do veículo, CA-410-01, CA-410-06): `situacao.rotulo` é "Reservado na LOC-2856", com o código da locação que reservou, montado pela API a partir do bloco `reserva` (abaixo); tom `info`. Sem bloco (dado antigo, antes do acerto), o rótulo fica "Reservado". A Frota e a ficha mostram o `rotulo` como vem.
  ```json
  "status": "reservado",
  "situacao": { "codigo": "reservado", "rotulo": "Reservado na LOC-2856", "tom": "info", "desde": "2026-10-07" },
  "reserva": { "locacao_id": 2856, "codigo": "LOC-2856", "motivo": "locacao" },
  "locacao_atual": { "id": 2856, "codigo": "LOC-2856", "status": "aguardando_retirada", "cliente_nome": "Lucas Ferreira", "inicio": "2026-10-07T12:00:00Z", "fim_previsto": "2026-10-21T12:00:00Z", "desde": "2026-10-07" }
  ```
  `reserva.motivo`: `locacao` (locação `aguardando_retirada` do veículo; a mesma do `locacao_atual`) ou `troca` (o veículo novo de uma troca pendente, `LOC-09`; aí o `codigo` é o da locação da troca, e o `locacao_atual` do veículo novo continua `null`, porque a locação ainda é do veículo antigo). O link "LOC-2856" abre `/locacoes/{locacao_id}`. Fora do `reservado`, `reserva` vem `null`.
- `valor_compra_centavos` e `data_compra` vêm `null` para quem não é administrador ou gerente.
- `combustivel` (T-247, `VEI-08`): `gasolina`, `etanol`, `flex`, `diesel`, `eletrico`, `hibrido` ou `null` (veículo cadastrado antes). Desde a T-421 (`VEI-09`), visível e editável no cadastro, no editar e na ficha.
- Os campos da `VEI-09` (bloco `documento`, rastreador e anotações) estão em "Dados do documento, rastreador e anotações", abaixo. Vêm no detalhe e nas respostas do `POST` e do `PATCH`; a lista da Frota não os traz.

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
           "aviso_baixar": "A MOV-0002 será cancelada.", "lancar_despesa": true }
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
| `locacao_atual` | `locacoes` | `{ "id", "codigo": "LOC-2841", "status", "cliente_nome": "Carlos Menezes", "inicio", "fim_previsto", "desde": "2026-10-14", "alerta"? }` (`desde`: ver `situacao.desde`) para locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada` do veículo | `null` |
| `manutencao` | `manutencao` | `{ "proxima": { "servico", "km" } \| null, "os_aberta": { "id", "codigo": "OS-118", "status" } \| null, "alerta"? }` | `null` |
| `locacao_atual.plano` e `locacao_atual.pagamento` (só no detalhe, T-275) | `locacoes` (com `financeiro.selectors`) | ver "Blocos da ficha" | ausentes |
| `manutencao.proxima`, campos novos (só no detalhe, T-275) | `manutencao` | ver "Blocos da ficha" | `null`, como o bloco |
| `vistoria_recente` (só no detalhe, T-275) | `vistorias` | ver "Blocos da ficha" | `null` |
| `movimentacoes` (só no detalhe, T-275) | `movimentacoes` (ADR 0028) | ver "Blocos da ficha" | `null` |
| `reserva` (lista e detalhe, T-410) | `locacoes` | `{ "locacao_id", "codigo": "LOC-2856", "motivo": "locacao" \| "troca" }` do veículo `reservado`: a locação `aguardando_retirada` dele ou a troca pendente em que ele é o veículo novo; ver "Veículo reservado", acima. Uma anotação na lista, sem N+1 | `null` |
| `movimentacao_aberta` (lista e detalhe, T-286; formato fechado na T-300) | `movimentacoes` | `{ "id", "codigo": "MOV-0001", "status", "rotulo", "tom" }` da movimentação `agendada`, `em_transito` ou `no_local` do veículo; ver "Veículo em movimentação", acima | `null` |
| `vendas` (só no detalhe, T-420) | `vendas` (`vendas.selectors.vendas_do_veiculo`) | `{ "itens": [...] }`, as vendas do veículo, a mais nova primeiro; ver "`vendas`", abaixo. Para todos os perfis (não traz valores) | `null` (também sem venda) |
| `indicadores_financeiros` (só no detalhe) | `financeiro` | `{ "rendeu_no_ano_centavos", "custo_manutencao_ano_centavos", "despesas_ano_centavos" }` (`VEI-05`, `FIN-17`) | `null` |

**`indicadores_financeiros`** (`VEI-05`, `FIN-17`, T-417), sem as despesas `recusada` e no ano de hoje:
- `custo_manutencao_ano_centavos` ("Custo de manutenção"): só as despesas do veículo nas categorias `manutencao` e `pecas`.
- `despesas_ano_centavos` ("Despesas no ano" da seção "Despesas do veículo"): todas as despesas ligadas ao veículo, de qualquer categoria e filial. É o `total_ano_centavos` de `GET /api/financeiro/despesas/veiculo/{id}/` no ano de hoje.
- `rendeu_no_ano_centavos` ("Rendeu no ano"): receitas de locação recebidas do veículo no ano (de `locacoes`) − `despesas_ano_centavos`. Pode ser negativo. A conta é do `veiculos.selectors`, que junta os dois fornecedores; a tela mostra o número como vem.
- Ex. (CA-417-10): o QXA-4B21 com o óleo de R$ 48,00 tem custo 4800 e despesas 4800; lançado o "IPVA 2026" de R$ 210,00, despesas 25800, custo 4800, e o rendeu cai 21000.

**`vendas`** (`VEN-11`, `LOC-16`, T-420): cada item é
```json
{ "id": 18, "codigo": "VEN-0178", "status": "vendida", "origem": "quitacao_locacao",
  "origem_rotulo": "Quitação de locação", "descricao": "Quitação da LOC-2901",
  "cliente": { "id": 1310, "nome": "Lucas Ferreira" }, "vendida_em": "2028-10-10T13:20:00Z",
  "transferencia": { "feita_em": "2028-10-15", "registrada_por": { "id": 2, "nome": "Rodrigo Pinheiro" }, "pendente": false },
  "transferencia_texto": "Transferência no Detran feita em 15/10/2028 · Rodrigo Pinheiro" }
```
- `transferencia_texto` é a linha do histórico do veículo depois de "Transferência feita" (CA-420-16), montada pela API; `null` enquanto a transferência está pendente. A tela mostra como vem.
- A venda também aparece no `historico_status`: a passagem de `alugado` para `vendido`, com `origem_tipo: "venda"`, `origem_codigo: "VEN-0178"` e o motivo "Quitação da LOC-2901".

**`acoes.lancar_despesa`** (`FIN-17`, T-417): `true` para quem lança despesa (administrador, gerente, vendedor, financeiro e vistoriador), mesmo sem ver a lista, com o recurso `manutencao_despesas` no plano (`PLT-12`). Em qualquer status do veículo. Abre o lançamento com o veículo travado, que vai para `POST /api/financeiro/despesas/veiculo/{id}/` (`financeiro.md`). A lista da seção vem de `GET /api/financeiro/despesas/veiculo/{id}/`, que a ficha só chama quando recebe `indicadores_financeiros` (administrador, gerente e financeiro).

**`acoes.motivo_trocar_tipo`** (`VEI-11`, T-438): para administrador e gerente, a frase que trava o campo Tipo no editar quando o veículo tem locação aberta (`reservado` ou `alugado`, à espera da retirada, ou o novo de uma troca pedida, `LOC-09`): "Este veículo está na LOC-2841. Troque o tipo depois da devolução." Sem o código da locação (dado antigo), "Este veículo está numa locação aberta. Troque o tipo depois da devolução.". `null` quando o tipo troca livre, e sempre `null` para os perfis que não editam. É a mesma frase do 409 `tipo_com_locacao_aberta` do `PATCH`.

---

## Frota

### GET /api/veiculos/
Perfis: todos (escopo de filial).
Query: `?status=`, `?tipo_veiculo=moto|carro`, `?categoria=<id>`, `?busca=` (placa, modelo, chassi), `?ordem=placa|-km_atual|modelo|em_estoque`. A filial vem do `X-Filial` (`filiais.md`).
- `?ordem=em_estoque` (T-486, `VEI-18`): do mais parado para o menos (a entrada mais antiga primeiro, com data e hora), depois a placa; os veículos sem o número (fora do estoque ou sem entrada) vão para o fim. Com `?status=a_venda` e sem `?ordem`, essa é a ordem padrão.
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
- `?movimentavel=true` (T-300): a escolha do veículo na Nova movimentação. Só os veículos para os quais `acoes.movimentar` viria `true`: `disponivel` sem locação `aguardando_retirada` (depois da T-410, o veículo dessa locação é `reservado`; a guarda fica como defesa), `indisponivel`, `em_manutencao` ou `a_venda`, sem movimentação aberta, nas filiais em que o usuário cria movimentação (`MOV-02`, `MOV-03`). Combina com `?busca=` e `?tipo_veiculo=`. A tela não filtra por conta própria, e o 409 `MOV-03` do `POST` continua como última palavra (o veículo pode mudar entre a lista e o envio). Para vendedor, vistoriador e financeiro, a lista vem vazia.
- `vendido` e `baixado` só aparecem com `?status=vendido` ou `?status=baixado` (histórico).
- Exportar: `POST /api/veiculos/exportar/` `{ formato: "planilha" | "csv", filtros }`, só administrador (exportar é da Administração), → 202 `{ "exportacao_id" }`; o arquivo sai pela exportação em segundo plano (`AUD-07`), não na resposta.

### GET /api/veiculos/{id}/
200: representação completa, com `indicadores_financeiros` (só administrador, gerente e financeiro; ausente para os demais) e:
```json
"ocupacao": { "pct": "86.00", "periodo_dias": 90 },
"historico_status": [ { "de": "disponivel", "para": "alugado", "em": "...", "origem_tipo": "locacao", "origem_codigo": "LOC-2841", "motivo": null } ]
```
- `ocupacao` (`VEI-06`): dias `alugado` ÷ dias na frota nos últimos 90 dias, a partir do `HistoricoStatusVeiculo`, excluindo os dias em `a_venda`, `vendido` e `baixado`. Calculada pelo app `veiculos`, pelo tempo exato entre as mudanças de status: conta a fração de dia (`VEI-06`), e um veículo alugado às 14:00 conta 0,42 daquele dia. Com mudanças em dias inteiros, dá o mesmo que contar dias.
- `limite_dias_parado` (T-486, `VEI-19`): o limite de dias em estoque da empresa (padrão 30), para o "Limite da empresa" ao lado de "À venda desde 15 ago · 53 dias". Ausente para o vistoriador.
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
- `situacao`: `atrasado` (alguma conta vencida e não paga, o sinal `pagamento_atrasado` da locação), senão `vence_hoje`, senão `em_dia`. Locação `aguardando_retirada` é sempre `em_dia` (T-410, `LOC-05`): as contas dela não ficam `vence_hoje` nem `atrasada` até a retirada, pelos mesmos `q_vence_hoje` e `q_atrasada` do `financeiro`.
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
- `fotos`: desde a T-414 (`VEI-10`), **todas** as fotos ativas da vistoria, as fixas e as de avaria, com `url_download` e `nome_arquivo`; formato em "Fotos do veículo", abaixo. `total_fotos` = quantas vêm em `fotos`. URL assinada de 15 minutos (`AUD-05`), gerada a cada `GET`. As 12 já estão no bloco, e o visualizador passa por elas; o link "Ver as 12 fotos e as vistorias anteriores" da tela continua abrindo `GET /api/vistorias/{id}/`.
- `avarias`: as avarias abertas do veículo (as de `GET /api/vistorias/avarias/?veiculo=<id>&abertas=true`), da mais antiga para a mais nova. `preexistente: true` é o "já existia, não cobrar"; `locacao_codigo` é a locação em que foi registrada ("registrado na saída da LOC-2841"). Não há campo de lado: o lado faz parte da `descricao`, como na vistoria. Sem valor em dinheiro.
- Perfis: os que fazem vistoria (administrador, gerente, vendedor, vistoriador). O financeiro recebe a chave ausente.
- "As vistorias anteriores" do link não têm lista por veículo neste contrato; a tela abre a vistoria recente. Uma lista `GET /api/vistorias/?veiculo=` fica para quando a tela pedir.

**`movimentacoes`** (`MOV-01` a `MOV-06`, no MVP pela decisão do dono de 16 out 2026; fornecedor: o app `movimentacoes`, contrato em `movimentacoes.md`): `total` de movimentações do veículo, `ultimas` (até 3, mais nova primeiro: `{ "id", "codigo": "MOV-0043", "status", "destino_nome", "paradas": ["Lava Rápido Aldeota"], "iniciada_em", "concluida_em" }`) e `em_andamento` (a movimentação não concluída e não cancelada, com o mesmo formato, ou `null`; no máximo uma, `MOV-03`). "Ver todas" abre `GET /api/movimentacoes/?veiculo=<id>`. Até o app existir, o bloco vem `null`, e `acoes.movimentar` vem `false` com `motivo_movimentar` `null`. O vistoriador e o financeiro não recebem o bloco (a chave vem ausente).

**`acoes.movimentar`** (`MOV-02`, `MOV-03`): `true` para administrador e gerente com acesso à filial do veículo, com o veículo `disponivel`, `indisponivel`, `em_manutencao` ou `a_venda` e sem movimentação `agendada`, `em_transito` ou `no_local`. `motivo_movimentar`: quando o perfil pode movimentar mas o veículo não, o motivo, para a tela mostrar o botão desativado com ele: "Veículo alugado não se movimenta. O botão volta quando a LOC-2841 for devolvida.", "Veículo reservado não se movimenta.", "Veículo vendido não se movimenta.", "Veículo baixado não se movimenta.", "O veículo já está na MOV-0043."; `null` quando `movimentar` é `true` ou quando o perfil não movimenta (aí a tela não mostra o botão).

**`acoes.transferir`** (`MOV-06`, T-286): continua `true` para administrador e gerente com o veículo que pode ser movimentado, mas agora abre a Nova movimentação com o destino em outra filial e a vistoria rápida marcada (CA-246-16); a transferência só vale na chegada. A rota `POST /api/veiculos/{id}/transferir/` saiu (ADR 0028, item 6; removida na T-288 parte 2).

### POST /api/veiculos/
Perfis: administrador, gerente.
Corpo: `{ placa, chassi, renavam?, marca, modelo, ano_fabricacao, ano_modelo, cor, combustivel?, km_atual, categoria_id, filial_id, capacidade_tanque_litros?, valor_compra_centavos?, data_compra?, entrou_na_frota_em?, documento?, rastreador?, anotacoes? }` (os três últimos da `VEI-09`, formato abaixo; todos opcionais, `VEI-01`). Com o CRLV lido (`VEI-08`), o mesmo corpo vai em `multipart/form-data`, com o bloco do documento ("Preencher pelo CRLV-e", abaixo). Sem `capacidade_tanque_litros`, o combustível do acerto é informado à mão (`DEV-01`).
201: representação (status `disponivel`).
400 `validacao`: placa ou chassi fora do formato, categoria de outra filial, ano inválido.
409 `{ "codigo": "VEI-01", "mensagem": "Já existe um veículo com esta placa", "detalhes": { "campo": "placa", "veiculo_id": 77 } }`; o mesmo para `chassi`. Vale para veículo em qualquer estado, inclusive `vendido` e `baixado`.
422 `PLT-03`: limite de veículos do plano.
Efeitos: grava a primeira `LeituraKm` e o `HistoricoStatusVeiculo` inicial; `atualizar_uso("veiculos", +1)`.
Recompra numa troca (`VEN-05`, `VEI-07`) não passa por aqui: a venda chama `veiculos.services.receber_na_troca(chassi, ...)`, que acha o cadastro pelo chassi e leva o veículo de `vendido` para `indisponivel`.
Regras: VEI-01, PLT-03.

### PATCH /api/veiculos/{id}/
Perfis: administrador, gerente. Corpo: `renavam`, `marca`, `modelo`, `ano_fabricacao`, `ano_modelo`, `cor`, `combustivel`, `categoria_id`, `capacidade_tanque_litros`, `valor_compra_centavos`, `data_compra`, `documento`, `rastreador`, `anotacoes` (`VEI-09`), e `leitura?`, o comprovante da leitura no editar (abaixo).
Não mudam por aqui: `placa` e `chassi` (corrigir é ação do administrador, abaixo), `status`, `km_atual`, `filial`.
Mudar a categoria vale para locações novas; locação em andamento mantém o preço congelado (`LOC-15`).

**Tipo do veículo** (`VEI-11`, T-438): o tipo é o `tipo_veiculo` da categoria; não há campo de tipo no veículo. Para trocar de moto para carro (ou o contrário), o `PATCH` manda só o `categoria_id` de uma categoria do tipo novo, e a resposta traz o `tipo_veiculo` dela. Um `tipo_veiculo` no corpo é ignorado.
- **409 `tipo_com_locacao_aberta`**: a categoria nova é de outro tipo e o veículo tem locação aberta (`reservado` ou `alugado`, locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada`, ou troca de veículo pedida, `LOC-09`). Nada é gravado. `{ "codigo": "tipo_com_locacao_aberta", "mensagem": "Este veículo está na LOC-2841. Troque o tipo depois da devolução.", "detalhes": null }`. A mesma frase vem antes em `acoes.motivo_trocar_tipo`.
- Trocar de categoria **sem** mudar o tipo continua livre em qualquer estado em que o veículo se edita.
- **Auditoria** (`AUD-01`): no `veiculo.editar`, a troca de categoria leva `categoria_id` e `categoria_nome` de antes e depois; com troca de tipo, também `tipo_veiculo` (`"moto"` → `"carro"`).
- Testes: `test_vei_11_*` em `tests/aceitacao/test_t438_tipo_do_veiculo.py` (CA-438-04, 07 a 11, 13 e 14).

### POST /api/veiculos/{id}/corrigir-identificacao/
Perfil: administrador. Corpo: `{ placa?, chassi?, motivo }`. Para erro de digitação. 409 `VEI-01` se colidir. Auditoria `operacao`, com antes e depois.

## Dados do documento, rastreador e anotações (`VEI-09`, T-421)

Decisões do dono de 29 e 30 out 2026; regra e formatos na `VEI-09` (PR #459 do produto); critérios CA-421-01 a 14. Modelo: campos novos do item 9 em `modelo-de-dados.md`. Todos opcionais (`VEI-01`); nenhum muda o status nem bloqueia ação nenhuma, nem a alienação nas observações (CA-421-13).

### Na representação

No detalhe (`GET /api/veiculos/{id}/`) e nas respostas do `POST` e do `PATCH`; a lista da Frota não traz. Caso do QXA-4B21 do seed, para o gerente:

```json
"combustivel": "flex",
"documento": { "potencia_cv": 15, "cilindrada_cc": 162, "especie": "passageiro", "tipo": "Motocicleta",
               "carroceria": null, "lotacao": 2, "peso_bruto_kg": 290,
               "numero_motor": "KC22E1P004401", "observacoes": "ALIENACAO FIDUCIARIA" },
"rastreador": { "numero": "356938035643809", "empresa": "Rastreia Fácil" },
"anotacoes": "Risco no tanque, lado esquerdo"
```

- Campo vazio vem `null` (nunca `""`), e a ficha mostra "—" (CA-421-06, CA-421-14). Veículo sem nada: `documento` com todas as chaves `null`, `rastreador` `{ "numero": null, "empresa": null }`, `anotacoes` `null`. Os blocos sempre vêm.
- **`documento.numero_motor` e `documento.observacoes` só para administrador e gerente.** Para vendedor, vistoriador e financeiro, as duas chaves vêm **ausentes**, não `null` (CA-421-12, como `indicadores_financeiros`, `USR-09`). O serializer tira as chaves pelo perfil; a tela não esconde nada por conta própria. O token de suporte recebe como o perfil que ele assume (administrador): o número do motor e as observações não são dado pessoal (`AUD-09` cobre CPF, CNH e documentos de pessoa).
- `especie`: enum `passageiro`, `carga`, `misto`, `competicao`, `tracao`, `especial`, `colecao`. Rótulos da tela: "Passageiro", "Carga", "Misto", "Competição", "Tração", "Especial", "Coleção". A ficha mostra "Passageiro · Motocicleta" (`especie` e `tipo`), ou só o que houver.
- Números sem unidade: a tela põe "15 cv", "162 cc", "2 pessoas" ("1 pessoa"), "290 kg" (com separador de milhar: "1.400 kg"). `combustivel` com os rótulos de sempre ("Flex", "Gasolina", "Etanol", "Diesel", "Elétrico", "Híbrido").

### No cadastro e no editar

`POST /api/veiculos/` e `PATCH /api/veiculos/{id}/` aceitam os mesmos blocos, todos opcionais:

```json
{ "combustivel": "flex",
  "documento": { "potencia_cv": 15, "cilindrada_cc": 162, "especie": "passageiro", "tipo": "Motocicleta",
                 "carroceria": null, "lotacao": 2, "peso_bruto_kg": 290,
                 "numero_motor": "KC22E1P004401", "observacoes": "ALIENACAO FIDUCIARIA" },
  "rastreador": { "numero": "356938035643809", "empresa": "Rastreia Fácil" },
  "anotacoes": "Risco no tanque, lado esquerdo" }
```

- No `PATCH`, cada chave enviada substitui o valor; chave ausente não muda; `null` ou `""` apaga. Vale dentro de `documento` e `rastreador` (mandar `{ "documento": { "lotacao": 1 } }` só muda a lotação).
- No `POST` em `multipart/form-data` (com o CRLV lido), os blocos vão achatados: `documento.potencia_cv`, `rastreador.numero`, `anotacoes` etc., como os outros campos do formulário.
- Texto: espaços das pontas tirados; texto só com espaços vira `null`. `numero_motor` e `rastreador.numero` em maiúsculas, sem espaços. `observacoes` e `anotacoes` guardam as quebras de linha.
- Quem edita: administrador e gerente (`pode.veiculos = editar`); os outros, 403 `permissao` (CA-421-09), como o resto do `PATCH`. O gerente edita também o motor e as observações, que ele vê.
- **Formato** (400 `validacao`, mensagem no campo, nada gravado; CA-421-07):

  | Campo | Aceita | Mensagem |
  | --- | --- | --- |
  | `documento.potencia_cv` | inteiro 1 a 999 | "Informe a potência em cv, de 1 a 999." |
  | `documento.cilindrada_cc` | inteiro 1 a 9999 | "Informe a cilindrada em cc, de 1 a 9999." |
  | `documento.especie` | um do enum | "Escolha a espécie da lista." |
  | `documento.tipo` | até 30 caracteres | "Use até 30 caracteres." |
  | `documento.carroceria` | até 30 caracteres | "Use até 30 caracteres." |
  | `documento.lotacao` | inteiro 1 a 99 | "Informe a lotação em pessoas, de 1 a 99." |
  | `documento.peso_bruto_kg` | inteiro 1 a 99999 | "Informe o peso bruto em kg." |
  | `documento.numero_motor` | letras e números, até 21 | "Use só letras e números, até 21." |
  | `documento.observacoes` | até 500 caracteres | "Use até 500 caracteres." |
  | `rastreador.numero` | letras e números, até 20 | "Use só letras e números, até 20." |
  | `rastreador.empresa` | até 60 caracteres | "Use até 60 caracteres." |
  | `anotacoes` | até 500 caracteres | "Use até 500 caracteres." |

  O erro vem com a chave pontuada: `{ "codigo": "validacao", "campos": { "documento.potencia_cv": ["Informe a potência em cv, de 1 a 999."] } }`. O vendedor, o vistoriador e o financeiro não editam, então não há caso de "editar o que não vê".
- **Auditoria** (`AUD-01`, CA-421-08): o `veiculo.editar` de sempre, com antes e depois de cada campo mudado, com as chaves pontuadas (`documento.lotacao`, `rastreador.numero`, `anotacoes`). A auditoria da empresa só é lida pelo administrador (`auditoria.md`), então o motor e as observações entram inteiros.
- O seed preenche só o QXA-4B21, com os valores da linha "Dados do CRLV-e do QXA-4B21" das regras (fictícios).
- Testes com o código: `test_vei_09_campos_opcionais` (CA-421-06), `test_vei_09_formatos` (CA-421-07), `test_vei_09_combustivel_e_auditoria` (CA-421-08), `test_vei_09_quem_edita` (CA-421-09), `test_vei_09_motor_e_observacoes_por_perfil` (CA-421-11 e 12, chave ausente), `test_vei_09_alienacao_nao_bloqueia` (CA-421-13) e `test_vei_09_veiculo_antigo` (CA-421-14).

## Ações de status

Todas `POST /api/veiculos/{id}/<acao>/`, respondem 200 com a representação. Transição fora da tabela da seção "Veículos" das regras → 409 `{ "codigo": "transicao_veiculo", "mensagem": "Não é possível <ação> um veículo <status>", "detalhes": { "de": "alugado", "para": "a_venda" } }`.

| Ação | Corpo | De → para | Perfis |
| --- | --- | --- | --- |
| `bloquear` | `{ motivo }` | `disponivel` → `indisponivel` | administrador, gerente |
| `desbloquear` | `{ motivo? }` | `indisponivel` → `disponivel`. 422 `VEI-03` se ainda há CRLV ou seguro vencido | administrador, gerente |
| `colocar-a-venda` | `{ valor_venda_centavos, referencia_fipe_centavos? }` (com a referência FIPE da rotina, o valor mandado é ignorado; "Referência FIPE", abaixo) | `disponivel` → `a_venda` (`VEN-01`) | administrador, gerente |
| `voltar-para-frota` | `{}` | `a_venda` → `disponivel`. 409 `VEN-10` se houver venda aberta do veículo | administrador, gerente |
| `baixar` | `{ motivo: "perda_total" \| "roubo" \| "sucata" \| "outro", descricao }` | qualquer, exceto `alugado` → `baixado`, inclusive `em_movimentacao` e com movimentação aberta (abaixo) | administrador |

**Baixa: motivo e descrição** (`VEI-23`, T-518): 400 `validacao` sem `motivo` ou com motivo fora da lista, em `motivo`: "Escolha o motivo da baixa.". `descricao` tem até 200 caracteres em todos os motivos (acima, em `descricao`: "Use até 200 caracteres.") e é obrigatória só no `outro` (ausente, vazia ou só espaços, em `descricao`: "Descreva o motivo da baixa."). Nos outros motivos, é opcional.

**Venda aberta** (`VEN-10`): `voltar-para-frota` e `baixar` com venda em `proposta`, `negociacao` ou `aguardando_aprovacao` respondem 409 `{ "codigo": "VEN-10", "mensagem": "Este veículo tem uma venda em andamento (VEN-0177).", "detalhes": { "venda_id": 177 } }`. O `venda_id` leva o "Ver a venda" do diálogo da ficha (`VEI-23`).

As transições de locação, vistoria, OS e venda não têm endpoint aqui: acontecem pelos serviços desses módulos.

**Baixa com movimentação aberta** (`MOV-03`, decisão do dono em 16 out 2026, T-310; contrato na T-311): não há 409. A baixa leva o veículo a `baixado` e, na mesma transação, cancela a movimentação `agendada`, `em_transito` ou `no_local` dele com o motivo "Veículo baixado: {motivo}". As despesas das paradas ficam, a transferência não acontece e o veículo fica na filial em que está, que é a de saída. O detalhe está em `movimentacoes.md`, "Baixa do veículo com a movimentação aberta". 200: a representação, com `movimentacao_aberta: null`.
- `acoes.aviso_baixar`: com `acoes.baixar` `true` e `movimentacao_aberta`, o texto para o diálogo da baixa, "A MOV-0001 será cancelada."; senão `null`. A tela mostra o texto como vem.

## Excluir o veículo sem histórico (`VEI-22`, T-515)

Para o cadastro feito por engano. Padrão A nos pontos em aberto da T-515: o veículo fica guardado no banco, marcado (`excluido_em`, `excluido_por`), e some de tudo para a locadora; o botão aparece com ou sem histórico, e com histórico a API diz por quê.

### POST /api/veiculos/{id}/excluir/

- **Perfis:** administrador e gerente; o gerente só nas filiais dele (fora delas, 404, como toda rota do veículo, `USR-07`). Vendedor, vistoriador e financeiro: 403 `permissao`. Suporte Giro, nos dois modos: 403 `PLT-07` (`suporte_proibido`).
- **Corpo:** nenhum (`{}`). Sem motivo.
- **200:** `{ "id": 41, "mensagem": "Veículo SAK-1D39 excluído." }`. A tela volta para a Frota e mostra a `mensagem` como vem.
- **409 com histórico:** `{ "codigo": "VEI-22", "mensagem": "Este veículo já tem locação e vistoria. Ele fica guardado e não pode ser excluído.", "detalhes": { "historico": ["locacao", "vistoria"] } }`. `historico` traz os tipos achados, nesta ordem: `locacao`, `troca`, `venda`, `vistoria`, `ordem_servico`, `despesa`, `movimentacao`, `transferencia`; a frase usa os nomes da regra (locação, troca de veículo, venda, vistoria, ordem de serviço, despesa, movimentação, transferência).
- **404:** veículo que não existe, fora do escopo de filiais ou já excluído.

**O que conta como histórico** (qualquer estado, inclusive rascunho, cancelado e `recusada`): locação ou trecho de locação; troca de veículo, como antigo ou novo; venda, como veículo vendido ou recebido na troca; vistoria ou avaria; ordem de serviço (fase 2: sem fornecedor, vale 0); despesa ligada ao veículo; movimentação; transferência entre filiais. Cada app dono registra um contador `historico_<tipo>` no alvo `veiculos.Veiculo` (ADR 0015), sem `recurso=`: o histórico conta mesmo com o módulo desligado no plano.

**O que acontece**, na mesma gravação e com o veículo travado: `excluido_em` e `excluido_por` gravados (o status não muda); os planos ficam `ativo=false`, desligados e sem agendamento; documentos e fotos ficam `ativo=false`, com o arquivo guardado, como a foto apagada (`VEI-10`); o uso do plano desce 1 quando o veículo estava na frota (`PLT-03`). Evento `veiculo.excluir` ("Excluiu o veículo SAK-1D39"), com o código da placa e, no `antes`, placa, chassi, marca, modelo, anos, filial e status.

**Depois:** o manager padrão (`Veiculo.objects`) tira o excluído de todas as consultas: Frota, filtros, busca, contagens, Nova locação, troca, início, relatórios, importação; a ficha responde 404. A placa e o chassi ficam livres (`VEI-01`: as constraints `veiculo_placa_unica` e `veiculo_chassi_unico` valem só fora do excluído). `Veiculo.todos` vê também os excluídos (conferência da equipe Giro).

### Na ficha: `acoes.excluir`

Só no `GET /api/veiculos/{id}/` (não vem na Frota). `null` para quem não exclui (vendedor, vistoriador, financeiro e o suporte Giro): o botão não aparece. Para administrador e gerente, sempre um objeto:

| Campo | Sem histórico | Com histórico |
| --- | --- | --- |
| `permitido` | `true` | `false` |
| `titulo` | "Excluir a SAK-1D39?" | "Este veículo não pode ser excluído" |
| `texto` | "Use só para um cadastro feito por engano. A moto sai da frota e de todas as listas, com as fotos, os documentos e os preços. A placa e o chassi ficam livres para um novo cadastro. Não dá para desfazer." (carro: "O carro") | `null` |
| `motivo` | `null` | a frase do 409 |
| `caminho` | `null` | administrador: "Para tirar a moto da frota, coloque à venda ou faça a baixa (perda total, roubo ou sucata)."; gerente: "... coloque à venda ou peça a baixa ao administrador (perda total, roubo ou sucata)." (carro: "o carro") |
| `historico` | `[]` | os tipos achados |

O aviso com histórico mostra `motivo` e, em seguida, `caminho`; o botão "Colocar à venda" do aviso segue `acoes.colocar_a_venda`. Os botões ("Excluir veículo", "Manter veículo", "Fechar") são da tela.

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

## Fotos do veículo (`VEI-10`, T-414, ADR 0036)

Duas origens que nunca se misturam: a **galeria** (`veiculos.FotoVeiculo`, modelo de dados, item 9a), que se muda no editar, e as **fotos da última vistoria** (bloco `vistoria_recente`, de `vistorias`), só para ver e baixar. Critérios: `docs/qa/criterios/T-414.md` (CA-414-01 a 14). Telas: `Veiculo-Editar-*` (galeria), `Veiculo-*` (ficha) e `Veiculo-Visualizador-*`.

### Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro | Suporte Giro |
| --- | --- | --- | --- | --- | --- | --- |
| Ver a galeria na ficha | sim | sim | sim | sim | sim | "ver e editar": sim; "só ver": sem os links |
| `GET .../fotos/` (galeria do editar) | sim | sim | sim | sim | sim | "ver e editar": sim; "só ver": 403 `PLT-07` |
| Enviar, trocar, apagar, usar como capa | sim | sim | 403 | 403 | 403 | 403 `PLT-07`, mesmo em "ver e editar" |
| Ver as fotos da última vistoria na ficha | sim | sim | sim | sim | chave ausente | "ver e editar": sim; "só ver": sem os links |

**Suporte Giro em "só ver"** (ADR 0013, item 2: no "só ver" não se gera URL assinada de documento nem de foto, mesmo em leitura; revisão de segurança de 10 nov 2026, M-01): na ficha, `galeria` e `vistoria_recente` vêm completos (`total`, `numero`, `rotulo`, `nome_arquivo`, datas), mas cada foto traz `url`, `url_download` e `url_expira_em` nulos. `GET .../fotos/` responde 403 `PLT-07`. Em "ver e editar", o suporte recebe os links como o administrador.

Escopo de filial como no resto do veículo (`USR-07`): veículo de filial fora do escopo responde 404. As mudanças valem em qualquer `status`, menos `vendido` e `baixado`: 409 `{ "codigo": "VEI-10", "mensagem": "A galeria de veículo vendido fica só para ver." }` (ou "... de veículo baixado ..."). A conferência do status vem antes da do arquivo.

### A foto, nas duas origens

```json
{
  "id": 7001,
  "numero": 1,
  "rotulo": "Frente",
  "capa": true,
  "url": "https://...assinada...",
  "url_download": "https://...assinada...&response-content-disposition=attachment...",
  "url_expira_em": "2026-10-07T13:15:00Z",
  "nome_arquivo": "QXA-4B21-galeria-1.jpg",
  "enviada_em": "2025-03-12T13:02:00Z",
  "enviada_por": { "id": 1, "nome": "Mariana Costa" }
}
```

- `url` abre a foto (inline); `url_download` baixa com o `nome_arquivo` (`Content-Disposition: attachment`, ADR 0036, item 4). Os dois valem 15 minutos e são novos a cada `GET` (`AUD-05`). A tela usa `url_download` no "Baixar" e não monta nome nem link. Depois de `url_expira_em`, ela recarrega a ficha (ou a galeria) para ter links novos antes de abrir ou baixar (CA-414-12).
- `numero`: a posição na exibição, de 1 a `total`, capa primeiro. É o que vai no nome: "QXA-4B21-galeria-1.jpg", "QXA-4B21-galeria-2.png" (a extensão é a do formato guardado). Muda quando a capa muda.
- `rotulo`: na galeria, `null`: a foto da galeria não tem posição nem legenda (`VEI-10`), e a tela mostra "Foto 1 de 3". As legendas "Frente", "Traseira" e "Painel" das fotos da galeria na tela de referência são ilustração; a ficha não as mostra. Na vistoria, o rótulo da posição: "Frente", "Traseira", "Lado esquerdo", "Lado direito", "Painel", e "Avaria 1", "Avaria 2" nas de avaria, na ordem em que foram tiradas.
- `capa`, `enviada_em` e `enviada_por` só na galeria. Na vistoria, a foto traz `posicao` (`frente`, `traseira`, `lado_esquerdo`, `lado_direito`, `painel`, `avaria`), `tirada_em` e `avaria_id` (a avaria ligada à foto, ou `null`).
- Nome na vistoria: `<placa com hífen>-vistoria-<saida|chegada>-<posição>.<ext>`, com a posição em minúsculas e hífen: "QXA-4B21-vistoria-saida-frente.jpg", "QXA-4B21-vistoria-saida-lado-esquerdo.jpg", "QXA-4B21-vistoria-saida-avaria-1.jpg". `chegada` é a vistoria `tipo = devolucao`.
- `nome_arquivo` só leva `A-Z`, `a-z`, `0-9`, `-` e `.` (ADR 0036).

### Na ficha: `GET /api/veiculos/{id}/`

Dois blocos novos e uma ação nova, só no detalhe (a lista da Frota não muda; a capa no catálogo é da T-418):

```json
"galeria": {
  "total": 3, "limite": 20,
  "fotos": [ { "id": 7002, "numero": 1, "capa": true, "...": "..." },
             { "id": 7001, "numero": 2, "capa": false, "...": "..." },
             { "id": 7003, "numero": 3, "capa": false, "...": "..." } ]
},
"vistoria_recente": { "id": 3120, "tipo": "saida", "rotulo_tipo": "Vistoria de saída", "concluida_em": "2026-09-23T12:10:00Z",
  "locacao_codigo": "LOC-2841", "total_fotos": 12,
  "fotos": [ { "id": 901, "numero": 1, "posicao": "frente", "rotulo": "Frente", "tirada_em": "...", "avaria_id": null,
               "url": "...", "url_download": "...", "url_expira_em": "...", "nome_arquivo": "QXA-4B21-vistoria-saida-frente.jpg" } ],
  "...": "o resto do bloco como em Blocos da ficha" },
"acoes": { "...": "...", "editar_fotos": true }
```

- `galeria`: todas as fotos ativas, capa primeiro e depois pela ordem de envio, para todos os perfis. Sem foto: `{ "total": 0, "limite": 20, "fotos": [] }`; a tela mostra "Nenhuma foto do veículo." e, com `acoes.editar_fotos`, "Adicionar fotos", que abre o editar (CA-414-13).
- `vistoria_recente.fotos` passa a trazer **todas** as fotos ativas da vistoria (antes, só as 5 fixas): as fixas na ordem das posições e depois as de avaria pela hora, com `numero` de 1 a `total_fotos`. `rotulo_tipo`: "Vistoria de saída" ou "Vistoria de chegada". A tela monta "Vistoria de saída · LOC-2841 · 23 set" com `rotulo_tipo`, `locacao_codigo` e a data de `concluida_em`. Para o financeiro a chave continua ausente; sem vistoria concluída, `null`, e a seção não aparece (CA-414-11, 13).
- `acoes.editar_fotos`: `true` para administrador e gerente com o veículo fora de `vendido` e `baixado`; `false` para os outros perfis e para o suporte Giro. A tela mostra "Gerenciar fotos", "Adicionar fotos" e os botões do editar só com `true` (CA-414-08, 09).
- O visualizador passa só pelas fotos da origem aberta: a ordem é a de `fotos` de cada bloco (CA-414-10, 14).

### GET /api/veiculos/{id}/fotos/
Perfis: todos (escopo de filial). A galeria para o editar, no mesmo formato do bloco `galeria`, com `editar` e `motivo`:
```json
{ "total": 3, "limite": 20, "editar": true, "motivo": null, "fotos": [ ... ] }
```
- `editar`: o mesmo `acoes.editar_fotos`. `motivo`: com o perfil que edita e o veículo `vendido` ou `baixado`, a mensagem do 409, para a tela mostrar a galeria só para ver; `null` nos outros casos.

### POST /api/veiculos/{id}/fotos/
Perfis: administrador, gerente. `multipart/form-data`: `arquivo` (um só; ADR 0036, item 3). 201: a galeria inteira, no formato do `GET`, com `foto_id` da nova.
- Uma foto por requisição. A tela envia as fotos escolhidas **uma depois da outra**, na ordem da escolha, e mostra a recusa de cada uma no item dela; as outras seguem (CA-414-02, 03).
- A primeira foto ativa do veículo vira capa (CA-414-05). A nova entra no fim da ordem.
- 400 `validacao`, `campos.arquivo`:
  - fora de JPG ou PNG pelo conteúdo, acima de 10 MB, PDF, HEIC ou imagem que não abre: `["Envie uma foto JPG ou PNG de até 10 MB."]`;
  - com 20 ativas: `["O veículo já tem 20 fotos. Apague uma para enviar outra."]`.
- Arquivo acima de 12 MB volta 413 do proxy, antes do Django: a tela mostra a mesma "Envie uma foto JPG ou PNG de até 10 MB.". A tela pode recusar antes de enviar o que passa de 10 MB ou não é `.jpg`, `.jpeg` ou `.png`, mas a palavra final é a da API.
- Auditoria `veiculo.foto_enviar` (objeto: o veículo; `detalhes`: `foto_id`, `numero`, `capa`, `arquivo`), sem a imagem (`AUD-01`). `arquivo` é só o nome do arquivo como veio do aparelho, sem pasta (`moto.png`).
- **Na lista da auditoria (T-460)**, os quatro eventos da galeria vêm com a placa com hífen em `objeto.codigo` (`TBC-5H22`) e com `resumo` e `detalhe` prontos, só com nome do arquivo, número da foto e capa:

| `acao` | `resumo` | `detalhe` |
| --- | --- | --- |
| `veiculo.foto_enviar` | Enviou uma foto do veículo TBC-5H22 | `moto.png · foto 1 · virou a capa` ou `lateral.jpg · foto 2 · não é a capa` |
| `veiculo.foto_trocar` | Trocou uma foto do veículo TBC-5H22 | `lateral-nova.png · foto 2 · não é a capa` (ou `é a capa`) |
| `veiculo.foto_capa` | Mudou a capa do veículo TBC-5H22 | `a foto 3 virou a capa` (o número de antes da troca) |
| `veiculo.foto_apagar` | Apagou uma foto do veículo TBC-5H22 | `foto 1 · era a capa; a mais antiga virou a capa`, `foto 1 · era a capa` ou `foto 2 · não era a capa` |

  Nos eventos gravados antes da T-460, sem código nem `arquivo`, o `resumo` leva a placa atual do veículo e o `detalhe`, só o que o evento tem; `objeto.codigo` continua `null` neles.
- **Cadastrar e editar na lista da auditoria (T-464, `VEI-01`):** `veiculo.cadastrar` e `veiculo.editar` também vêm com a placa com hífen em `objeto.codigo` e com o `resumo` "Cadastrou o veículo QAB-1C23" ou "Editou o veículo PNB-7C04". O `detalhe` não muda (vazio). Nos eventos gravados antes da T-464, sem código, o `resumo` leva a placa atual do veículo e `objeto.codigo` continua `null`. Testes: `test_vei_01_*` em `tests/aceitacao/test_t464_auditoria_cadastro_veiculo.py`.

### POST /api/veiculos/{id}/fotos/{foto_id}/trocar/
Perfis: administrador, gerente. `multipart/form-data`: `arquivo`. 200: a galeria, com `foto_id` da nova.
- A antiga fica inativa (`substituida_por`); a nova fica na mesma posição e com a mesma `capa` (CA-414-06). O total não muda, e o limite de 20 não se aplica.
- 400 como no envio. 404 `nao_encontrado` se a foto não é ativa deste veículo.
- Auditoria `veiculo.foto_trocar` (`detalhes`: `foto_id_antiga`, `foto_id_nova`, `numero`, `capa`, `arquivo` da nova).

### POST /api/veiculos/{id}/fotos/{foto_id}/capa/
Perfis: administrador, gerente. Sem corpo. 200: a galeria. A escolhida vira capa e passa a `numero` 1; a anterior perde a marca. Já capa: 200 sem mudança e sem evento.
- Auditoria `veiculo.foto_capa` (`detalhes`: `foto_id`, `capa_anterior_id`, `numero` de antes de virar capa).

### POST /api/veiculos/{id}/fotos/{foto_id}/apagar/
Perfis: administrador, gerente. Sem corpo. 200: a galeria.
- A foto fica inativa (`ativo = False`, `apagada_por`), com o arquivo guardado; não volta pela tela nem pela API (CA-414-07). Apagada a capa, a ativa mais antiga vira capa (CA-414-05).
- A tela pede confirmação antes ("Apagar esta foto? Ela sai da galeria e da ficha.").
- Auditoria `veiculo.foto_apagar` (`detalhes`: `foto_id`, `numero` de antes de apagar, `era_capa`, `nova_capa_id`), com quem e quando.

### Para o catálogo (T-418)
`veiculos.selectors.galeria(veiculo)` devolve as fotos ativas na ordem de exibição, e `veiculos.selectors.capa(veiculo)` a capa ou `None`, para o app `vendas` ler sem tocar no model (ADR 0011).

---

## Referência FIPE (`VEN-01`, `VEI-08`, T-422, ADR 0038)

A referência de preço FIPE do veículo, atualizada uma vez por mês por uma rotina que consulta a API aberta da Parallelum de madrugada. Nenhuma rota abaixo chama a API externa, salvo a consulta por placa (desligada por padrão). O cadastro e a ficha nunca esperam a Parallelum. Modelo: item 9 (campos `fipe_*` e `referencia_fipe_*`) e "Apoio do public" (`PrecoFipe`, `AnosFipe`, `RodadaFipe`) em `docs/decisoes/modelo-de-dados.md`.

### Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver a referência na Frota e na ficha | sim | sim | sim | sem o valor | sim |
| Escolher a versão FIPE, digitar o código ou limpar | sim | sim | — | — | — |
| Consulta por placa (quando ligada) | sim | sim | — | — | — |

O suporte Giro segue o modo do acesso ("só ver" recebe 403 `PLT-07` nas escritas).

### Na representação (lista e detalhe)

`referencia_fipe_centavos` continua no lugar de sempre, com o mesmo valor. Ao lado, o bloco novo:

```json
"referencia_fipe": {
  "valor_centavos": 1302300,
  "mes": "2026-10",
  "rotulo": "Referência FIPE · outubro de 2026",
  "origem": "fipe",
  "situacao": "ok",
  "aviso": null,
  "versao": "CG 160 FAN ESDi FLEXONE",
  "codigo_fipe": "811134-0",
  "ano": "2017 Flex",
  "versoes": []
}
```

- `situacao` (o `fipe_situacao` do veículo):
  - `ok`: a versão é conhecida e a rotina já trouxe o preço. `origem` `fipe`.
  - `aguardando`: a versão foi escolhida ou casada, e o preço chega na próxima rodada. `valor_centavos` e `mes` ficam com o último valor, se havia.
  - `escolher_versao`: mais de uma versão serve. `versoes` traz até 5 candidatas `[ { "marca_id": 22, "modelo_id": 5585, "versao": "CRUZE LT 1.4 16V Turbo Flex Aut." } ]`.
  - `nao_encontrado`: nenhuma versão do catálogo bate.
  - `sem_versao`: veículo que ainda não passou pelo casamento (antes da primeira rodada).
- `aviso`, montado pela API (textos do produto, PR #481, `VEN-01`); a tela mostra como vem:

  | Situação | Com `acoes.escolher_versao_fipe` | Sem |
  | --- | --- | --- |
  | `aguardando` e `sem_versao` | "A referência FIPE chega na próxima atualização, feita de madrugada." | o mesmo |
  | `escolher_versao` | "Escolha a versão FIPE para ver a referência." | "Falta escolher a versão FIPE. O gerente ou o administrador escolhe." |
  | `nao_encontrado` | "Versão FIPE não encontrada. Escolha a versão ou digite o código." | "Versão FIPE não encontrada. O gerente ou o administrador escolhe a versão ou digita o código." |
  | `ok` com o `mes` dois ou mais meses antes do mês corrente (`America/Sao_Paulo`) | "Esta referência é de agosto de 2026 e não foi atualizada." | o mesmo |
  | `ok` com até um mês de atraso, e a origem `manual` | `null` | `null` |

- `origem`: `fipe` (rotina), `manual` (informado em "Colocar à venda", sem versão) ou `null` (sem valor).
- `mes`: `"AAAA-MM"` do preço; `null` sem valor ou na origem `manual`. `rotulo`, montado pela API: "Referência FIPE · outubro de 2026" na origem `fipe`, "Referência FIPE · informada à mão" na `manual`, `null` sem valor. A ficha e o "Valor de venda (FIPE)" mostram o `rotulo` e o valor como vêm (`VEN-01`).
- **Valor antigo** (a API saiu do ar ou a FIPE tirou a versão): o bloco fica com o último `valor_centavos` e o `mes` dele, `situacao` `ok`, sem erro (ADR 0038, item 7). Com um mês de atraso, é o normal da virada da tabela, e não há aviso; com dois ou mais, vem o aviso de valor antigo da tabela acima. A conta é da API, não da tela.
- O vistoriador recebe o bloco sem `valor_centavos` (e sem `referencia_fipe_centavos`), como os outros valores (`USR-09`).
- `acoes.escolher_versao_fipe`: `true` para administrador e gerente com o veículo fora de `vendido` e `baixado`. A tela mostra "Escolher versão" (com `escolher_versao` ou `nao_encontrado`) e "Trocar versão" (nos outros) só com `true`.
- Frota: `?fipe_situacao=escolher_versao` (ou outro valor) filtra, para a lista "veículos sem referência FIPE".

### Escolher a versão no cadastro e no editar

`POST /api/veiculos/` e `PATCH /api/veiculos/{id}/` aceitam o bloco opcional `fipe`, com uma das três formas:

```json
"fipe": { "marca_id": 80, "modelo_id": 7329 }
"fipe": { "codigo_fipe": "811134-0" }
"fipe": null
```

- `marca_id` e `modelo_id` vêm de `GET /api/veiculos/modelos/` (abaixo), da linha escolhida na lista "Da lista FIPE" (a mesma escolha da T-415). Têm de existir no catálogo e ser do mesmo `tipo` do veículo: senão, 400 `validacao` em `fipe`: "Escolha uma versão da lista FIPE.".
- `codigo_fipe`: seis dígitos, hífen e um dígito (`^\d{6}-\d$`); fora disso, 400 em `fipe.codigo_fipe`: "Digite o código FIPE no formato 811134-0.". O código não é conferido na hora (não há chamada externa); se a rotina não o achar, o veículo fica `nao_encontrado`.
- Com `marca_id` e `modelo_id` ou `codigo_fipe`: grava os campos, limpa `fipe_versoes` e põe `situacao` `aguardando`. O valor e o mês antigos ficam até a rotina trazer o novo.
- `fipe: null`: limpa a versão, o código, o valor e o mês, e o veículo volta ao casamento na próxima rodada (`sem_versao`).
- Sem a chave `fipe` no corpo, nada muda. Mudar `marca`, `modelo`, `ano_modelo` ou `combustivel` no `PATCH` sem mandar `fipe` limpa a versão como em `fipe: null` (ADR 0038, item 3).
- No `vendido` e no `baixado`, o `PATCH` com `fipe` responde 409 `transicao_veiculo`, como as outras edições.
- **Formatos fechados** (ADR 0038, item 9.1, M-01 da segurança), conferidos no serializer e de novo no cliente antes de montar a URL: `codigo_fipe` `^\d{6}-\d$`; `marca_id` e `modelo_id` inteiros positivos; o ano FIPE (`fipe_ano_codigo`, `^\d{4,5}-\d$`) e a referência (`^\d{1,4}$`) nunca vêm do cliente, só da rotina. Com `escolher_versao`, `marca_id` e `modelo_id` têm de ser de uma das `versoes` guardadas no veículo ou de uma linha do catálogo do mesmo tipo; senão, 400 "Escolha uma versão da lista FIPE.".
- **Só de leitura** (item 9.4, B-04): `fipe_situacao`, `referencia_fipe_origem`, `referencia_fipe_mes`, `fipe_versao`, `fipe_ano_codigo` e, com `situacao` `ok`, `referencia_fipe_centavos`. Mandados no corpo, são ignorados (não dão 400), e a resposta traz os valores que valem.
- Auditoria: a escolha da pessoa gera o evento de edição do veículo com os campos FIPE de antes e de depois (`AUD-01`). O que a rotina muda gera um evento de lote por empresa a cada aplicação, `veiculo.referencia_fipe_rotina`, ator Sistema, com a lista dos veículos e a situação, o valor e o mês de antes e de depois (ADR 0038, item 9.4).

Atalho na ficha, sem abrir o editar: `POST /api/veiculos/{id}/fipe/` com o mesmo bloco (`{ "marca_id", "modelo_id" }`, `{ "codigo_fipe" }` ou `{ "limpar": true }`). 200: a representação. Perfis e erros como acima.

### GET /api/veiculos/modelos/ com os ids

Cada linha passa a trazer `marca_id` e `modelo_id` (os ids da Parallelum, ADR 0038, item 4), ou `null` nas linhas da lista própria da equipe ("CG 160 Fan", sem versão FIPE):

```json
{ "resultados": [ { "marca": "HONDA", "modelo": "CG 160 FAN ESDi FLEXONE", "tipo": "moto", "marca_id": 80, "modelo_id": 7329 } ] }
```

A tela guarda os dois ids com a escolha e manda no bloco `fipe`. Linha com ids `null` não serve para `fipe` (só preenche marca e modelo, como hoje).

### Colocar à venda

`colocar-a-venda` continua com `{ valor_venda_centavos, referencia_fipe_centavos? }`. Com `referencia_fipe.situacao` `ok`, `referencia_fipe_centavos` mandado é ignorado (sem erro): vale o da rotina, e o 200 traz o valor que vale, para a tela não mostrar o digitado. Nos outros casos, grava com `origem` `manual`, como hoje.

### Consulta por placa (desligada por padrão)

`GET /api/veiculos/consulta-placa/` → `{ "ativa": false }`. Com `GIRO_FIPE_PLACA_ATIVA=true`: `{ "ativa": true, "restantes_hoje": 3 }` (o limite da empresa, `comum.limites`). A tela do cadastro mostra "Buscar pela placa" só com `ativa` `true`.

`POST /api/veiculos/consulta-placa/` · administrador e gerente · corpo `{ "placa": "QXA4B21" }`. Sem hífen e em maiúsculas, tem de casar `^[A-Z]{3}\d[A-Z0-9]\d{2}$` (ADR 0038, item 9.1); fora dele, 400 `validacao`. Não grava nada.
- Ordem (B-05 da segurança): perfil primeiro (403 para os outros perfis e para o suporte Giro, que não gasta a cota), depois o formato, depois o limite de 3 por dia da empresa, e só então a chamada. Um 403 ou um 400 não gastam o limite.
- 200 com resultado:
  ```json
  { "disponivel": true, "marca": "HONDA", "modelo": "CG 160 FAN", "ano_modelo": 2023, "combustivel": "flex",
    "versoes": [ { "codigo_fipe": "811134-0", "versao": "CG 160 FAN ESDi FLEXONE", "ano": "2023 Flex",
                   "valor_centavos": 1450000, "mes": "2026-11" } ] }
  ```
  A tela preenche marca, modelo, ano e combustível marcados como "lido pela placa", editáveis, como a leitura do CRLV-e (`VEI-08`), e a pessoa escolhe a versão, que vai no bloco `fipe` como `codigo_fipe`. O valor só aparece para conferência; quem grava a referência é a rotina.
- 200 `{ "disponivel": false, "mensagem": "A busca pela placa não está disponível agora. Preencha pelo CRLV-e ou escolha a versão na lista FIPE." }` em todos os outros casos: recurso desligado, cota global esgotada (`X-Plate-Quota-Remaining`, marcada no cache do `public`, igual para todas as empresas, item 9.3), limite da empresa no dia, placa não achada, API fora do ar ou resposta fora do formato. A resposta é a mesma em todos e não diz o motivo (texto do produto, PR #481). A tela mostra a `mensagem` em tom de informação, sem erro, e segue pelo CRLV-e e pela escolha da versão (decisão do dono de 29 out 2026).
- Da resposta da Parallelum, só marca, modelo, ano, combustível e as versões com código FIPE, ano, valor e mês chegam à tela; qualquer outro campo (chassi, município, cor) é descartado.
- A placa vai para a Parallelum e não fica guardada em lugar nenhum do Giro além do veículo que a pessoa salvar; o log e o Sentry não levam a placa.

### Interface interna e tarefas

| Item | Uso |
| --- | --- |
| `integracoes.fipe.provedor()` | `falso` ou `parallelum` (`GIRO_PROVEDOR_FIPE`); `referencias`, `anos_do_modelo`, `anos_do_codigo`, `preco`, `placa`. Só a rotina e a consulta por placa chamam. Valida os formatos antes da URL e a resposta (até 256 KB, só JSON, preço pelo formato e com teto, código e mês iguais ao pedido, textos e listas limitados; ADR 0038, itens 9.1 e 9.2). |
| `integracoes.fipe.cache_publico` | a trava da rotina e a marca de cota esgotada da placa, sempre no `public` (item 9.3). |
| `veiculos.services.casar_fipe(veiculo)` | casamento local pelo catálogo (ADR 0038, item 5); chamado pela rotina nos `sem_versao`. |
| `veiculos.selectors.pendencias_fipe(referencia_mes)` | só chaves: `(tipo, codigo_fipe, ano_codigo)` a precificar e `(tipo, marca_id, modelo_id)` ou `(tipo, codigo_fipe)` a buscar anos; nenhum dado da empresa. |
| `veiculos.services.aplicar_referencias_fipe(referencia_mes)` | grava, do `PrecoFipe`, valor, mês, versão e código; resolve o ano pelo `AnosFipe` (ano do modelo e combustível); passa a `ok`, `escolher_versao` ou `nao_encontrado`. Sem pedido à API. |
| `plataforma.services.guardar_preco_fipe`, `guardar_anos_fipe`, `abrir_rodada_fipe`, `registrar_pedidos_fipe`, `parar_rodada_fipe`; `plataforma.selectors.preco_fipe`, `anos_fipe`, `rodada_fipe` | as tabelas do `public` (ADR 0038, item 2). |
| tarefa `fipe_rodada_do_dia` (Beat, 04:30, no `public`) | os passos 1 a 4 e 6 do item 6 da ADR; trava pelo cache. |
| tarefa `fipe_aplicar_referencias` (por empresa, `tarefa_de_empresa`) | o passo 5, chamada por `para_cada_empresa` no fim da rodada do dia. |
| configurações | `GIRO_PROVEDOR_FIPE` (`falso`), `GIRO_FIPE_URL_BASE` (`https://fipe.parallelum.com.br/api/v2`), `GIRO_FIPE_TOKEN` (vazio; só pelo cofre), `GIRO_FIPE_PEDIDOS_POR_DIA` (400), `GIRO_FIPE_PLACA_ATIVA` (`false`). |

### Seed e testes

- O seed não ganha código FIPE: os 86 veículos ficam `sem_versao`, e com `GIRO_PROVEDOR_FIPE=falso` a primeira rodada casa pelo catálogo e precifica pelo provedor falso. O provedor falso responde as referências "outubro/2026" e "novembro/2026" e os preços dos modelos do seed, com números fictícios fixos, para os testes; não muda nenhum número das regras.
- Testes `test_ven_01_*` e `test_vei_08_*` com o provedor falso e com respostas gravadas da Parallelum (sem chamada real no CI): parada no 429 e retomada no dia seguinte, orçamento do dia, um pedido por código e ano com dois veículos de empresas diferentes, último valor quando a API cai, casamento com uma, várias e nenhuma versão, consulta por placa com cota esgotada.

---

## Preços do veículo (`VEI-12` a `VEI-17`, T-494, ADR 0041)

Telas `Veiculo-Precos-Desktop` (`/veiculos/[id]/precos`) e o componente "Preços desta moto" da ficha (`Veiculo-Componente-PrecosDaMoto`). O preço é de cada veículo: planos de aluguel, regras, custos e a locação com compra. A API calcula tudo (margem, parcela, juros, alertas); a tela só mostra e chama o `simular` a cada mudança, com debounce. A locação ainda lê a tabela da categoria até a T-495 (ADR 0041, tarefa 2).

### Quem pode

- `GET`: administrador, gerente, vendedor e financeiro, no veículo das suas filiais (fora delas, 404). O vistoriador recebe 403 (não vê dinheiro, `USR-09`). O suporte Giro lê nos dois modos ("só ver" e "ver e editar"); a rota está na lista do `PLT-07`.
- `PUT`, `simular` e o liga e desliga: só o administrador. O gerente recebe 403 (padrão A de "quem edita"). O suporte Giro só vê (`VEI-12`): recebe 403 `PLT-07` mesmo com "ver e editar" (`suporte_proibido`).
- `custos`, `pago_na_moto`, `planos[].margem` e o lucro e a margem da compra só saem para administrador, gerente e financeiro; para o vendedor, as chaves vêm **ausentes**, não `null` (`VEI-13`, `USR-09`).

### GET /api/veiculos/{id}/precos/

```json
{
  "veiculo": { "id": 900, "placa": "TBC5H21", "marca": "Honda", "modelo": "Pop 110i", "status": "disponivel" },
  "valor_venda_centavos": 1590000,
  "aluguel_ligado": true,
  "aviso_aluguel": null,
  "fipe_centavos": 1390000,
  "ocupacao_real_90d_pct": "84.00",
  "margem_minima_pct": null,
  "pago_na_moto": { "total_centavos": 1380000, "compra_centavos": 1349000, "despesas_centavos": 31000 },
  "custos": {
    "manutencao_mes_centavos": 10000, "seguro_mes_centavos": 8000, "rastreador_mes_centavos": 5000,
    "ipva_ano_centavos": 120000, "ipva_mes_centavos": 10000, "revenda_estimada_centavos": 900000,
    "ocupacao_esperada_pct": "85.00", "custo_mes_centavos": 53000,
    "sem_custo_compra": false, "revenda_acima_do_pago": false
  },
  "planos": [
    {
      "id": 31, "tipo": "semanal", "nome": null, "rotulo": "Semanal", "periodo": "semana", "ligado": true,
      "valor_centavos": 32900, "como_paga": "semana_adiantado", "formas_aceitas": ["pix", "boleto", "cartao", "dinheiro"],
      "caucao_centavos": 30000, "caucao_parcelas": 1, "caucao_parcelada": null, "franquia_km": 1000, "prazo_minimo_periodos": null,
      "agendado": { "valor_centavos": 34900, "caucao_centavos": null, "a_partir_de": "2026-12-01" },
      "parcela_do_mes": null,
      "margem": { "receita_mes_centavos": 121182, "lucro_mes_centavos": 68182, "margem_pct": "56.26", "abaixo_da_minima": false, "sem_custo_compra": false }
    },
    { "id": null, "tipo": "entregador", "nome": null, "rotulo": "Entregador", "periodo": null, "ligado": false, "valor_centavos": 0, "...": "..." }
  ],
  "regras": {
    "km_excedente_centavos": 35, "dia_atraso_centavos": 5500, "multa_minima_centavos": 5490,
    "desconto_sem_aprovacao_pct": "10.00", "prazo_devolucao_caucao_dias": 3
  },
  "plano_compra": {
    "ligado": true, "periodicidade": "semanal", "parcelas": 104, "entrada_centavos": 100000, "juros_mes_pct": "1.00",
    "modo": "calcular", "parcela_moto_centavos": 16124, "adicional_centavos": 2977, "caucao_centavos": 30000,
    "resultado": {
      "financiado_centavos": 1490000, "meses_do_prazo": "24.00", "taxa_periodo_pct": "0.23", "juros_mes_pct": "1.00",
      "parcela_moto_centavos": 16124, "adicional_centavos": 2977, "parcela_cliente_centavos": 19101,
      "recebe_pela_moto_centavos": 1776896, "juros_no_prazo_centavos": 186896, "venda_abaixo_do_pago": false,
      "lucro_centavos": 396896, "margem_sobre_pago_pct": "28.76",
      "pago_sobre_recebe_pct": "77.66", "lucro_sobre_recebe_pct": "22.34", "sem_custo_compra": false,
      "nas_periodicidades": [
        { "periodicidade": "diaria", "parcelas": 730, "parcela_cliente_centavos": 2719 },
        { "periodicidade": "semanal", "parcelas": 104, "parcela_cliente_centavos": 19101 },
        { "periodicidade": "quinzenal", "parcelas": 52, "parcela_cliente_centavos": 38239 },
        { "periodicidade": "mensal", "parcelas": 24, "parcela_cliente_centavos": 83039 }
      ]
    }
  },
  "alertas": [],
  "aviso_preco": null,
  "pede_confirmacao_juros": false,
  "pode_editar": true
}
```

- `planos`: sempre os quatro tipos fixos, nesta ordem (`diaria`, `semanal`, `mensal`, `entregador`), e depois os `outro` ativos. Tipo fixo que o veículo ainda não tem vem com `id` `null`, desligado e valor 0 ("Ligue para definir valor, prazo mínimo e caução").
- `valor_centavos` e `caucao_centavos` são os **efetivos de hoje**: com o preço agendado já na data, vêm os agendados e `agendado` vem `null`, mesmo antes da rotina das 00:05 (ADR 0041, risco 3). `agendado` só aparece enquanto a data é futura ("R$ 349,00 a partir de 01 dez").
- `periodo`: `dia`, `semana` ou `mes`. `como_paga`: `tudo_na_retirada` (dia), `semana_adiantado` (semana), `mes_uma_parcela`, `mes_duas_quinzenais` ou `mes_quatro_semanais` (mês). `parcela_do_mes` só no mês dividido: `{ "parcelas": 4, "parcela_centavos": 24750, "ultima_parcela_centavos": 24750 }` (a diferença de centavos vai para a última).
- `franquia_km` `null` = livre; `prazo_minimo_periodos` `null` = sem mínimo; `caucao_centavos` `null` = não preenchida (R$ 0,00 é válido).
- `caucao_parcelada` (`LOC-04`): a caução de hoje dividida em `caucao_parcelas`, no mesmo formato do `parcela_do_mes`, com a diferença de centavos na última: R$ 500,00 em 2 → `{ "parcelas": 2, "parcela_centavos": 25000, "ultima_parcela_centavos": 25000 }` ("2 × R$ 250,00"). `null` à vista (`caucao_parcelas` 1) ou sem caução preenchida.
- `custos.ipva_mes_centavos`: o IPVA do ano ÷ 12, arredondado ao centavo (`ROUND_HALF_UP`), só para mostrar ("R$ 39,00 por mês"); o custo por mês usa o valor sem arredondar.
- `plano_compra.resultado.pago_sobre_recebe_pct` e `lucro_sobre_recebe_pct`: a divisão da barra do "recebe pela moto", com 2 casas e somando 100,00 (o do lucro é 100 − o do pago). Pop: 77,66% e 22,34%. Com lucro negativo (venda abaixo do pago e juros que não cobrem), o do pago passa de 100 e o do lucro fica negativo. Só para administrador, gerente e financeiro; nulos sem valor de compra.
- `margem` `null` sem `ocupacao_esperada_pct` ("Informe a ocupação"). `margem_pct` `null` com receita zero. `abaixo_da_minima` pinta a faixa de amarelo (`margem_minima_pct` da empresa; nula = nunca).
- `pago_na_moto.total_centavos` = compra + despesas do veículo sem as recusadas (`FIN-17`); `null` sem valor de compra (aí `lucro_centavos` e `margem_sobre_pago_pct` também vêm `null`).
- **Desvalorização** (`VEI-13`, padrão A de 22 nov 2026, T-505): entra no `custo_mes_centavos` como max(0, pago na moto − revenda estimada) ÷ 24. Vazia (zero) sem revenda estimada, sem valor de compra ou com a revenda acima do pago; nunca negativa.
- `sem_custo_compra` (`VEI-13`, `VEI-16`): `true` quando o veículo não tem valor de compra. Vem em `custos`, em cada `planos[].margem` e em `plano_compra.resultado`, só para quem vê custo (ausente para o vendedor, como o resto). A margem continua calculada (sem a desvalorização), e a tela a marca "sem custo de compra" com a dica "A margem não conta a compra desta moto. Informe o valor de compra para ver a margem real."; `abaixo_da_minima` vem sempre `false` (sem a faixa amarela). Na compra, `lucro_centavos`, `margem_sobre_pago_pct` e a divisão da barra vêm `null`. Biz ADJ-4T71 (revenda R$ 9.000,00): custo R$ 330,00 por mês, e não −R$ 45,00; semanal R$ 299,40 a 85%, margem 70,08%.
- `custos.revenda_acima_do_pago`: `true` quando a revenda estimada passa do pago na moto; a desvalorização fica em R$ 0,00, e a tela mostra a dica "A revenda passa do que foi pago: sem desvalorização no custo.".
- `plano_compra` `null` enquanto o veículo não tem um; `resultado` `null` sem valor de venda ou com entrada maior ou igual a ele. O "recebe pela moto" usa a parcela arredondada × `n` + entrada (padrão A: Pop R$ 17.768,96). A parcela nas 4 periodicidades usa o mesmo prazo em meses; a parcela da moto e o adicional se arredondam cada um.
- `alertas`: `{ "codigo": "venda_abaixo_do_pago", "mensagem": "Valor de venda abaixo do que foi pago: o lucro vem só dos juros." }` e, com juros acima de 1% ao mês, `{ "codigo": "VEI-16", "mensagem": "Locadora não é financeira: juros acima de 1% ao mês (12% ao ano) pedem confirmação. Valide o contrato com seu advogado." }`.
- `aviso_preco`: o mesmo da representação do veículo, calculado sobre o documento mostrado.
- `aluguel_ligado` e `aviso_aluguel` (`VEI-21`): com o aluguel desligado, `aviso_aluguel` traz "O aluguel desta moto está desativado. O administrador ativa em Planos e preços." ("deste carro" no carro, pelo tipo da categoria); ligado, `null`. A Nova locação mostra esse texto no lugar dos planos de aluguel.
- `pode_editar`: `true` só para o administrador; `false` para o suporte Giro, nos dois modos.

### PUT /api/veiculos/{id}/precos/

Corpo com o documento da tela; bloco ausente fica como está, e campo ausente dentro de um plano também. Devolve o mesmo corpo do `GET`. `aluguel_ligado` (`VEI-21`, opcional) liga e desliga o aluguel inteiro: o "Oferecer aluguel" manda só `{ "aluguel_ligado": false }` (ou `true`).

```json
{
  "valor_venda_centavos": 1590000,
  "custos": { "manutencao_mes_centavos": 10000, "seguro_mes_centavos": 8000, "rastreador_mes_centavos": 5000,
              "ipva_ano_centavos": 120000, "revenda_estimada_centavos": 900000, "ocupacao_esperada_pct": "85.00" },
  "planos": [
    { "id": 31, "valor_centavos": 32900, "ligado": true, "franquia_km": 1000,
      "agendado": { "valor_centavos": 34900, "caucao_centavos": null, "a_partir_de": "2026-12-01" } },
    { "tipo": "entregador", "periodo": "semana", "ligado": true, "valor_centavos": 27900, "formas_aceitas": ["pix"],
      "caucao_centavos": 0, "caucao_parcelas": 3, "prazo_minimo_periodos": 12 },
    { "id": null, "tipo": "outro", "nome": "Fim de semana", "periodo": "dia", "valor_centavos": 9900 },
    { "id": 44, "ativo": false }
  ],
  "regras": { "km_excedente_centavos": 35, "dia_atraso_centavos": 5500, "multa_minima_centavos": 5490,
              "desconto_sem_aprovacao_pct": "10.00", "prazo_devolucao_caucao_dias": 3 },
  "plano_compra": { "ligado": true, "periodicidade": "semanal", "parcelas": 104, "entrada_centavos": 100000,
                    "juros_mes_pct": "1.00", "modo": "calcular", "parcela_moto_centavos": 0,
                    "adicional_centavos": 2977, "caucao_centavos": 30000 },
  "confirmar_juros": false
}
```

- O plano se acha pelo `id`, ou pelo `tipo` nos tipos fixos sem `id` (cria o que ainda não existe). `outro` com `id` `null` cria um novo; precisa de `nome` (até 40), único entre os `outro` ativos sem diferenciar maiúsculas. `entregador` e `outro` precisam de `periodo`.
- `ativo: false` retira só o `outro` (fica `ativo=false`, nada se apaga); nos tipos fixos responde 400 "Este plano não se retira. Desligue o plano.".
- `agendado: null` desfaz o agendado; um objeto troca o anterior. `a_partir_de` a partir de amanhã (data sem hora, `America/Sao_Paulo`).
- `plano_compra`: `periodicidade` (`diaria`, `semanal`, `quinzenal`, `mensal`), `parcelas` de 2 a 1000. No `calcular`, a API calcula a parcela pelos juros e ignora `parcela_moto_centavos`; no `digitar`, grava a parcela digitada e acha os juros por bisseção, gravados com 2 casas.
- 400 `validacao`, com os campos pontuados (`planos.0.valor_centavos`, `plano_compra.entrada_centavos`):

| Campo | Mensagem |
| --- | --- |
| `planos.N.valor_centavos` | Informe um valor maior que zero para ligar o plano. |
| `planos.N.formas_aceitas` | Escolha ao menos uma forma de pagamento para ligar o plano. |
| `planos.N.caucao_centavos` | Informe a caução para ligar o plano. Pode ser R$ 0,00. |
| `planos.N.como_paga` | Escolha como o cliente paga neste período. |
| `planos.N.nome` | Dê um nome ao plano. |
| `planos.N.agendado.a_partir_de` | Escolha uma data a partir de amanhã. |
| `valor_venda_centavos` | Informe o valor de venda para ligar a locação com compra. |
| `plano_compra.entrada_centavos` | A entrada precisa ser menor que o valor de venda. |
| `plano_compra.parcela_moto_centavos` | A parcela não cobre o valor de venda. |

- 409 `VEI-16` quando a compra fica ligada com juros acima de 1,00% ao mês (o digitado no `calcular`, o achado no `digitar`), mudados desde a última gravação ou com a compra ligada agora, sem `confirmar_juros: true`:
  `{ "codigo": "VEI-16", "mensagem": "Locadora não é financeira: juros acima de 1% ao mês (12% ao ano) pedem confirmação. Valide o contrato com seu advogado.", "detalhes": { "juros_mes_pct": "1.46" } }`. A tela confirma e reenvia com `confirmar_juros: true`; o evento de auditoria grava `juros_confirmados: { pct, por, em }`.
- A gravação é uma transação com o veículo travado. Cada campo mudado vira uma linha do histórico de preços (`VEI-17`, origem `tela_precos`), e a gravação inteira um evento de auditoria `veiculo.precos_salvar` ("Mudou os preços do veículo TBC-5H21"), com o `lote`.
- Depois de gravar, o "sem preço" se alinha (abaixo).

### POST /api/veiculos/{id}/precos/simular/

O mesmo corpo do `PUT` (o `confirmar_juros` é ignorado), sem gravar nada (ADR 0005). Devolve o corpo do `GET` com o documento simulado e `pede_confirmacao_juros` `true` quando salvar pediria a confirmação. Os mesmos 400.

### POST /api/veiculos/{id}/precos/planos/{plano_id}/ligado/

`{ "ligado": false }`: o liga e desliga do cartão da ficha, com confirmação na tela. Mesmo histórico (origem `ficha`), auditoria e "sem preço" do `PUT`. Ligar sem valor, forma ou caução: 400 com `valor_centavos`, `formas_aceitas` ou `caucao_centavos`. Plano de outro veículo ou retirado: 404. Devolve o corpo do `GET`.

### Sem preço (`VEI-15`)

- O veículo `disponivel` que fica sem nenhum plano ligado (nem a compra) vai para `indisponivel` com `motivo_status` "Sem preço · ligue um plano", na mesma gravação. Ligar um plano o devolve a `disponivel`, desde que o motivo seja esse e nenhum CRLV ou seguro tenha vencido; bloqueio ou documento vencido não voltam sozinhos.
- `reservado`, `alugado`, `em_manutencao` e `em_movimentacao` mantêm o status. Na volta (`transicionar(..., "disponivel")`: devolução, reserva cancelada, fim de OS, chegada da movimentação), o veículo sem plano ligado vai para `indisponivel` "sem preço" (`acao` `veiculo.sem_preco`).
- Vale em todo retorno (PR #630), inclusive o desbloqueio e o "Voltar para a frota":
  - **`desbloquear` sem plano ligado:** responde 200 com o veículo `indisponivel` e `motivo_status` "Sem preço · ligue um plano". O bloqueio sai e o motivo dele deixa de aparecer. O histórico de status ganha uma linha de `indisponivel` para `indisponivel` com o motivo novo, e a auditoria um evento `veiculo.sem_preco`. CRLV ou seguro vencido continua respondendo 422 `VEI-03` antes disso.
  - **`voltar-para-frota` sem plano ligado:** `a_venda` vai para `indisponivel` "sem preço".
  - **As idas a `indisponivel` a partir de `alugado`, `reservado`, `em_manutencao` e `a_venda`** existem só por essa volta. Bloquear um veículo nesses status continua 409 `transicao_veiculo`.
- "Colocar à venda" sem plano ligado: 409 `{ "codigo": "VEI-15", "mensagem": "A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda." }` (`VEN-01`).

### Aluguel desligado (`VEI-21`, T-507)

- `PUT .../precos/` com `aluguel_ligado`: só o administrador (o gerente recebe 403; o suporte Giro, 403 `PLT-07`), como os preços. Grava `Veiculo.aluguel_ligado` e uma linha de histórico (`alvo` `aluguel`, `campo` `aluguel_ligado`, `de` e `para`) no evento `veiculo.precos_salvar` (`VEI-17`). O mesmo valor de novo não grava nada.
- Os planos ficam como estão, com o ligado de cada um, o valor, o agendado e o histórico, e continuam editáveis. O agendado que chega à data entra em vigor do mesmo jeito.
- **Status (padrão A, decisão do dono de 24 nov 2026):** não muda e não é "sem preço". A `VEI-15` continua olhando o ligado de cada plano, e o `aviso_preco` também.
- **Nova locação de aluguel e troca de veículo (`LOC-09`):** 409 `{ "codigo": "VEI-21", "mensagem": "O aluguel desta moto está desativado. O administrador ativa em Planos e preços." }` no `simular`, no rascunho e no pedido de troca (`veiculos.services.conferir_aluguel_ligado`).
- **Locação com compra (padrão A):** independente; com a compra ligada, o veículo segue na Nova locação só para ela.
- **Locação aberta:** desligar é aceito, e a locação segue com o preço e as renovações dela (`LOC-15`); a renovação não confere o aluguel.
- Veículo novo, importado ou migrado começa com o aluguel ligado (migration `veiculos 0012`, `default` `true`).

### Preço agendado

Um por plano. Quem lê o preço pergunta pelo dia: o agendado vale a partir de `a_partir_de`. A rotina `consolidar_precos_agendados` (Celery Beat, 00:05, uma por empresa, idempotente) passa o agendado vencido a vigente e limpa os campos, com histórico (origem `agendamento`, sem pessoa) e o evento `veiculo.precos_agendado_vigente` do Sistema. O plano que nasceu sem preço na migração e só com o agendado liga no dia, se tiver forma e caução.

### Veículo novo e migração

- O veículo cadastrado (tela, CRLV, importação, troca) nasce com `diaria`, `semanal` e `mensal` pelo preço vigente da categoria (`veiculos.services.aplicar_modelo_de_preco`), ligados quando há valor e caução; o primeiro preço futuro da categoria vira o agendado; regras com dia de atraso e multa mínima iguais à diária e 5% sem aprovação.
- A migration `veiculos 0010` faz o mesmo para os veículos que já existem (origem `migracao`), uma vez por veículo (sem `RegrasVeiculo`); um segundo preço futuro da categoria não cabe e sai listado no `migrate`.

### Interface interna

| Item | Uso |
| --- | --- |
| `veiculos.services.tem_plano_ligado(veiculo)` | algum plano ativo e ligado, ou a compra ligada |
| `veiculos.services.sem_preco()` | o `Conflito` 409 `VEI-15` com o aviso, para a Nova locação e a troca (T-495) |
| `veiculos.services.conferir_aluguel_ligado(veiculo)` | 409 `VEI-21` com o aluguel desligado, para a Nova locação de aluguel e a troca (T-507) |
| `veiculos.services.MOTIVO_SEM_PRECO`, `AVISO_PRECO` | os textos |
| `PlanoVeiculo.valor_em(dia)`, `caucao_em(dia)` | o preço do dia, com o agendado |
| `veiculos.precos` | o cálculo puro (`simular`, `simular_compra`, `pmt`, `juros_por_bissecao`, `margem`) |
| `financeiro` registra o contador `("veiculos.Veiculo", "despesas_centavos")` | as despesas do veículo sem as recusadas, para o "pago na moto" (ADR 0015) |

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
| tarefa `aut_18_veiculos_parados` (Beat às 07:00) | `VEI-19`, `AUT-18`: avisa os gerentes ativos da filial (`FIL-02`) de cada veículo `a_venda` com `dias_em_estoque` acima do limite, uma vez por entrada no estoque (`Veiculo.estoque_aviso_entrada_em`), no sino e por e-mail: "O veículo PVF-2B18 (Honda CG 160 Fan) está à venda há 31 dias. O limite da empresa é 30 dias.", com o link da ficha. Administradores não recebem; filial sem gerente ativo fica sem o aviso. Execução perdida e limite que baixou avisam na próxima execução. |
| `veiculos.selectors.estoque_a_venda(filiais)`, `parados_a_venda(filiais, limite, hoje)` | `VEI-20` e `VEI-18` para o painel (`painel.md`). |
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
  "dicas": { "marca_modelo": null, "candidatos": [], "escolhido": null },
  "leitura": "<comprovante assinado>" }
```
- `campos` traz só os 9 da `VEI-08`. Campo não lido vem `null` e fica fora de `lidos`. `quantidade` é o tamanho de `lidos`, e a tela usa o `rotulo` como vem ("1 campo preenchido", no singular). Nunca vêm o nome, o CPF ou o CNPJ do proprietário, nem campo fora da lista (CA-247-02).
- **Marca e modelo sempre preenchidos (T-521, decisão do dono em 26 nov 2026; antes, sem um modelo único, os dois vinham `null`):** quando o documento traz o texto de marca e modelo, `campos.marca` e `campos.modelo` sempre vêm preenchidos e entram em `lidos` e na `quantidade`. Quem escolhe é a API; a tela só mostra.
- **Uma versão do catálogo bate:** marca e modelo dela; `dicas` vem `{ "marca_modelo": null, "candidatos": [], "escolhido": null }`.
- **Várias versões batem (T-415, T-521):** `campos.marca` e `campos.modelo` vêm da versão mais parecida com o texto lido (semelhança entre o modelo do texto e o do catálogo; no empate, a primeira em ordem de marca e modelo), e ela vem também em `dicas.escolhido`. `dicas.marca_modelo` traz o texto lido, e `dicas.candidatos` traz as versões que batem, no formato da lista de modelos (`{ "marca", "modelo", "tipo" }`), da mais parecida à menos parecida, com a escolhida na frente, para a pessoa trocar; trocar não muda a `quantidade`. Palavras do documento que não existem em nenhuma versão são ignoradas: "CHEVROLET/CRUZE LT NB" (CRLV-e real do Detran-CE) preenche "GM - Chevrolet" e "CRUZE LT 1.4 16V Turbo Flex 4p Aut.", com "CRUZE LT 1.8 16V FlexPower 4p Aut." e "CRUZE LT 1.8 16V FlexPower 4p Mec." depois (CA-521-01: 16 campos). Acima de 20 versões, `candidatos` traz as 20 mais parecidas, e a pessoa busca as outras na lista de modelos.
- **Nenhuma versão bate (CA-247-05, CA-521-02):** marca e modelo saem do texto, separados pela barra (o "I/" do importado sai); a marca usa o nome do catálogo quando ela está nele, pelo nome ou pelo apelido do Detran. "SUZUKI/YES 125" preenche marca "Suzuki" e modelo "YES 125"; uma marca fora do catálogo fica como lida. `dicas` vem com `marca_modelo` (o texto), `candidatos` `[]` e `escolhido` `null`.
- `campos` traz só os campos da `VEI-08` (os 9 abaixo e, desde a T-421, os 9 da `VEI-09`, mais abaixo). Campo não lido vem `null` e fica fora de `lidos`. `quantidade` é o tamanho de `lidos`, e a tela usa o `rotulo` como vem ("1 campo preenchido", no singular). Nunca vêm o nome, o CPF ou o CNPJ do proprietário, nem campo fora da lista (CA-247-02).
- `cor` vem no texto do cadastro, em minúsculas ("vermelha"). `combustivel` vem no enum: `ALCOOL/GASOLINA` vira `flex`, e um valor fora do enum fica fora de `lidos`.
- `exercicio`: o ano do licenciamento, para o documento CRLV; não conta nos 9. A validade do CRLV não vem (`VEI-08`): a pessoa informa.
- **Campos da `VEI-09`** (T-421; a `VEI-08` passa a ler até 18): `campos` ganha as chaves pontuadas `documento.potencia_cv`, `documento.cilindrada_cc`, `documento.especie`, `documento.tipo`, `documento.carroceria`, `documento.lotacao`, `documento.peso_bruto_kg`, `documento.numero_motor` e `documento.observacoes`, no formato do corpo do cadastro, e elas entram em `lidos` e na `quantidade` como as outras. Com o `crlv-tbc5h21.pdf` (CA-421-01): os 9 de antes mais potência 8, cilindrada 109, `passageiro`, "Motocicleta", lotação 2, peso 240 e motor `JC75E1S123456`, `quantidade` 16, `rotulo` "CRLV-e lido · 16 campos preenchidos"; carroceria e observações `null`, fora de `lidos`. A leitura nunca traz `rastreador` nem `anotacoes`, e a tela não mexe neles (CA-421-04). As chaves de `dicas` da T-415 (`dicas.candidatos`) não mudam; a T-521 acrescenta `dicas.escolhido`.
- **Do texto do CRLV-e ao campo** (`integracoes/leitura_documentos/crlv.py`, um validador por campo na lista `CAMPOS`, como os de hoje; o que não passa fica `null` e fora da conta, `VEI-09`):

  | Rótulo no CRLV-e | Campo | Conversão |
  | --- | --- | --- |
  | POTÊNCIA/CILINDRADA | `potencia_cv` e `cilindrada_cc` | "15CV/0162" → 15 e 162. Potência 0 → `null`. Cilindrada 0 (elétrico) → `null`. Fora da faixa → `null` |
  | ESPÉCIE / TIPO | `especie` e `tipo` | 1ª palavra no enum, sem acento ("PASSAGEIRO" → `passageiro`, "COMPETICAO" → `competicao`); o resto vira o `tipo`, pela tabela dos tipos do CTB com acento e só a 1ª maiúscula ("MOTOCICLETA" → "Motocicleta", "AUTOMOVEL" → "Automóvel", "CAMINHONETE" → "Caminhonete", "MICRO-ONIBUS" → "Micro-ônibus", "UTILITARIO" → "Utilitário"); tipo fora da tabela, só a 1ª maiúscula. Espécie fora do enum: os dois `null` |
  | CARROCERIA | `carroceria` | "NÃO APLICAVEL", "NAO APLICAVEL" ou só asteriscos → `null`; senão o texto como vem, até 30 |
  | LOTAÇÃO | `lotacao` | "02P" → 2; fora de 1 a 99 → `null` |
  | PESO BRUTO TOTAL | `peso_bruto_kg` | toneladas com vírgula ou ponto: "0,29" → 290, "1,40" → 1400 (× 1000, arredondado); zero → `null` |
  | MOTOR | `numero_motor` | maiúsculas, sem espaços nem asteriscos, até 21 letras e números |
  | OBSERVAÇÕES DO VEÍCULO | `observacoes` | as linhas do bloco até o próximo rótulo, com as quebras, até 500; só asteriscos ou vazio → `null` |

  Não são lidos (`VEI-08`): categoria do documento, capacidade, CMT, eixos, CRV, código de segurança, DPVAT, proprietário (CA-421-04). O parser não tem rótulo para eles, e o teste confere que nenhuma chave fora da lista aparece.
- O comprovante `leitura` passa a listar também os campos da `VEI-09` lidos, e o `preenchido_pelo_documento` do evento usa as chaves pontuadas (`"campos": [..., "documento.lotacao"], "corrigidos": ["documento.lotacao"]`, CA-421-05).
- Testes com o código: `test_vei_08_le_os_campos_da_vei_09` (CA-421-01 a 03, com os três PDFs), `test_vei_08_nao_le_o_que_nao_e_da_lista` (CA-421-04) e `test_vei_08_corrigidos_com_campos_novos` (CA-421-05). O `test_vei_08_le_os_9_campos` (T-265, CA-247-01) passa a esperar 16 com o mesmo arquivo.
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

### POST /api/veiculos/{id}/leitura-crlv/ (ler o CRLV-e no editar, T-421)

Padrão A do ponto em aberto "Ler o CRLV-e no editar do veículo" (regras, T-421), valendo até a resposta do dono. Para a frota já cadastrada ganhar os campos da `VEI-09` sem digitar (CA-421-10).

- Mesma leitura, mesmos perfis, mesmo arquivo, mesmos limites (os 30 por hora e 200 por empresa somam com a do cadastro e a da CNH-e), as mesmas 400, 422 `VEI-08`, 429 e 503 de `POST /api/veiculos/leitura-crlv/`. O veículo tem de estar nas filiais da pessoa (404 fora delas, como o `GET`).
- **Confere que o documento é deste veículo:** a placa e o chassi lidos são comparados com os do cadastro (sem hífen, maiúsculas). Precisa ter lido pelo menos um dos dois, e todo o que foi lido tem de ser igual. Diferente: 422 `{ "codigo": "crlv_outro_veiculo", "mensagem": "Este CRLV-e é de outro veículo." }`, sem nenhum campo na resposta (CA-421-10). Sem placa e sem chassi lidos: a 422 `VEI-08` de sempre ("Não conseguimos ler este documento..."), porque não dá para conferir.
- **200** no formato da leitura do cadastro, com duas diferenças: `placa` e `chassi` não vêm em `campos` nem em `lidos` e não contam na `quantidade` (no editar eles não mudam; corrigir é `corrigir-identificacao/`); e o comprovante `leitura` leva o `id` do veículo. `marca`, `modelo` e os outros vêm como no cadastro, inclusive as `dicas` da T-415. Com o `crlv-pnb7c04.pdf` no PNB-7C04: renavam, marca, modelo, anos, cor, combustível e os campos da `VEI-09` que o documento traz.
- **Nada é gravado na leitura.** A tela troca os campos lidos e os marca "lido do documento"; só o `PATCH` grava. O `PATCH` continua JSON e **não recebe o PDF**: o documento CRLV do veículo não é substituído pela leitura (substituir é a seção Documentos, `POST .../documentos/`, T-413).
- **Comprovante no `PATCH`:** `leitura?` no corpo. Válido (assinatura, até 30 minutos, mesma empresa, mesmo usuário e o mesmo veículo do `id` da rota), o `veiculo.editar` leva `preenchido_pelo_documento: { "tipo": "crlv", "campos": [...], "corrigidos": [...] }`, como no cadastro. No editar não há o SHA-256 do arquivo para conferir, porque o arquivo não vem; o comprovante amarra o veículo e a pessoa. Inválido ou ausente: salva do mesmo jeito, sem a marca (ADR 0026, item 8).
- Testes com o código: `test_vei_08_leitura_no_editar` (CA-421-10, o PNB-7C04 com o próprio CRLV-e, placa e chassi fora da resposta, nada gravado), `test_vei_08_leitura_no_editar_outro_veiculo` (CA-421-10, `crlv-tbc5h21.pdf` → 422 `crlv_outro_veiculo`) e `test_vei_08_editar_com_comprovante` (o evento com `preenchido_pelo_documento`; comprovante de outro veículo, sem a marca).

### GET /api/veiculos/modelos/ (catálogo, T-257)
É a lista "Da lista FIPE" da tela, local e sem consulta externa. Perfis: todos (quem vê veículos, `pode.veiculos` ≠ `nao`); o suporte em "só ver" também. Query `?tipo=moto|carro`, `?marca=` (igual, sem diferenciar maiúsculas e acento), `?busca=` (cada palavra em marca e modelo) → `{ "resultados": [ { "marca": "Honda", "modelo": "Pop 110i ES", "tipo": "moto", "marca_id": null, "modelo_id": null } ] }` (os ids da Parallelum desde a T-422, "Referência FIPE", abaixo), até 50, em ordem de marca e modelo. `tipo` fora da lista: 400 `validacao`. A `marca` e cada palavra da `busca` valem também pelos apelidos do Detran (`catalogo.APELIDOS_DO_DETRAN`, T-415): `?marca=Chevrolet` traz "Chevrolet" e "GM - Chevrolet", `?marca=VW` traz "VW - VolksWagen" e "Volkswagen", e `?busca=chevrolet cruze` acha as versões de "GM - Chevrolet".
O catálogo é o arquivo versionado `backend/apps/veiculos/dados/catalogo_modelos.csv`, igual para todas as empresas, atualizado por PR com `python manage.py atualizar_catalogo_modelos <arquivo>` (a tabela FIPE baixada pela equipe, em CSV com `marca`, `modelo` e `tipo`). A leitura do CRLV-e usa `veiculos.catalogo.candidatos(texto)`: os modelos cujo `marca + modelo` é igual ao texto normalizado, ou começa com ele (ou é o começo dele); sem nenhum, o começo mais longo do texto que ainda começa algum modelo, com as palavras que sobram filtrando as versões e as que não existem nelas ignoradas (T-415). Só a marca não basta. `achar_modelo(texto)` é o candidato quando ele é único. Sem candidato, `separar(texto)` divide o texto em marca e modelo (T-521).
Catálogo completo (T-337): a fonte está em decisão do dono (backlog, "Levantada pelo arquiteto em T-337"). A rota, o formato do CSV e o comando não mudam. Com milhares de linhas, a tela busca pela rota (`tipo` e `busca`, até 50) e nunca carrega a lista inteira. Na FIPE, o carro tem uma linha por versão ("ARGO DRIVE 1.3 8V Flex" e "... Flex Aut."), então o texto do CRLV-e de carro ("FIAT/ARGO DRIVE 1.3") costuma achar mais de um modelo: a leitura preenche o mais parecido (`catalogo.por_semelhanca`) e manda os outros em `dicas.candidatos` (T-521).

### O que muda para as tarefas (T-247)
- **Backend (sem número):**
  - a dependência `pypdf`, com o motivo no PR;
  - `integracoes/leitura_documentos/`: o processo filho, o parser do CRLV-e e os limites;
  - a rota de leitura e o `POST` em multipart com o documento;
  - `Veiculo.combustivel` e `DocumentoVeiculo.exercicio` (`modelo-de-dados.md`);
  - testes `test_vei_08_le_os_9_campos` (CA-247-01), `test_vei_08_nao_le_o_proprietario` (CA-247-02), `test_vei_08_salva_com_o_documento` (CA-247-03), `test_vei_08_validacoes_de_sempre` (CA-247-04), `test_vei_08_modelo_fora_da_lista` (CA-247-05), `test_vei_08_nao_da_para_ler` (CA-247-06), `test_vei_08_quem_pode` (CA-247-07) e os do processo filho da ADR 0026.
- **Frontend (sem número):** "Preencher pelo documento" para quem tem `pode.veiculos = editar`; os campos marcados, o `rotulo` e as `dicas` como vierem; o arquivo e o `leitura` guardados até o salvar; a mensagem da 422 como vem.
- **Qa:** os arquivos de teste de `docs/qa/criterios/T-247.md`.

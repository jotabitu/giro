# Movimentações de veículos

**Dono:** arquiteto · **Versão:** 16 out 2026 (T-286) · **App:** `movimentacoes` (schema da empresa, ADR 0028) · **Regras:** MOV-01 a MOV-06, VEI-01 a VEI-04, VEI-06, FIN-05, FIN-06, APR-03, AUD-05, USR-07 · **ADRs:** 0011, 0015, 0028 · **Telas:** Movimentacoes (desktop e celular), Movimentacao-Nova (desktop e celular), Movimentacao-Chegada-Mobile · **Critérios:** `docs/qa/criterios/T-246.md` (CA-246-01 a 16)

Convenções gerais em `docs/api/README.md`. Modelo: itens 26 e 27 de `docs/decisoes/modelo-de-dados.md`. A despesa da parada está em `financeiro.md`; o status do veículo, a ficha e a Frota, em `veiculos.md`.

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver o quadro e as movimentações | sim | sim (suas filiais) | só as que leva | só as que leva | — |
| Criar, agendar, editar a agendada, iniciar e cancelar (`MOV-02`) | sim | sim (filial de saída) | — | — | — |
| Registrar chegada na parada e no destino | sim | sim (filial de saída) | se leva | se leva | — |
| Criar local de apoio (na parada) | sim | sim | — | — | — |
| Inativar e reativar local de apoio | sim | — | — | — | — |

- "Suas filiais" é a regra de escopo de sempre (`USR-07`): o gerente vê e mexe nas movimentações cuja filial de saída ou de destino é dele, e só cria e inicia as de veículo da filial dele. Um gerente só da Caucaia não cria movimentação de veículo da Centro: 403 `permissao` (CA-246-11).
- "Se leva": o usuário em `levado_por` daquela movimentação, qualquer perfil (`MOV-02`). O financeiro nunca leva: ele não aparece na escolha de quem leva, e a API recusa (400).
- Fora disso, 403 `{ "codigo": "permissao", "mensagem": "Seu perfil não tem acesso a esta ação." }`. Token de suporte (`PLT-07`): lê; escreve só com "ver e editar".

`GET /api/auth/eu/` ganha `pode.movimentacoes`: `gerir` (administrador e gerente), `levar` (vendedor e vistoriador) e `nao` (financeiro); ver `contas.md`.

## Estados

`agendada` → `em_transito` (Iniciar) ou `cancelada`; "Sair agora" nasce `em_transito`; `em_transito` → `no_local` (chegou à parada) → `em_transito` (saiu da parada); `em_transito` → `concluida` (chegada no destino, depois de todas as paradas). `concluida` e `cancelada` não mudam mais. Transição fora disso: 409 `{ "codigo": "transicao_movimentacao", "mensagem": "Não é possível <ação> uma movimentação <status>", "detalhes": { "de": "em_transito", "para": "cancelada" } }` (CA-246-06). Toda mudança grava evento de auditoria de operação com o código e o veículo (CA-246-13): `movimentacao.criar`, `.editar`, `.iniciar`, `.chegar_parada`, `.sair_parada`, `.concluir`, `.cancelar`.

## Representação

```json
{
  "id": 2, "codigo": "MOV-0002", "status": "em_transito",
  "veiculo": { "id": 501, "placa": "SAK1D39", "modelo": "Honda CG 160 Fan", "status": "em_movimentacao" },
  "filial_saida": { "id": 1, "nome": "Filial Centro" },
  "destino": { "id": 2, "nome": "Filial Caucaia" }, "transferencia": true,
  "categoria_destino": { "id": 7, "nome": "Street 150–160" },
  "rota": "Centro → Lava Rápido Aldeota → Filial Caucaia",
  "levado_por": { "id": 4, "nome": "João Silva" },
  "agendada_para": null, "iniciada_em": "2026-10-07T13:02:00Z", "concluida_em": null,
  "duracao_minutos": null,
  "vistoria_rapida": true, "km_saida": 3120,
  "paradas": [
    { "id": 11, "ordem": 1, "local": { "id": 3, "nome": "Lava Rápido Aldeota", "tipo": "lava_jato", "ativo": true },
      "servico": "Lavagem completa", "categoria": "outros", "valor_previsto_centavos": 3500,
      "chegou_em": "2026-10-07T13:15:00Z", "saiu_em": "2026-10-07T13:58:00Z", "valor_pago_centavos": 3500,
      "despesa": { "id": 77, "status": "a_pagar", "sem_nota": false } }
  ],
  "proxima_etapa": "destino",
  "chegada": null,
  "custo_centavos": 3500,
  "acoes": { "editar": false, "iniciar": false, "cancelar": false, "chegar_parada": false, "sair_parada": false,
             "registrar_chegada": true }
}
```

- `rota`: montada pela API, com o nome curto da filial de saída, os locais na ordem e o destino ("Centro → Lava Rápido Aldeota → Centro").
- `transferencia`: destino diferente da filial de saída (`MOV-06`). `categoria_destino` só existe na transferência.
- `km_saida`: o km do veículo ao iniciar. `duracao_minutos`: de `iniciada_em` a `concluida_em`, só na concluída ("1 h 10 min" é formatação da tela).
- `proxima_etapa`: `parada:<id>` (a próxima parada sem chegada, ou a parada atual em `no_local`), `destino` ou `null` (agendada, concluída, cancelada). A chegada no destino só é aceita depois da saída da última parada.
- `custo_centavos`: soma dos `valor_pago_centavos` das paradas.
- `despesa`: a despesa gerada na saída da parada, ou `null` (parada ainda aberta ou valor zero). `sem_nota` como em `financeiro.md`.
- `chegada`: depois da conclusão, `{ "km": 3146, "combustivel": "cheio", "recebido_por": { "id": 9, "nome": "Paulo Lima" }, "fotos": [ { "posicao": "frente", "url": "...", "url_expira_em": "..." } ] }`. Antes dela, as fotos já enviadas vêm em `fotos_chegada` (mesmo formato), para a tela contar "Fotos · 2 de 4".
- `acoes`: a API decide pelo perfil, pela filial, por quem leva, pelo status e pela `proxima_etapa`. A tela mostra só o que vier `true`.
- O vistoriador recebe a movimentação sem nenhum campo `_centavos` (como em toda a API, `USR-09`).

## Quadro

### GET /api/movimentacoes/quadro/
Tela `Movimentacoes`. Query `?filial=<id>` (padrão: o seletor do topo; administrador pode "Todas as filiais"). Quem leva recebe só as dele.
```json
{ "colunas": [
  { "status": "agendada", "rotulo": "Agendadas", "total": 1, "itens": [ "<linha>" ] },
  { "status": "em_transito", "rotulo": "Em trânsito", "total": 1, "itens": [ ] },
  { "status": "no_local", "rotulo": "No local de apoio", "total": 0, "itens": [ ] },
  { "status": "concluida", "rotulo": "Concluídas", "total": 1, "itens": [ ] } ] }
```
- `<linha>` é a representação sem `paradas` e sem `chegada`, mais `paradas_total` e `resumo`: "amanhã 08:00" (agendada), "saiu 10:02 · 1 parada" (em trânsito), "no Lava Rápido Aldeota desde 10:15" (no local) e "hoje 08:30 · 1 h 10 min" (concluída). O `resumo` é texto pronto, no fuso da filial.
- Concluídas: só as concluídas hoje (dia local da filial de saída), da mais nova para a mais antiga. As outras ficam na lista abaixo. Agendadas por `agendada_para`; em trânsito e no local por `iniciada_em`.
- Cada coluna traz até 50 itens; `total` conta todos.

### GET /api/movimentacoes/
Query `?status=` (aceita vários, separados por vírgula), `?veiculo=<id>` (o "ver todas" da ficha, T-275), `?filial=<id>`, `?levando=eu`, `?periodo_inicio=`, `?periodo_fim=` (pela data de início ou de agendamento), `?busca=` (código, placa). Paginada, mais nova primeiro. Linhas como no quadro.

### GET /api/movimentacoes/{id}/
200: a representação.

## Criar e mudar

### POST /api/movimentacoes/
Tela `Movimentacao-Nova`. Corpo:
```json
{ "veiculo_id": 501,
  "paradas": [ { "local_id": 3, "servico": "Lavagem completa", "valor_previsto_centavos": 3500, "categoria": "outros" } ],
  "destino_filial_id": 1, "categoria_destino_id": null,
  "levado_por_id": 4, "sair_agora": true, "agendada_para": null,
  "vistoria_rapida": false }
```
- `paradas`: zero ou mais, na ordem (`MOV-01`). `categoria` da parada é uma das categorias da `FIN-06`; padrão `outros`, e `manutencao` quando o local é `oficina` (`MOV-04`). Local inativo: 400 em `paradas[n].local_id`. Não há campo de OS no MVP (CA-246-07).
- `destino_filial_id`: uma filial ativa da empresa, a de saída (ida e volta) ou outra (transferência). A filial de saída é sempre a do veículo; não vem no corpo.
- `categoria_destino_id`: na transferência, pela `VEI-04`: obrigatória quando a categoria do veículo é só da filial de saída (400 `validacao` "Escolha a categoria do veículo na Filial Caucaia."), e tem de ser uma categoria ativa do mesmo tipo de veículo, da empresa ou da filial de destino. Fora da transferência, ignorada.
- `vistoria_rapida`: na transferência é sempre `true` (a API grava `true` mesmo que venha `false`); na volta à mesma filial, a escolha da tela (`MOV-05`).
- `levado_por_id`: usuário ativo ligado à filial de saída, de qualquer perfil menos o financeiro (400 `validacao` em `levado_por_id`).
- `sair_agora: true` nasce `em_transito` (com os efeitos de Iniciar, abaixo); senão, `agendada_para` é obrigatório e no futuro, e nasce `agendada`.
201: a representação, com o código `MOV-` da empresa.
Erros:
- 403 `permissao` (perfil, ou filial do veículo fora do escopo do gerente).
- 409 `{ "codigo": "MOV-03", "mensagem": "Veículo alugado não se movimenta.", "detalhes": { "status": "alugado", "locacao_codigo": "LOC-2841" } }`: veículo `alugado`, `reservado`, `vendido`, `baixado` ou `em_movimentacao`, ou `disponivel` com locação `aguardando_retirada` ("O veículo está reservado na LOC-2850.") (CA-246-04).
- 409 `{ "codigo": "MOV-03", "mensagem": "O veículo já está na MOV-0001.", "detalhes": { "movimentacao_id": 1 } }`: outra movimentação `agendada`, `em_transito` ou `no_local` do veículo (pela restrição do banco, ADR 0028).
Regras: MOV-01 a MOV-03, MOV-06, VEI-04.

### PATCH /api/movimentacoes/{id}/
Reagendar ou mudar a agendada (CA-246-05). Só `agendada`: mesmo corpo, menos `veiculo_id` e `sair_agora`. 200. Fora de `agendada`, 409 `transicao_movimentacao`.

### POST /api/movimentacoes/{id}/iniciar/
`agendada` → `em_transito`. Corpo `{}`. Numa transação, com a linha do veículo travada (ADR 0028):
- confere de novo o veículo: `alugado`, `reservado`, `vendido`, `baixado`, ou `disponivel` com locação `aguardando_retirada` → 409 `MOV-03` com o motivo, e a movimentação continua `agendada` (CA-246-05);
- grava `iniciada_em` e `km_saida`;
- o veículo `disponivel` vai para `em_movimentacao` (`veiculos.services.transicionar`, origem a movimentação): sai da Nova locação e da reserva. `indisponivel`, `em_manutencao` e `a_venda` ficam como estão (CA-246-07).
200: a representação.

### POST /api/movimentacoes/{id}/cancelar/
Corpo `{ "motivo": "..." }`. Só `agendada` → `cancelada`; o veículo não muda. Depois de iniciada, 409 `transicao_movimentacao` (CA-246-06).

## Paradas e chegada

### POST /api/movimentacoes/{id}/paradas/{parada_id}/chegada/
"Cheguei" na parada: `em_transito` → `no_local`. Corpo `{}`. Só a parada da `proxima_etapa`; outra, 409 `{ "codigo": "parada_fora_de_ordem" }`. Grava `chegou_em`. 200.

### POST /api/movimentacoes/{id}/paradas/{parada_id}/saida/
Saída da parada, com o valor pago ("confira com o recibo", `MOV-04`): `no_local` → `em_transito`. `multipart/form-data`: `valor_pago_centavos` (≥ 0, obrigatório), `nota?` (imagem ou PDF até 10 MB, as validações de `comum.arquivos`). Numa transação:
- grava `saiu_em` e `valor_pago_centavos`;
- com valor acima de zero, chama `financeiro.services.lancar_despesa` com a filial de saída, o veículo, `data` e `vencimento` no dia local da saída, a `categoria` da parada, a descrição "MOV-0001 · Lavagem completa · Lava Rápido Aldeota", a `nota` (ou `None`), quem registrou como `lancada_por` e a origem `movimentacao`. A despesa segue a `FIN-05`: até o limite da empresa, `a_pagar`; acima, `aguardando_aprovacao` com o pedido `APR-03` (CA-246-02, 08). Sem nota, nasce com `sem_nota: true` (CA-246-14);
- valor zero: nenhuma despesa.
200: a representação.

### POST /api/movimentacoes/{id}/chegada/fotos/
Vistoria rápida (`MOV-05`). `multipart/form-data`: `posicao` (`frente`, `traseira`, `lado_esquerdo`, `lado_direito`) e `arquivo` (JPG ou PNG até 10 MB; reprocessada, sem metadados de localização, ADR 0028). Só com `vistoria_rapida`, em `em_transito`, com a `proxima_etapa` = `destino`. Nova foto da mesma posição substitui a anterior. 201: `{ "posicao", "url", "url_expira_em" }`. As fotos vão uma por vez porque o proxy aceita até 12 MB por corpo.

### POST /api/movimentacoes/{id}/chegada/
"Confirmar chegada" (`Movimentacao-Chegada-Mobile`): `em_transito` → `concluida`. Corpo `{ "km": 3146, "combustivel": "cheio", "recebido_por_id": 9 }`. Só com a `proxima_etapa` = `destino` (paradas todas saídas; senão 409 `parada_fora_de_ordem`).
- `km`: obrigatório, nunca menor que o atual: 422 `{ "codigo": "VEI-01", "mensagem": "O km informado é menor que o atual (3.120).", "detalhes": { "km_atual": 3120 } }` (CA-246-03). Atualiza o veículo e grava a `LeituraKm` com a origem (`veiculos.services.atualizar_km`, `VEI-02`).
- Com `vistoria_rapida`: `combustivel` (enum da vistoria) e as 4 fotos são obrigatórios. Falta algo: 400 `{ "codigo": "validacao", "campos": { "combustivel": ["Informe o combustível."], "fotos": ["Faltam 2 fotos."] } }` (CA-246-09). Sem vistoria rápida, só o km (CA-246-03).
- `recebido_por_id`: na transferência, obrigatório, um usuário ativo ligado à filial de destino (400 em `recebido_por_id`); fora dela, ignorado.
Numa transação, com a linha do veículo travada: a movimentação fica `concluida` com `concluida_em`; o veículo `em_movimentacao` vai para `disponivel`, ou para `indisponivel` com o motivo do documento (ex.: "CRLV vencido") se o CRLV ou o seguro está vencido no dia da chegada (`VEI-03`, CA-246-10); os outros status não mudam. Na transferência, `veiculos.services.transferir` com a categoria pedida na criação e a origem `movimentacao` (`MOV-06`, ADR 0028): o veículo passa a ser da filial de destino, com a `TransferenciaVeiculo` gravada (CA-246-09).
200: a representação. Regras: MOV-05, MOV-06, VEI-01 a VEI-04.

## Locais de apoio

### GET /api/movimentacoes/locais/
Perfis: quem tem `pode.movimentacoes` = `gerir`. Query `?ativo=` (padrão `true`; a escolha da parada só mostra ativos), `?tipo=`, `?busca=`. `{ "resultados": [ { "id": 3, "nome": "Lava Rápido Aldeota", "tipo": "lava_jato", "ativo": true } ] }`. São da empresa e valem para todas as filiais (`MOV-01`).

### POST /api/movimentacoes/locais/
"Novo local", na parada da Nova movimentação. Administrador e gerente. Corpo `{ "nome": "Lava Rápido Aldeota", "tipo": "lava_jato" }`; `tipo` em `lava_jato`, `oficina`, `despachante`, `outro`. 201. Nome repetido na empresa (sem diferença de maiúsculas, acentos e espaços): 409 `{ "codigo": "local_existente", "mensagem": "Já existe um local com este nome.", "detalhes": { "local_id": 3, "ativo": true } }` (CA-246-15). Vendedor: 403.

### POST /api/movimentacoes/locais/{id}/inativar/ · POST /api/movimentacoes/locais/{id}/reativar/
Administrador. 200. O local inativo sai da escolha e continua nas movimentações antigas com o nome dele. Nada é apagado.

## Reflexos em outros contratos

| Onde | O que muda |
| --- | --- |
| `veiculos.md` | status `em_movimentacao` (rótulo "Em movimentação", tom `info`); bloco `movimentacao_aberta` na lista e no detalhe; filtro `?em_movimentacao=true`; contador da Frota; `acoes.movimentar` e `acoes.transferir` (que abre a Nova movimentação); a rota `transferir` sai (ADR 0028, item 6) |
| `locacoes.md` | veículo `em_movimentacao` não aparece na escolha da Nova locação nem na reserva (já fica de fora por não ser `disponivel`); `confirmar` trava a linha do veículo (ADR 0028, item 3) |
| `financeiro.md` | origem `movimentacao` na despesa; `sem_nota`; `POST /api/financeiro/despesas/{id}/nota/` |
| `contas.md` | `pode.movimentacoes`; item de menu `movimentacoes` |
| Ocupação (`VEI-06`) | sem mudança: `em_movimentacao` conta como dia na frota e não como alugado (CA-246-12) |
| `AUT-06` | veículo `em_movimentacao` com CRLV ou seguro vencendo não muda de status; tarefa urgente aos gerentes; a chegada decide (`MOV-05`) |

## Interface interna

| Função | Uso |
| --- | --- |
| `movimentacoes.selectors.aberta(veiculo)` | a movimentação `agendada`, `em_transito` ou `no_local` do veículo; base do bloco `movimentacao_aberta` (registro de leituras, ADR 0015) |
| `locacoes.selectors.locacao_aberta(veiculo)` | lido ao criar e iniciar (`MOV-03`) |
| `veiculos.services.travar`, `transicionar`, `atualizar_km`, `transferir(..., origem=movimentacao)` | ADR 0028 |
| `financeiro.services.lancar_despesa(..., origem=...)` | despesa da parada (`MOV-04`) |
| eventos publicados | nenhum no MVP |

# Veículos, categorias e preços

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-036) · **App:** `veiculos` (schema da empresa) · **Regras:** VEI-01 a VEI-07, LOC-01, LOC-02, LOC-15, PLT-03, APR-06, AUD-05 · **ADRs:** 0011, 0015 · **Telas:** Frota, Veiculo, Precos

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

Ver é liberado a todos os perfis no escopo das suas filiais porque toda a operação (nova locação, vistoria, caixa) consulta o veículo; dados de compra (`valor_compra_centavos`) só saem para administrador e gerente.

## Representação do veículo

```json
{
  "id": 501,
  "placa": "SAK1D39",
  "chassi": "9C2KC2210RR004417",
  "renavam": "01289934410",
  "marca": "Honda", "modelo": "CG 160 Fan", "ano_fabricacao": 2025, "ano_modelo": 2025, "cor": "vermelha",
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
             "desbloquear": false, "transferir": true, "baixar": false, "registrar_km": true, "corrigir_km": true }
}
```

- `placa` sai sem hífen; aceita padrão antigo (`ABC1234`) e Mercosul (`ABC1D23`). `chassi` com 17 letras e números.
- `preco_vigente`: preço da categoria vigente hoje (`LOC-15`). A coluna "Diária" da Frota usa `diaria_centavos`; veículo `a_venda` mostra `valor_venda_centavos`.
- `situacao`: a API decide. Base no `status` do veículo; um bloco com `alerta` (ADR 0015) sobrepõe, ex.: "Atrasado" (`perigo`) quando a locação atual está `devolucao_atrasada`.
- `acoes`: combina perfil, `status` e a tabela de transições; o frontend mostra só o que vier `true`.
- `valor_compra_centavos` e `data_compra` vêm `null` para quem não é administrador ou gerente.

### Blocos de outros apps (ADR 0015)

| Bloco | Fornecedor | Conteúdo | Antes do fornecedor existir |
| --- | --- | --- | --- |
| `locacao_atual` | `locacoes` | `{ "id", "codigo": "LOC-2841", "status", "cliente_nome": "Carlos Menezes", "inicio", "fim_previsto", "alerta"? }` para locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada` do veículo | `null` |
| `manutencao` | `manutencao` | `{ "proxima": { "servico", "km" } \| null, "os_aberta": { "id", "codigo": "OS-118", "status" } \| null, "alerta"? }` | `null` |
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
                 "motos": 80, "carros": 6 },
  "resultados": [ { ...representação, sem "indicadores_financeiros"... } ],
  "proximo": "...", "anterior": null
}
```
- `contagens` respeitam os filtros de filial e tipo, não o de status (para as abas).
- `vendido` e `baixado` só aparecem com `?status=vendido` ou `?status=baixado` (histórico).
- Exportar: `POST /api/veiculos/exportar/` `{ formato: "planilha" | "csv", filtros }`, só administrador (exportar é da Administração), → 202 `{ "exportacao_id" }`; o arquivo sai pela exportação em segundo plano (`AUD-07`), não na resposta.

### GET /api/veiculos/{id}/
200: representação completa, com `indicadores_financeiros` e:
```json
"ocupacao": { "pct": "86.00", "periodo_dias": 90 },
"historico_status": [ { "de": "disponivel", "para": "alugado", "em": "...", "origem_codigo": "LOC-2841" } ]
```
- `ocupacao` (`VEI-06`): dias `alugado` ÷ dias na frota nos últimos 90 dias, a partir do `HistoricoStatusVeiculo`, excluindo os dias em `a_venda`, `vendido` e `baixado`. Calculada pelo app `veiculos`.
- Locações e manutenções da ficha vêm das listas dos outros módulos: `GET /api/locacoes/?veiculo=<id>` e `GET /api/manutencao/ordens/?veiculo=<id>` (contratos de locações e manutenção).

### POST /api/veiculos/
Perfis: administrador, gerente.
Corpo: `{ placa, chassi, renavam?, marca, modelo, ano_fabricacao, ano_modelo, cor, km_atual, categoria_id, filial_id, capacidade_tanque_litros?, valor_compra_centavos?, data_compra?, entrou_na_frota_em? }`. Sem `capacidade_tanque_litros`, o combustível do acerto é informado à mão (`DEV-01`).
201: representação (status `disponivel`).
400 `validacao`: placa ou chassi fora do formato, categoria de outra filial, ano inválido.
409 `{ "codigo": "VEI-01", "mensagem": "Já existe um veículo com esta placa", "detalhes": { "campo": "placa", "veiculo_id": 77 } }`; o mesmo para `chassi`. Vale para veículo em qualquer estado, inclusive `vendido` e `baixado`.
422 `PLT-03`: limite de veículos do plano.
Efeitos: grava a primeira `LeituraKm` e o `HistoricoStatusVeiculo` inicial; `atualizar_uso("veiculos", +1)`.
Recompra numa troca (`VEN-05`, `VEI-07`) não passa por aqui: a venda chama `veiculos.services.receber_na_troca(chassi, ...)`, que acha o cadastro pelo chassi e leva o veículo de `vendido` para `indisponivel`.
Regras: VEI-01, PLT-03.

### PATCH /api/veiculos/{id}/
Perfis: administrador, gerente. Corpo: `renavam`, `marca`, `modelo`, `ano_fabricacao`, `ano_modelo`, `cor`, `categoria_id`, `capacidade_tanque_litros`, `valor_compra_centavos`, `data_compra`.
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
| `baixar` | `{ motivo: "perda_total" \| "roubo" \| "sucata" \| "outro", descricao }` | qualquer, exceto `alugado` → `baixado` | administrador |

As transições de locação, vistoria, OS e venda não têm endpoint aqui: acontecem pelos serviços desses módulos.

### POST /api/veiculos/{id}/transferir/
Perfis: administrador, gerente (com acesso à filial de origem). Corpo: `{ filial_destino_id, motivo? }`.
Só com o veículo `disponivel`: senão 409 `{ "codigo": "VEI-04", "mensagem": "Só é possível transferir um veículo disponível" }`. Destino inativo ou igual à origem → 400.
Grava `TransferenciaVeiculo` com origem e destino (`VEI-04`). 200: representação.

## Km

### POST /api/veiculos/{id}/km/
Perfis: administrador, gerente, vistoriador. Corpo: `{ km }`.
200: representação. 422 `{ "codigo": "VEI-01", "mensagem": "O km informado é menor que o atual (18.950). Para corrigir, use Corrigir km.", "detalhes": { "km_atual": 18950 } }`.
Vistoria e OS atualizam o km pelos próprios serviços (`VEI-02`); este endpoint é para leitura avulsa. Cada leitura dispara o recálculo das preventivas (`MAN-03`, pelo evento `veiculos.km_atualizado`).

### POST /api/veiculos/{id}/corrigir-km/
Corpo: `{ km, motivo }`.
- Administrador ou gerente: aplica na hora, com `LeituraKm` de correção e auditoria. 200: representação.
- Vistoriador: cria o pedido `APR-06`. 202: `{ "pedido_aprovacao": { "id": 88, "tipo": "APR-06", "status": "pendente" } }`. O km muda só quando o gerente aprovar.
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
Perfis: administrador, gerente. `multipart/form-data`: `tipo`, `validade`, `arquivo?` (PDF, JPG ou PNG, até 10 MB).
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
`tipo_veiculo` não muda se a categoria já tem veículos (422 `{ "codigo": "categoria_com_veiculos" }`), porque ele define a CNH exigida (`CLI-02`).
`POST /api/categorias/{id}/desativar/` e `/reativar/`: desativada some da escolha em cadastros novos; 422 `categoria_com_veiculos` se ainda houver veículos ativos nela.

### GET /api/categorias/{id}/precos/
Perfis: todos. Histórico (`LOC-15`), do mais novo ao mais velho: `{ "resultados": [ { "vigente_desde": "2026-10-01", "diaria_centavos": 5490, "semanal_centavos": 32900, "mensal_centavos": 119000, "caucao_centavos": 30000, "alterado_por": "Mariana Costa", "alterado_em": "..." } ] }`.

### POST /api/categorias/{id}/precos/
Perfil: administrador. Corpo: `{ vigente_desde, diaria_centavos, semanal_centavos, mensal_centavos, caucao_centavos }`.
- `vigente_desde` ≥ hoje (o passado não se reescreve). Padrão: hoje.
- Preço novo vale só para contratos novos; contrato assinado mantém o preço da assinatura (`LOC-15`). A resposta traz `"locacoes_em_andamento_mantidas": 12` para a tela avisar.
- 409 `{ "codigo": "preco_ja_definido", "mensagem": "Já existe preço a partir desta data" }` quando a data já tem preço vigente; preço agendado para o futuro pode ser trocado com `PUT /api/categorias/{id}/precos/{vigente_desde}/` até a data chegar.
Caso do seed: Street semanal 29940 até 30 set e 32900 a partir de 01 out; LOC-2841, assinada em 23 set, continua com 29940 (`LOC-15`).

### GET /api/precos/historico/
Perfil: administrador. Todas as mudanças de preço da empresa, para "Histórico de preços": `{ "resultados": [ { "categoria", "vigente_desde", "campo", "antes_centavos", "depois_centavos", "alterado_por", "alterado_em" } ] }`.

## Extras (LOC-02)

`GET /api/extras/` (todos) → `{ "resultados": [ { "id", "nome": "Capacete extra", "valor_centavos": 1500, "cobranca": "por_periodo" | "unica", "ativo": true } ] }`.
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
| evento `veiculos.km_atualizado` | assinado por `manutencao` (preventivas, `MAN-03`). |
| evento `veiculos.documento_vencendo` / tarefa `aut_06_vencimento_de_documentos` | `VEI-03`, `AUT-06`: 30 dias antes avisa; no dia, CRLV ou seguro vencido leva `disponivel` → `indisponivel`; veículo alugado não muda e gera tarefa urgente para o gerente. |
| anotações de leitura fornecidas | `indicadores` de `Filial` (`veiculos`, `ocupacao_pct`), ver `filiais.md`. |

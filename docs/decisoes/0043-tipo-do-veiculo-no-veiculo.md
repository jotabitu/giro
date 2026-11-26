# Tipo do veículo no próprio veículo e saída do tipo de plano (categoria)

**Status:** aceita · 26 nov 2026 · T-522 (regras: `VEI-01`, `VEI-04`, `VEI-11`, `VEI-12`, `VEI-15`, `IMP-02`, `IMP-05`, `IMP-07`, `IMP-08`, `MOV-06`, `FIL-04`, `LOC-01`, `LOC-02`, `LOC-08`, `LOC-09`, `CLI-02`, `VIS-01`; decisões do dono de 26 nov 2026; regras no PR #692 do Produto; pontos em aberto T-522 · 1 a 3 com os padrões desta ADR) · **substitui em parte a 0041** (o papel da `Categoria` como "tipo" e como modelo de preço do cadastro, da importação e do assistente) · detalha a 0011 e a 0015

## Contexto

Até aqui o veículo não tinha tipo próprio. `Veiculo.categoria` é FK obrigatória (`PROTECT`) para `veiculos.Categoria`, que as telas chamam de "Tipo de plano" (T-507), e o moto ou carro do veículo é `veiculo.categoria.tipo_veiculo` (`VEI-11`). Esse tipo decide a CNH exigida (`CLI-02`), os itens da vistoria (`VIS-01`), os filtros Moto e Carro da Frota e da Nova locação, o ícone e os textos "desta moto" ou "deste carro". Desde a ADR 0041 o preço é de cada veículo; a categoria sobrou como tipo, como modelo de preço (`PrecoCategoria`) do cadastro, da importação e do passo Preços do assistente, como tabela da filial (`FIL-04`) na transferência e como restrição dos planos especiais antigos.

Decisões do dono de 26 nov 2026, em duas etapas no mesmo dia:

1. Moto ou carro passa a ser dado do próprio veículo, com o rótulo **"Veículo"**.
2. O tipo de plano sai **de vez**: "não faz mais sentido na regra de negócio atual; a escolha dos preços vai ser feita individualmente em cada veículo, então esse campo é inútil". Sai do cadastro, do editar, da importação (`IMP-08`), da transferência (`FIL-04`, `MOV-06`), dos planos especiais, do passo Preços do assistente (`IMP-05`, `IMP-07`) e da tela de administração dos tipos de plano.

A primeira versão desta ADR (mesmo PR, #693) deixava o tipo de plano opcional; esta a substitui inteira.

É caro de desfazer porque muda uma coluna de um model central, migra todos os veículos de todas as empresas, tira um passo do assistente e do funil da plataforma e troca a fonte de uma informação lida por seis apps.

## Decisão

### 1. Modelo

**`Veiculo.tipo_veiculo`, novo.** `CharField(max_length=10, choices=TipoVeiculo.choices)`, obrigatório, **sem default no model**. `TipoVeiculo` é o enum que já existe em `veiculos.models` (`moto`, `carro`). Um default `moto` faria um carro esquecido virar moto em silêncio, e a CNH (`CLI-02`) é conferida por ele; quem cria veículo informa o tipo, e a falta é erro de validação. `CheckConstraint` `veiculo_tipo_valido` (`tipo_veiculo IN ('moto', 'carro')`) e índice `(filial, tipo_veiculo)` para os filtros e as contagens.

**`Veiculo.categoria`, dado antigo.** Vira `null=True, blank=True`, continua `PROTECT` e continua no banco com o valor de hoje nos veículos que já existem. Veículo novo nasce com `categoria` nula. Nenhuma tela, nenhuma API e nenhuma regra nova lê ou grava o campo; a única leitura que fica é a das locações antigas (item 3, "Locações antigas"). Ele sai do `retrato` da auditoria dos eventos novos; os eventos antigos não mudam.

**Guardados sem leitura e sem tela** (nada de negócio se apaga, `CLAUDE.md`): `veiculos.Categoria`, `veiculos.PrecoCategoria`, `locacoes.PlanoCompra`, `locacoes.PlanoEspecial` (com o M2M `categorias`), `movimentacoes.Movimentacao.categoria_destino` e os campos de categoria de `TransferenciaVeiculo`. Os models ficam no código (as FKs das locações antigas apontam para eles) e no Django Admin só para leitura do suporte, se já estiverem lá. Tirar as tabelas do banco, se um dia for o caso, pede outra ADR, como a 0041 já dizia.

### 2. Migração

**`veiculos`, depois da `0013_excluido`:**

- `0014_tipo_do_veiculo` (esquema): `AddField("veiculo", "tipo_veiculo", ..., default="moto", preserve_default=False)` (o default só preenche a coluna nas linhas que existem; o model fica sem default); `AlterField` de `categoria` para nula; `AddConstraint` e `AddIndex`.
- `0015_tipo_pela_categoria` (dados, `RunPython`):

```python
def preencher(apps, schema_editor):
    db = schema_editor.connection.alias if schema_editor is not None else "default"
    veiculo = apps.get_model("veiculos", "Veiculo")
    (
        veiculo._base_manager.using(db)
        .filter(categoria__tipo_veiculo="carro")
        .update(tipo_veiculo="carro")
    )
```

- **`.using(schema_editor.connection.alias)`**, como a `0010_copiar_precos_da_categoria`: a empresa nova é migrada pela conexão do papel de migração, no schema dela (ADR 0040, `plataforma.banco.criar_schema`); a `default` aponta para outro schema e não tem a tabela.
- **`_base_manager`**: o excluído (`VEI-22`), o `vendido` e o `baixado` também recebem o tipo; o manager `objects` tira o excluído.
- Todos nascem `moto` pela `0014`; a `0015` só corrige os de categoria de carro. Um `UPDATE` por empresa, idempotente.
- **Na criação de empresa nova** a migração roda e não acha veículo: nada é alterado. Teste explícito (item 8).
- O `update()` não fere a regra de status por serviço (`tipo_veiculo` não é status) e não gera evento de auditoria, como a `0010`.
- **Reversa**: `noop` na `0015`; a da `0014` volta `categoria` a obrigatória e só funciona antes do primeiro veículo novo sem categoria. Aceito.

**`plataforma` (schema público), etapa Preços do funil (`IMP-05`):**

- `00NN_funil_sem_precos` (`RunPython`): cada `Empresa` com `etapa_implantacao = "precos"` passa para a etapa que o cálculo de sempre dá sem o passo Preços (a função que hoje devolve a etapa, chamada com o `FUNIL` novo). `etapa_implantacao_desde` passa a ser a hora da migração, para a empresa não cair em "precisam de ajuda" (3 dias no mesmo passo) por um passo que ela não fez.
- Depois, o valor `precos` sai de `EtapaImplantacao` (é só `choices`, sem mudança de coluna).
- O `"precos"` que já está em `UsoEmpresa.passos_implantacao` (json dos passos feitos) fica guardado e é ignorado, porque o passo sai de `PASSOS_IMPLANTACAO`.

**Seed (`seed/frota.py`, `seed/precos.py`)**: as categorias e o `criar_preco` saem; cada veículo é criado com `tipo_veiculo` e recebe os planos direto pelo serviço da tela de preços (ADR 0041), com os mesmos valores de hoje (Street semanal R$ 329,00 e o resto). Nenhum número de `dados-de-teste.md` muda; o texto que fala das 4 categorias é do Produto.

### 3. Quem lia a categoria e o que fica no lugar

Levantado no código da `origin/develop` de 26 nov 2026 (`1be376d2`).

**O tipo: lê `veiculo.tipo_veiculo`** (sem isso, um veículo sem categoria quebra com `AttributeError` em `None`).

| App | Onde | Uso | Regra |
| --- | --- | --- | --- |
| `veiculos` | `selectors.do_tipo` e `selectors.contagens` | filtro e contagem Moto ou Carro da Frota e da Nova locação | `VEI-11` |
| `veiculos` | `selectors` ficha e lista | `tipo_veiculo` da resposta | `VEI-11` |
| `veiculos` | `services.editar`, `motivo_de_nao_trocar_tipo` | troca do Veículo, 409 `tipo_com_locacao_aberta` | `VEI-11` |
| `veiculos` | `services` ("deste carro" ou "desta moto"), `exclusao.py` | textos | `VEI-15`, `VEI-22` |
| `locacoes` | `services` linhas 331 e 1563, `selectors` linhas 476 e 905 | CNH exigida e o `tipo` na resposta | `CLI-02`, `LOC-09` |
| `vistorias` | `services.ITENS_PADRAO[...]` (linha 135), CNH (linha 361), `selectors` linha 95 | itens da vistoria e CNH | `VIS-01`, `CLI-02` |
| `clientes` | `selectors` (CNH) | nada muda: recebe `tipo_veiculo: str`, e quem chama passa `veiculo.tipo_veiculo` | `CLI-02` |

**O resto: sai sem substituto, porque o preço já é do veículo (ADR 0041).**

| Uso da categoria | Onde | O que fica |
| --- | --- | --- |
| Modelo de preço do cadastro e da importação | `veiculos.services._criar` → `aplicar_modelo_de_preco`, `planos_do_modelo` | o veículo nasce com os planos vazios (item 5). `aplicar_modelo_de_preco` passa a não ler categoria e grava só o padrão; `planos_do_modelo` sai |
| Escolha na tela | cadastro, editar, `_categoria_para`, `_validar_dados`, `OBRIGATORIOS_DO_CADASTRO`, `CAMPOS_EDITAVEIS` | sai; `tipo_veiculo` entra nos obrigatórios e nos editáveis |
| Tabela da filial na transferência | `veiculos.services.categoria_no_destino`, `transferir`; `movimentacoes.services._categoria_destino` | sai. A transferência só muda a filial; some o caso de recusa da `VEI-04` (`MOV-06`). `categoria_destino` deixa de ser gravada |
| Importação por modelo | `importacao.linhas` (`CATEGORIA`, `CATEGORIA_PROPRIA`, `categorias_da_filial`), `selectors` (`faltam_categorias`, `_categorias`), `services` (`escolher_categorias`, `_categoria_na_correcao`, `sem_categoria`) | vira o Veículo por modelo (item 4) |
| Tela de tipos de plano e histórico | `veiculos.api` `/categorias/`, `.../precos/`, histórico; serviços `criar_categoria`, `editar_categoria`, `desativar_categoria`, `reativar_categoria`, `criar_preco`, `trocar_preco_futuro`; `locacoes.leituras.locacoes_da_categoria` | sai (rotas e serviços). Os formatadores de auditoria dos eventos `categoria.*` ficam, para os eventos antigos se lerem |
| Lista de planos especiais e de compra da tela | `locacoes.api` (lista com `?categoria=`, detalhe do `PlanoCompra`), `selectors.planos_especiais`, `planos_compra` | sai (cadastro já respondia 410 desde a ADR 0041) |
| Passo Preços e cartão de Configurações | `plataforma.services.PASSOS_IMPLANTACAO`, `FUNIL`, `veiculos.apps` (`registrar_conferencia_de_passo("precos", ...)`, `registrar_passo_implantacao("precos")`), `relatorios.configuracoes` (`precos`, `resumo_precos`), `relatorios.selectors.PASSOS_DA_CONFIGURACAO`, `categorias_ativas` | sai o passo, a conferência, o funil e o resumo. O cartão "Tabelas de preço" depende do ponto em aberto T-522 · 2 (extras) |
| Filtro `?categoria=` | `GET /api/veiculos/`, `selectors` linha 298 | sai |
| `preco_vigente` da categoria na ficha e na lista | `selectors` linha 502, `api/views` linha 180 | sai (já era só informativo) |

**Locações antigas: a leitura fica, só para elas.** A locação confirmada antes da ADR 0041 pode ter `plano_especial` ou `plano_compra` gravados. Renovação (`LOC-08`), troca (`LOC-09`) e acerto delas continuam lendo esses models, como hoje, e nada muda para essas locações:

- `locacoes.services` linha 1358 (renovação: preço fixo e desconto do plano especial);
- `preco_da_troca` linha 1543: o plano especial de preço fixo restrito a categorias continua conferindo `veiculo.categoria_id` do veículo novo. Veículo cadastrado depois desta ADR tem categoria nula e não entra no plano restrito; a troca usa o plano do veículo novo (`LOC-09`), que é o que a ADR 0041 já faz para o plano desligado;
- `locacoes.selectors` linhas 1202 e 1410 (plano de compra antigo).

**O que não muda:** os preços do veículo (`PlanoVeiculo`, `RegrasVeiculo`, `CustosVeiculo`, `PlanoCompraVeiculo`, `HistoricoPrecoVeiculo`), os extras (`LOC-02`, `veiculos.Extra` e `/api/extras/`), as locações já gravadas (`LOC-15`), os contratos (`cliente.cnh_categoria` é a categoria da CNH), `financeiro` (a "categoria" de lá é da despesa, `FIN-06`).

### 4. Contrato da API

`docs/api/veiculos.md`, `importacao.md`, `movimentacoes.md`, `locacoes.md`, `plataforma.md` e `configuracoes.md` mudam nos PRs de cada tarefa.

**Veículos**

- `POST /api/veiculos/`: `tipo_veiculo` (`moto` | `carro`) obrigatório; sem ele, 400 `{"tipo_veiculo": ["Escolha moto ou carro."]}`. `categoria_id` sai do corpo (chave enviada é ignorada, como qualquer campo fora do contrato). O cadastro pelo CRLV-e e o `validar_novo` da importação seguem as mesmas regras. A leitura do CRLV-e não preenche o tipo (o "Motocicleta" do documento fica em `tipo_documento`; ligar os dois é tarefa à parte, se o Produto quiser).
- `PATCH /api/veiculos/{id}/`: aceita `tipo_veiculo`. Com locação aberta, a troca dá 409 `tipo_com_locacao_aberta`, com a frase de hoje. `categoria_id` sai. O evento `veiculo.editar` leva `tipo_veiculo` de antes e depois pelo `retrato`.
- Ficha e lista: `tipo_veiculo` lido do veículo; saem `categoria` e o `preco_vigente` da categoria. Filtro `?tipo_veiculo=` fica; `?categoria=` sai.
- Saem `/api/categorias/` e as rotas filhas (preços, histórico, desativar, reativar). Sem 410: o frontend e o backend sobem juntos, e não há cliente de fora.
- `veiculos.services.receber_na_troca` (troca na venda, `VEI-07`, fase 2 da ADR 0042): `dados` passa a exigir `tipo_veiculo`.

**Movimentações e transferência**

- `categoria_destino_id` sai do corpo de criação; `categoria_destino` sai da resposta. Some o 400 "Escolha a categoria do veículo na <filial>".

**Importação**

- A linha guarda `_tipo_veiculo` no lugar de `_categoria_id`; a exceção da linha (`_tipo_propria`) e a escolha por modelo seguem o mecanismo que existe.
- `POST /api/importacoes/{id}/tipos/` (no lugar de `.../categorias/`) recebe `[{marca, modelo, tipo_veiculo}]`.
- O bloco da importação passa a `tipos`: por modelo `{marca, modelo, veiculos, tipo_veiculo}` (nulo até escolher), sempre perguntado na importação de veículos.
- "Importar" trava com linha a gravar sem `tipo_veiculo`: erro `tipo_do_modelo`, "Escolha o veículo de cada modelo.".
- Sai o 422 `sem_categoria` do começo da importação e o erro da categoria desativada no meio do caminho.
- Correção da linha ("Corrigir aqui"): aceita `tipo_veiculo` no lugar de `categoria_id`.
- A linha nasce como o cadastro (item 5).

**Locações**: saem as listas de planos especiais e de planos de compra da tela de preços e o filtro `?categoria=`; o cadastro deles já respondia 410 e passa a 404 com as rotas fora.

**Plataforma e Configurações**: o passo `precos` sai da lista de passos (`GET /api/implantacao/`, `Plat-Empresa-Detalhe`), do funil (`Plat-Implantacoes`) e do status da configuração (`GET /api/configuracoes/`). O cartão `precos` de Configurações segue o ponto em aberto T-522 · 2.

**OpenAPI**: muda. Quem muda roda `npm run api:gerar`, `npm run typecheck` e conserta no mesmo PR o que deixar de compilar no frontend (`tarefas/README.md`).

### 5. Veículo novo: planos, regras e status

Cadastro, importação e troca na venda criam o veículo pelo mesmo `_criar`, que grava, na mesma transação:

- planos `diaria`, `semanal` e `mensal` com R$ 0,00, desligados, com o "como paga" padrão do período e as quatro formas;
- regras como na migração da ADR 0041 (`VEI-12`, `VEI-14`): dia de atraso e multa mínima R$ 0,00, km excedente R$ 0,00 (franquia livre), desconto sem aprovação 5%, prazo da caução vazio;
- custos vazios e o histórico de preços com a origem `cadastro` ou `importacao`;
- **status `indisponivel` com o motivo "sem preço"** (`VEI-15`); o histórico inicial fica `"" → indisponivel`. A troca na venda já nasce `indisponivel` ("Recebido numa troca") e continua assim. O primeiro plano ligado na tela de preços leva a `disponivel` pelo caminho que já existe.

Ponto em aberto **T-522 · 1**, com este padrão. Se o dono decidir nascer `disponivel` (só fora da Nova locação), muda o status no `_criar` e um teste.

### 6. Assistente de implantação

- O passo `precos` sai de `PASSOS_IMPLANTACAO`; nas regras, o assistente passa de 12 para 11 etapas (4 de compra e 7 passos), com Contrato 8, Recebimentos 9, Importar 10 e Equipe 11 (`IMP-04`, `PLT-12`, #692) e o `Onboarding-Precos` sai do frontend (`PassoPrecos.tsx`).
- O funil da `IMP-05` fica Conta → Marca → Filial → Dados → 1ª locação (migração no item 2).
- Sai a conferência do passo Preços da `IMP-07` (o preço agendado que chegava à data e marcava o passo).
- Sai o atalho "Cadastre os preços antes de importar veículos." da importação.

### 7. Rótulos (com o Produto, `VEI-11`)

- "Moto ou carro" → **"Veículo"** no cadastro e no editar, obrigatório, com Moto e Carro; no cadastro começa em Moto.
- Importação: "Tipo de plano de cada modelo" passa a **"Veículo de cada modelo"**, e "Tipo de plano desta linha" a "Veículo desta linha".
- Ficha: sai a linha "Tipo de plano"; o Veículo aparece no lugar.
- Nova movimentação: sai o campo da categoria no destino.
- Auditoria: a chave `tipo_veiculo` aparece como "veículo".

Os textos finais são os das regras no PR #692; se divergirem daqui, valem os das regras.

### 8. Testes que a mudança pede

- `test_vei_11_tipo_e_do_veiculo`: Frota filtra e conta pelo tipo do veículo, com veículo de categoria nula.
- `test_vei_11_trocar_tipo_com_locacao_aberta_409` (existe; passa a mandar `tipo_veiculo`).
- `test_vei_01_cadastro_sem_tipo_veiculo_400` e `test_vei_01_cadastro_ignora_categoria_id`.
- `test_vei_15_cadastro_nasce_sem_preco` (planos, regras e status do item 5).
- `test_cli_02_cnh_pelo_tipo_do_veiculo` e `test_vis_01_itens_pelo_tipo_do_veiculo`, com veículo de categoria nula.
- `test_mov_06_transferencia_sem_categoria`.
- `test_imp_08_veiculo_por_modelo`, `test_imp_08_importa_sem_tabela_de_preco`.
- `test_imp_05_funil_sem_precos` e a migração da etapa (empresa parada em Preços vai para a seguinte, com `etapa_implantacao_desde` novo).
- `test_loc_09_troca_antiga_com_plano_especial_restrito` (veículo novo sem categoria usa o plano do veículo).
- Migração: `test_t522_migracao_preenche_tipo_pela_categoria` (carros e motos, excluído incluído) e `test_t522_migracao_na_empresa_nova` (schema vazio, pela conexão da migração).
- O `grep` do PR final: nenhum `categoria` de veículo lido fora de `locacoes` (locações antigas) e das migrações.

## Pontos em aberto (dependem do dono)

Registrados pelo Produto em `docs/regras/pontos-em-aberto.md` (PR #692), com a mesma numeração e o padrão A já aplicado nas regras. Os pontos 2 a 7 da primeira versão saem: sem tipo de plano, não há categoria de outro tipo, transferência com tabela da filial, desativar com veículos, plano especial restrito nem passo Preços para decidir.

| Ponto | Pergunta | Opções | Padrão desta ADR |
| --- | --- | --- | --- |
| **T-522 · 1** | Em que status nasce o veículo cadastrado ou importado, que vem sem plano ligado? | A `indisponivel` "sem preço" (`VEI-15`), sai quando um plano é ligado; B `disponivel`, só fora da Nova locação até ligar um plano | A |
| **T-522 · 2** | Onde ficam os extras (`LOC-02`), que hoje estão na tela Tabelas de preço, que sai? | A a tela vira "Extras", só com o painel de extras, e o cartão de Configurações vira "Extras"; B dentro de Configurações, num cartão de locação; C na tela de preços de cada veículo | A |
| **T-522 · 3** | Como a locadora preenche o preço de muitos veículos (os 86 importados da Moto Rápida nascem todos sem preço)? | A um a um na tela de preços do veículo (palavras do dono); B "copiar os planos de outro veículo" na tela de preços (tarefa nova); C colunas de preço opcionais na planilha da importação (tarefa nova) | A |

Nenhum dos três muda o modelo desta ADR: o 1 é uma linha do `_criar`, o 2 é a rota de uma tela, o 3 é tarefa nova se o dono escolher B ou C.

## Divisão em tarefas

| Tarefa | Agente | Depende de | O que entrega | Pronto quando |
| --- | --- | --- | --- | --- |
| **B1** · tipo no veículo | backend | #692 e este PR | itens 1 e 2 (migrações de `veiculos`), o tipo do item 3 em todos os leitores, cadastro e editar sem categoria e com `tipo_veiculo`, item 5, transferência e movimentação sem categoria, saída do `?categoria=` e do `preco_vigente` da categoria, seed sem categorias com os mesmos números; `docs/api/veiculos.md` e `movimentacoes.md`; OpenAPI e o frontend compilando (os campos `categoria` tirados das telas com o mínimo para compilar) | veículo de categoria nula passa por Nova locação, CNH, vistoria de saída, devolução e transferência; migração testada em empresa existente e nova; `make check` limpo |
| **B2** · importação e assistente | backend | B1 | importação com o Veículo por modelo (item 4), saída do passo Preços, do funil, da `IMP-07` e do resumo de Configurações, migração da etapa no `plataforma`, saída das rotas de categoria, planos especiais e de compra da tela; `docs/api/importacao.md`, `plataforma.md`, `configuracoes.md`, `locacoes.md`; OpenAPI | Moto Rápida importa 86 veículos escolhendo o Veículo por modelo; empresa parada em Preços sai da etapa; `test_imp_*` |
| **F1** · cadastro, editar, ficha, movimentação | frontend | B1 | cadastro sem "Tipo de plano" e sem a prévia "Preços da categoria", com "Veículo"; editar com "Veículo", travado com locação aberta como hoje; ficha sem a linha "Tipo de plano"; Nova movimentação sem a categoria no destino; capturas claro e escuro, 1440 e 390 px | testes dos componentes e o E2E do cadastro passando |
| **F2** · importação, assistente e Administração | frontend | B2 e o ponto T-522 · 2 | `CaixaDeImportacao` com "Veículo de cada modelo"; assistente sem `PassoPrecos`; `/admin/precos` conforme o ponto 2 (padrão: só "Extras"), sem categorias, histórico, planos especiais e planos de compra; cartão de Configurações; capturas | testes do assistente e da tela de extras |
| **DS** · telas de referência | design-system | #692 e este PR | `Veiculo-Novo` e o editar com "Veículo" e sem tipo de plano; ficha sem a linha; `Onboarding-Importar` com "Veículo de cada modelo"; sai o `Onboarding-Precos` e o assistente fica com 7 passos (11 etapas); tela "Extras" (ponto T-522 · 2); Nova movimentação sem categoria; índice `docs/telas/README.md` | as telas citadas em F1 e F2 batem com as regras do #692 |
| **QA** · conferência do lote | qa | B1, B2, F1, F2 | critérios e E2E com o seed novo: cadastro que nasce "sem preço", 86 veículos importados sem preço, transferência sem categoria, CNH e vistoria pelo Veículo, assistente com 7 passos | E2E verde na `develop` antes da promoção |

B1 vem antes de tudo no código (o campo novo); DS pode correr junto com B1. B2 e F1 podem correr em paralelo depois de B1 mesclado; F1 e F2 seguem as telas de DS. O seed fica em B1, porque sem ele os testes da `dados-de-teste.md` quebram assim que o cadastro deixa de ler a categoria. Os extras não pedem backend novo (`/api/extras/` fica); só a rota da tela e o cartão de Configurações, em B2 e F2. Cuidado com conflito: o PR #691 (T-521, aberto) mexe no `NovoVeiculoForm`; F1 começa depois dele mesclado ou faz `merge origin/develop` antes do push.

## Alternativas consideradas

- **Tipo de plano opcional** (primeira versão desta ADR, mesmo dia): mantinha a categoria no editar, na importação e na transferência. Superada pela decisão do dono de tirar o campo de vez.
- **Apagar `Categoria`, `PrecoCategoria`, `PlanoCompra` e `PlanoEspecial`**: recusada; nada de negócio se apaga, e as locações antigas apontam para eles.
- **Esconder a categoria na API mas continuar gravando** (por exemplo, uma categoria "Moto" e uma "Carro" criadas sozinhas): mantém o `NOT NULL`, mas guarda um dado que ninguém lê e que pode voltar a ser usado por engano. Recusada.
- **Default `moto` no model**: facilita testes e seed, mas esconde carro sem tipo. Recusada.
- **Rotas antigas com 410 por uma versão**: só serve para cliente de fora, que não existe; o frontend sobe junto. Recusada.

## Consequências

- Moto ou carro tem uma fonte só, o veículo. Não há mais coerência a conferir entre veículo e categoria.
- O preço de cada veículo é preenchido na tela dele, desde o primeiro dia; o veículo novo fica fora da Nova locação até ter um plano ligado (ponto em aberto 1).
- O assistente perde um passo, e o funil da plataforma perde uma etapa; a empresa que estava parada nela anda sozinha na migração.
- `Categoria`, `PrecoCategoria`, `PlanoCompra`, `PlanoEspecial` e `Veiculo.categoria` ficam como dado antigo, lidos só pelas locações de antes da ADR 0041.
- A reversa da `0014` só funciona antes do primeiro veículo novo.
- `modelo-de-dados.md` passa a ter `tipo_veiculo` no Veículo, a categoria como dado antigo e a seção Categoria como guardada sem uso.

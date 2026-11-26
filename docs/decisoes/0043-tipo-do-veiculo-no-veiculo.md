# Tipo do veículo no próprio veículo e tipo de plano opcional

**Status:** aceita · 26 nov 2026 · T-522 (regras: `VEI-01`, `VEI-04`, `VEI-11`, `VEI-12`, `VEI-15`, `IMP-02`, `IMP-08`, `CLI-02`, `VIS-01`, `FIL-04`; decisão do dono de 26 nov 2026; regras no PR do Produto da T-522) · **substitui em parte a 0041** (o "a categoria vira só tipo" do item sobre `Categoria`: o moto ou carro sai dela como fonte do veículo) · detalha a 0011 e a 0015

## Contexto

Até aqui o veículo não tinha tipo próprio. `Veiculo.categoria` é FK obrigatória (`PROTECT`) para `veiculos.Categoria`, que a tela chama de "Tipo de plano" (T-507), e o moto ou carro do veículo é `veiculo.categoria.tipo_veiculo` (`VEI-11`, decisão de 05 nov 2026, "para os dois nunca discordarem"). Esse tipo decide a CNH exigida (`CLI-02`), os itens da vistoria (`VIS-01`), os filtros Moto e Carro da Frota e da Nova locação, o ícone e os textos "desta moto" ou "deste carro".

A decisão do dono de 26 nov 2026:

1. O "Tipo de plano" sai do cadastro do veículo. Cadastro novo não pede nem grava tipo de plano.
2. O veículo pode ficar sem tipo de plano.
3. Moto ou carro passa a ser dado do próprio veículo.
4. O editar e a importação (`IMP-08`) mantêm o tipo de plano, opcional.
5. O seletor "Moto ou carro" passa a se chamar **"Veículo"**, no cadastro, no editar e onde mais o rótulo aparecer.

É caro de desfazer porque muda uma coluna de um model central, migra todos os veículos de todas as empresas e troca a fonte de uma informação lida por seis apps.

## Decisão

### 1. Modelo: `Veiculo.tipo_veiculo` e `Veiculo.categoria` nula

| Campo | Antes | Depois |
| --- | --- | --- |
| `tipo_veiculo` | não existe (lido de `categoria.tipo_veiculo`) | `CharField(max_length=10, choices=TipoVeiculo.choices)`, obrigatório, **sem default no model** |
| `categoria` | FK → `Categoria`, obrigatória, `PROTECT` | FK → `Categoria`, `null=True, blank=True`, `PROTECT` |

- `TipoVeiculo` é o enum que já existe em `veiculos.models` (`moto`, `carro`). Não se cria outro.
- **Sem default no model**: um default `moto` faria um carro esquecido virar moto em silêncio, e a CNH (`CLI-02`) é conferida por ele. Quem cria veículo informa o tipo; a falta é erro de validação.
- `CheckConstraint` `veiculo_tipo_valido`: `tipo_veiculo IN ('moto', 'carro')`.
- **Coerência com a categoria**: com `categoria` preenchida, `categoria.tipo_veiculo == veiculo.tipo_veiculo`. Não dá para ser constraint (é entre tabelas); é conferida no serviço de domínio, em todo caminho que grava `categoria` ou `tipo_veiculo` (cadastro, editar, importação, transferência), e por um teste de varredura (item 7). `Categoria.tipo_veiculo` continua travado com veículos na categoria (`editar_categoria`, `categoria_com_veiculos`), o que mantém a coerência pelo outro lado.
- Índice: `(filial, tipo_veiculo)` para os filtros da Frota e da Nova locação e as contagens por tipo. O índice de `categoria` fica.
- `Categoria` não muda: nome, `tipo_veiculo`, `filial`, `ativo`, e o `PrecoCategoria` como modelo de preço (ADR 0041). Ela continua precisando do moto ou carro para filtrar a lista do editar e da importação.
- Nada se apaga: a categoria dos veículos que existem fica.

### 2. Migração

Duas migrações em `veiculos`, depois da `0013_excluido`:

**`0014_tipo_do_veiculo` (esquema)**

1. `AddField("veiculo", "tipo_veiculo", CharField(..., default="moto"), preserve_default=False)`: o default só existe para preencher a coluna nas linhas que já estão lá; o model fica sem default.
2. `AlterField("veiculo", "categoria", ForeignKey(..., null=True, blank=True, on_delete=PROTECT))`.
3. `AddConstraint` `veiculo_tipo_valido` e `AddIndex` `(filial, tipo_veiculo)`.

**`0015_tipo_pela_categoria` (dados, `RunPython`)**

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

- **`.using(schema_editor.connection.alias)`**, como a `0010_copiar_precos_da_categoria`: a empresa nova é migrada pela conexão do papel de migração, no schema dela (ADR 0040, `plataforma.banco.criar_schema`). A `default` aponta para outro schema e não tem a tabela.
- **`_base_manager`**: o veículo excluído (`VEI-22`) e os `vendido` e `baixado` também recebem o tipo; o manager padrão pode filtrar o excluído.
- Todos nascem `moto` pelo passo 1 da `0014`; a `0015` só corrige os de categoria de carro. Um `UPDATE` por empresa, sem laço em Python.
- **Idempotente**: rodar de novo dá o mesmo resultado.
- **Na criação de empresa nova** a migração roda (o schema novo passa por todas as migrações) e não acha veículo: nada é alterado e nada quebra. Teste explícito (item 7).
- O `update()` aqui não fere a regra de status por serviço: `tipo_veiculo` não é status, e a migração não gera evento de auditoria, como a `0010` (dado copiado, nada que a pessoa fez).
- **Reversa**: `RunPython.noop` na `0015`. A reversa da `0014` volta `categoria` a obrigatória, e só funciona enquanto nenhum veículo ficou sem categoria. Isso é aceito: depois do primeiro cadastro novo, voltar exige escolher categoria para cada veículo, decisão de produto e não de migração.
- **Seed**: `seed/frota.py` e os outros que criam `Veiculo` passam o `tipo_veiculo` explicitamente (igual ao da categoria). A Moto Rápida não muda nenhum número de `dados-de-teste.md`.

### 3. Quem passa a ler o tipo do veículo no lugar da categoria

Levantado no código da `origin/develop` de 26 nov 2026 (`1be376d2`). Toda leitura de `veiculo.categoria.tipo_veiculo` ou `categoria__tipo_veiculo` vira `veiculo.tipo_veiculo` ou `tipo_veiculo`. Sem isso, um veículo sem categoria quebra com `AttributeError` em `None`.

| App | Onde | O que lê | Regra |
| --- | --- | --- | --- |
| `veiculos` | `selectors.do_tipo` | filtro Moto ou Carro da Frota e da Nova locação (`categoria__tipo_veiculo`) | `VEI-11` |
| `veiculos` | `selectors.contagens` | contagem por tipo das abas da Frota (`values_list("categoria__tipo_veiculo")`) | `VEI-11` |
| `veiculos` | `selectors` ficha e lista (`"tipo_veiculo": veiculo.categoria.tipo_veiculo`, `"categoria": {...}`) | campo `tipo_veiculo` e `categoria` da resposta | `VEI-11` |
| `veiculos` | `services.editar` | troca de tipo com locação aberta (409 `tipo_com_locacao_aberta`) e os campos da auditoria | `VEI-11`, `AUD-01` |
| `veiculos` | `services.categoria_no_destino`, `transferir` | tipo de plano no destino da transferência | `VEI-04`, `FIL-04` |
| `veiculos` | `services` linha do texto "deste carro" ou "desta moto" (`veiculo.categoria.tipo_veiculo == CARRO`) | textos | `VEI-15` |
| `veiculos` | `exclusao.py` (`é moto?`) | texto da exclusão | `VEI-22` |
| `veiculos` | `services.aplicar_modelo_de_preco`, `planos_do_modelo` | modelo de preço do cadastro e da importação | `VEI-12` |
| `veiculos` | `selectors` ficha (`precos_vigentes({veiculo.categoria_id})`) e `api/views` lista (`{v.categoria_id for v in pagina}`) | `preco_vigente` da categoria na resposta | ADR 0041 |
| `locacoes` | `services` (rascunho e confirmação, linha 331; troca de veículo, linha 1563) | CNH exigida | `CLI-02`, `LOC-09` |
| `locacoes` | `selectors` (linha 476, `"tipo"` do veículo; linha 905, impedimentos da CNH) | tipo na resposta e CNH | `CLI-02` |
| `locacoes` | `services` plano especial (linha 1545, `veiculo.categoria_id in categorias`) | plano especial restrito a tipos de plano | `LOC-01` |
| `vistorias` | `services.ITENS_PADRAO[veiculo.categoria.tipo_veiculo]` (linha 135), CNH (linha 361) | itens da vistoria e CNH | `VIS-01`, `CLI-02` |
| `vistorias` | `selectors` linha 95 | CNH na vistoria | `CLI-02` |
| `clientes` | `selectors` (função da CNH, recebe `tipo_veiculo: str`) | nada muda: quem chama passa `veiculo.tipo_veiculo` | `CLI-02` |
| `importacao` | `linhas`, `selectors`, `services`, `api/serializers` | categoria da linha e do modelo; tipo do veículo importado | `IMP-02`, `IMP-08` |
| `movimentacoes` | `services._categoria_destino` (`veiculo.categoria.filial_id`), `api/serializers` | tipo de plano no destino | `VEI-04`, `MOV` |
| `relatorios` | `configuracoes.resumo_precos`, `selectors.categorias_ativas` | contagem de tipos de plano | não muda (não lê o veículo) |
| `auditoria` | `retrato(veiculo)` | passa a ter `tipo_veiculo`; `categoria_id` pode ser `null` | `AUD-01` |
| `vendas` | `veiculos.services.receber_na_troca` (veículo recebido na troca, `VEI-07`, fase 2 da ADR 0042) | `dados` do cadastro: passa a exigir `tipo_veiculo` | `VEN-05` |

Os `select_related("categoria")` que existem só para ler o tipo (locações, vistorias, movimentações, views de veículos) saem ou ficam conforme o resto da função ainda use a categoria; com FK nula o `select_related` continua valendo (LEFT JOIN).

**O que não muda:** `Categoria` e os endpoints de tipo de plano (`/api/categorias/`, preços da categoria, histórico), `PrecoCategoria`, `PlanoCompra` antigo e `PlanoEspecial` (ADR 0041), as locações já gravadas (o preço é do veículo e congelado, `LOC-15`), os contratos (`cliente.cnh_categoria` é a categoria da CNH, não a do veículo), `relatorios`, `financeiro`.

### 4. Contrato da API (`docs/api/veiculos.md`, `docs/api/importacao.md`, `docs/api/movimentacoes.md`)

**`POST /api/veiculos/` (cadastro)**

- `tipo_veiculo` (`moto` | `carro`) **obrigatório**. Sem ele: 400 `{"tipo_veiculo": ["Escolha moto ou carro."]}`.
- `categoria_id` sai dos obrigatórios. Continua aceito, opcional e nulo (o mesmo serviço serve a importação e a troca na venda); a tela de cadastro não manda. Com valor, precisa ser ativa, da empresa ou da filial (`FIL-04`) e do mesmo tipo (item 5).
- Sem `categoria_id`, o veículo nasce com os planos `diaria`, `semanal` e `mensal` com R$ 0,00 e desligados, regras com dia de atraso e multa mínima R$ 0,00 e custos vazios, pelo mesmo `aplicar_modelo_de_preco` com o modelo vazio (`ModeloDePreco(0, 0, 0, None, None)`, que já existe para categoria sem preço). Status em que nasce: ver item 6.
- O cadastro pelo CRLV-e (`cadastrar_com_crlv`) e o `validar_novo` da importação seguem as mesmas regras.

**`PATCH /api/veiculos/{id}/` (editar)**

- Aceita `tipo_veiculo` e `categoria_id` (nulo = tirar o tipo de plano). Os dois se gravam juntos, num só evento `veiculo.editar`.
- O tipo vem de `tipo_veiculo`, não mais da categoria. Item 5 para as combinações.

**Ficha (`GET /api/veiculos/{id}/`) e lista (`GET /api/veiculos/`)**

- `tipo_veiculo`: lido do veículo. Não muda de forma.
- `categoria`: `{id, nome}` **ou `null`** (`IdNomeSerializer(allow_null=True)`).
- `preco_vigente` da categoria (ADR 0041, informativo): `null` sem categoria.
- Filtro `?tipo_veiculo=` e `?categoria=` continuam; `?categoria=` não traz veículo sem categoria.

**Transferência (Movimentações, `docs/api/movimentacoes.md`; o serviço é `veiculos.services.transferir`)**

- `categoria_destino_id`: opcional e nulo. Item 5.
- `Movimentacao.categoria_destino` já é nula; o `CHECK mov_categoria_so_na_transferencia` não muda.

**Importação (`docs/api/importacao.md`)**

- A linha guarda `_tipo_veiculo` ao lado de `_categoria_id` (`linhas.py`), e as duas seguem o modelo (marca e modelo) ou são exceção da linha (`_categoria_propria` passa a cobrir o par).
- `POST /api/importacoes/{id}/categorias/` (escolha por modelo) recebe `[{marca, modelo, tipo_veiculo, categoria_id}]`, com `categoria_id` nulo aceito e do mesmo tipo quando preenchido. O nome da rota fica (mudar quebra o cliente gerado sem ganho).
- O bloco `categorias` da importação devolve, por modelo, `tipo_veiculo` e `categoria_id` (nulo); `pergunta` passa a ser sempre `true` na importação de veículos (o Veículo sempre se escolhe), e as `opcoes` levam o `tipo_veiculo` de cada tipo de plano (já levam).
- "Importar" trava só com linha a gravar sem `tipo_veiculo` (`faltam_categorias` vira `faltam_tipos`; o código de erro `categoria_do_modelo` passa a `tipo_do_modelo`, "Escolha o veículo de cada modelo.").
- Sai o 422 `sem_categoria` do começo da importação: sem tipo de plano cadastrado, importa do mesmo jeito.
- Correção da linha ("Corrigir aqui"): aceita `tipo_veiculo` além de `categoria_id`.
- A categoria escolhida que for desativada no meio do caminho continua gerando o erro da linha.

**OpenAPI**: muda (`categoria` nulo na ficha e na lista, `tipo_veiculo` obrigatório no cadastro, campos novos na importação). Quem muda roda `npm run api:gerar`, `npm run typecheck` e conserta no mesmo PR o que deixar de compilar no frontend (`tarefas/README.md`).

### 5. Combinações de tipo e tipo de plano (editar, importação, transferência)

A regra é uma só, no serviço `veiculos.services._tipo_e_categoria(tipo, categoria_id, filial_id, erros)`, usado pelo cadastro, pelo editar, pela importação e pela transferência:

| Recebe | Resultado |
| --- | --- |
| tipo de plano do mesmo tipo do veículo | grava |
| tipo de plano de **outro** tipo | **400 no campo** `categoria_id`: "Escolha um tipo de plano de moto." (ou "de carro"). O veículo **não** troca de tipo sozinho, e a categoria não é tirada em silêncio. |
| `categoria_id: null` | tira o tipo de plano; planos e status não mudam |
| troca de `tipo_veiculo` com o tipo de plano atual do tipo antigo e sem mandar `categoria_id` | 400 no campo `categoria_id`: a mesma frase. A tela já esvazia o tipo de plano ao trocar o Veículo (`VEI-11`), então manda `categoria_id: null` ou um do tipo novo. |
| troca de `tipo_veiculo` com locação aberta | 409 `tipo_com_locacao_aberta`, como hoje, conferido **antes** da coerência (a frase da dica é a mesma) |

Por que recusar em vez de seguir a categoria: até aqui a API recebia só a categoria e o tipo vinha dela. Agora o tipo é dado do veículo e decide a CNH; deixar uma categoria de carro transformar uma moto em carro é exatamente o efeito escondido que a decisão do dono quer tirar. A tela evita o caso; a API garante.

Trocar ou tirar o tipo de plano não aplica modelo de preço nem mexe nos planos (já é assim depois do cadastro, `VEI-11`) e é livre em qualquer estado em que o veículo se edita. Auditoria: o evento `veiculo.editar` leva `tipo_veiculo` e `categoria_id` de antes e depois pelo `retrato`, e `categoria_nome` (nulo quando sem tipo de plano).

**Transferência** (`categoria_no_destino`):

- veículo sem tipo de plano, ou com tipo de plano da empresa: passa direto, sem pergunta;
- tipo de plano só da filial de origem: a resposta de erro deixa de ser recusa. Sem `categoria_id`, o veículo fica sem tipo de plano no destino; com `categoria_id`, precisa ser ativa, do mesmo tipo, da empresa ou do destino (400 no campo, como hoje). A tela pergunta, com a opção "Sem tipo de plano".

### 6. Status do veículo cadastrado sem tipo de plano

Sem modelo de preço, o veículo nasce sem plano ligado. A `VEI-15` diz que veículo sem plano ligado é `indisponivel` "sem preço". O cadastro de hoje já tem o caso (categoria sem preço) e deixa o veículo `disponivel`, fora da Nova locação só porque não tem plano ligado.

**Padrão desta ADR**, combinado com o Produto (`pontos-em-aberto.md`, item da T-522): o cadastro sem plano ligado passa a nascer `indisponivel` com o motivo "sem preço", no próprio `_criar` (o histórico inicial fica `"" → indisponivel`), e o primeiro plano ligado na tela de preços leva a `disponivel` pelo caminho que já existe (`VEI-15`). Vale para todo cadastro sem plano ligado, com ou sem tipo de plano. Se o dono decidir o contrário (nascer `disponivel`), muda uma linha no `_criar` e um teste; nada do resto desta ADR depende disso.

### 7. Testes que a mudança pede

- `test_vei_11_tipo_e_do_veiculo`: veículo sem categoria tem tipo; Frota filtra e conta pelo tipo do veículo.
- `test_vei_11_categoria_de_outro_tipo_recusada` (editar, importação, transferência).
- `test_vei_11_trocar_tipo_com_locacao_aberta_409` (já existe; passa a mandar `tipo_veiculo`).
- `test_vei_01_cadastro_sem_tipo_de_plano` e `test_vei_01_cadastro_sem_tipo_veiculo_400`.
- `test_vei_15_cadastro_sem_plano_nasce_sem_preco` (item 6).
- `test_cli_02_cnh_pelo_tipo_do_veiculo` e `test_vis_01_itens_pelo_tipo_do_veiculo` com veículo **sem** categoria.
- `test_vei_04_transferencia_sem_tipo_de_plano`.
- `test_imp_08_veiculo_e_tipo_de_plano_por_modelo`, `test_imp_08_importa_sem_tipo_de_plano_cadastrado`.
- Migração: `test_t522_migracao_preenche_tipo_pela_categoria` (carros e motos, excluído incluído) e `test_t522_migracao_na_empresa_nova` (schema vazio, pela conexão da migração).
- Varredura: nenhum veículo do seed com `categoria.tipo_veiculo != tipo_veiculo`.

### 8. Rótulos (com o Produto, `VEI-11`)

- "Moto ou carro" → **"Veículo"** no cadastro e no editar (`SelectField rotulo`), obrigatório, com as opções Moto e Carro.
- Importação: "Tipo de plano de cada modelo" passa a "Veículo e tipo de plano de cada modelo", com as duas listas por modelo; "Tipo de plano desta linha" ganha o "Veículo desta linha".
- Ficha: a linha "Tipo de plano" mostra "Sem tipo de plano" quando vazio.
- Transferência: a opção vazia passa de "Manter a categoria atual" a "Sem tipo de plano" quando o tipo de plano é só da origem.
- Auditoria: a chave `tipo_veiculo` aparece como "veículo".

Os textos finais são os de `docs/regras/veiculos.md` e `implantacao.md`, no PR do Produto da T-522; se divergirem daqui, valem os das regras.

## Divisão em tarefas

Ordem: B1 → F1; B2 → F2. B1 e B2 podem correr em paralelo depois da migração de B1 mesclada (B2 depende do campo). F1 pode começar pelo contrato desta ADR com o falso da API.

| Tarefa | Agente | Depende de | O que entrega | Pronto quando |
| --- | --- | --- | --- | --- |
| **B1** · tipo no veículo | backend | regras do Produto da T-522 | itens 1, 2, 3 (todos os leitores menos `importacao`), 4 (cadastro, editar, ficha, lista, transferência e movimentações), 5, 6, 7; seed com `tipo_veiculo`; `docs/api/veiculos.md` e `movimentacoes.md`; OpenAPI regerado e o frontend compilando (`categoria?.nome` na ficha e no editar, falsos com `categoria: null` aceitos) | veículo sem categoria passa por Nova locação, confirmação com CNH, vistoria de saída e devolução, transferência; migração testada em empresa existente e nova; `make check` limpo |
| **B2** · importação | backend | B1 | item 4 da importação e item 5 na importação; `docs/api/importacao.md`; OpenAPI | Moto Rápida importa 86 veículos com e sem tipo de plano por modelo; `test_imp_08_*` |
| **F1** · cadastro, editar, ficha, transferência | frontend | B1 | cadastro sem o campo "Tipo de plano" e sem a prévia "Preços da categoria", com "Veículo"; editar com "Veículo" e "Tipo de plano" opcional ("Sem tipo de plano" na lista), esvaziando ao trocar o Veículo, travado com locação aberta como hoje; ficha com "Sem tipo de plano"; Nova movimentação com "Sem tipo de plano" no destino; capturas claro e escuro, 1440 e 390 px | testes dos componentes e o E2E do cadastro passando |
| **F2** · importação | frontend | B2 | `CaixaDeImportacao`: "Veículo e tipo de plano de cada modelo" e a exceção da linha com os dois campos | teste do assistente com uma importação sem tipo de plano |

Cuidado com conflito: o PR #691 (T-521, aberto) mexe no `NovoVeiculoForm`; F1 começa depois dele mesclado ou faz `merge origin/develop` antes do push.

## Alternativas consideradas

- **Manter o tipo só na categoria e criar uma categoria "sem plano" por tipo** (uma "Moto" e uma "Carro" escondidas): nenhuma migração de esquema, mas a categoria continua sendo o lugar do tipo, que é o que o dono tirou; a lista de tipos de plano ganharia itens que não são planos, e a importação, a transferência e a Administração teriam que esconder esses dois. Recusada.
- **`tipo_veiculo` no veículo e a categoria trocando o tipo junto** (como hoje, a categoria manda): mantém o "nunca discordam", mas o editar com uma categoria de carro viraria a moto em carro sem a pessoa mexer no Veículo. Recusada pelo item 5.
- **Default `moto` no model**: facilita os testes e o seed, mas esconde carro sem tipo. Recusada pelo item 1.
- **Migração em uma só (esquema e dados juntos)**: funciona no PostgreSQL nesta ordem, mas separar deixa a reversa e a leitura mais claras, como na ADR 0041.

## Consequências

- Moto ou carro tem uma fonte só, o veículo, e a categoria fica só como agrupador de preço, opcional.
- A coerência veículo e categoria deixa de ser estrutural e passa a ser regra do serviço, coberta por teste e pela trava que já existe em `editar_categoria`.
- Veículo sem tipo de plano não entra em plano especial restrito a tipos de plano (`PlanoEspecial.categorias`); só nos "para todos". Plano de compra antigo da categoria não muda.
- A reversa da `0014` só funciona antes do primeiro veículo sem categoria.
- `modelo-de-dados.md` (Veículo) passa a ter `tipo_veiculo` e `categoria` nula.

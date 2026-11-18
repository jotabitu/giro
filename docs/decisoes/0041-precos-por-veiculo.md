# Preços por veículo: planos, regras, custos e compra no app `veiculos`, a categoria como tipo e a migração da tabela

**Status:** aceita · 18 nov 2026 · T-492 (regras: `VEI-12` a `VEI-17`, `LOC-01`, `LOC-03`, `LOC-04`, `LOC-10`, `LOC-15`, `LOC-16`, tabela de transições do veículo; decisão do dono de 18 nov 2026; regras no PR #612, T-491) · detalha a 0011, a 0012 e a 0015 · **substitui em parte a 0037** (item 2 inteiro e a origem do valor no item 1) · vale com os padrões dos 11 pontos em aberto da T-491 e as decisões do dono de 18 nov 2026 sobre esta ADR (multa mínima própria, aviso de tabela não preenchida, preço agendado)

## Contexto

Até aqui o preço era da categoria: `veiculos.Categoria` (com `filial` nula ou preenchida, a "tabela da filial", `FIL-04`), `veiculos.PrecoCategoria` com vigência (`LOC-15`), `locacoes.PlanoEspecial` (preço fixo ou desconto, `LOC-01`) e `locacoes.PlanoCompra` por categoria (ADR 0037). A locação lê o preço por `veiculos.selectors.preco_vigente(categoria, data)` em quatro pontos de `locacoes.services` (rascunho, confirmação, renovação, troca) e um de `locacoes.selectors`.

A decisão do dono de 18 nov 2026 leva o preço para cada veículo: planos de aluguel do veículo, regras do veículo (km excedente, dia de atraso, desconto sem aprovação, prazo da caução), custos e margem, um plano de compra por veículo com juros e a simulação na API, e o histórico de preços do veículo. A categoria vira "Tipo de veículo". Quatro pontos são caros de desfazer: onde moram os models (e quem importa quem), o que acontece com as tabelas antigas, a migração sem perder dado nem mudar locação confirmada, e onde mora o cálculo.

## Decisão

### 1. Os models ficam em `veiculos`, e a ordem dos apps não muda

Os cinco models novos são de `veiculos` (nível 6 da ADR 0011). Nenhum deles importa app acima:

- `veiculos` não importa `locacoes` nem `financeiro`. As formas de pagamento aceitas viram um enum próprio de `veiculos` (`FormaAceita`, mesmos valores do `locacoes.FormaPagamento`); `locacoes` confere que a forma escolhida está em `formas_aceitas`.
- O "pago na moto" precisa das despesas do veículo (`FIN-17`), que são de `financeiro` (nível 8). Vem pelo registro de leituras da ADR 0015: `financeiro.leituras` registra `despesas_do_veiculo(veiculo_id) -> int` (soma sem as `recusada`), e `veiculos` lê pelo registro, como já faz com `indicadores_financeiros`. Sem o registro (testes de `veiculos` isolados), a soma é 0.
- A margem mínima (ponto em aberto, padrão A) é `empresas.ConfiguracaoEmpresa.margem_minima_pct` (pct, nulo; nulo = a faixa nunca fica amarela). `empresas` está abaixo de `veiculos`.
- `locacoes` (10) passa a ler o preço por `veiculos.selectors` e a guardar FK para `veiculos.PlanoVeiculo` e `veiculos.PlanoCompraVeiculo` (sentido permitido).

Todos herdam `ModeloBase`. Tipos como em `modelo-de-dados.md` (`centavos`, `pct` = `Decimal(5,2)`).

#### `veiculos.PlanoVeiculo` · ativável (`VEI-12`)

| Campo | Tipo | Observação |
| --- | --- | --- |
| `veiculo` | FK → `Veiculo` | `related_name="planos"` |
| `tipo` | enum `diaria`, `semanal`, `mensal`, `entregador`, `outro` | |
| `nome` | texto(40), vazio | obrigatório só no `outro` |
| `periodo` | enum `dia`, `semana`, `mes` | fixo pelo tipo nos três primeiros; escolhido no `entregador` e no `outro` |
| `ligado` | bool, padrão `false` | desligado não aparece na Nova locação |
| `valor_centavos` | centavos, padrão 0 | por período |
| `como_paga` | enum `tudo_na_retirada`, `semana_adiantado`, `mes_uma_parcela`, `mes_duas_quinzenais`, `mes_quatro_semanais` | lista fechada por período |
| `formas_aceitas` | `ArrayField` de enum `FormaAceita` (`pix`, `boleto`, `cartao`, `dinheiro`) | |
| `caucao_centavos` | centavos, nulo | nulo = não preenchida; R$ 0,00 é válido |
| `caucao_parcelas` | smallint, padrão 1, `CHECK 1..12` | 1 = à vista |
| `franquia_km` | int, nulo, `CHECK > 0` | nulo = livre |
| `prazo_minimo_periodos` | smallint, nulo, `CHECK > 0` | nulo = sem mínimo |
| `valor_agendado_centavos` | centavos, nulo | preço com vigência futura (decisão do dono de 18 nov 2026, item 4) |
| `caucao_agendada_centavos` | centavos, nulo | caução que entra junto; nula = a caução não muda |
| `agendado_para` | data, nula | dia em que o agendado passa a valer (data local da filial) |

- **Preço agendado: um por plano, em campos, sem tabela de vigências.** A tela agenda um valor por vez ("R$ 329,00 a partir de 01 out"); uma tabela de vigências daria a mesma resposta com mais junções em toda leitura. `CHECK`: `agendado_para` nula ↔ `valor_agendado_centavos` nulo e `caucao_agendada_centavos` nula; `agendado_para` só se grava no futuro (serviço). Agendar de novo substitui o anterior, com histórico.
- **Como entra na data: leitura por data, com consolidação pelo Celery Beat.** Quem lê o preço pergunta pelo dia: `valor_em(dia)` = `valor_agendado_centavos` se `agendado_para <= dia`, senão `valor_centavos` (o mesmo para a caução). Assim a confirmação, a renovação e a troca de um dia qualquer pegam o preço certo mesmo que a rotina atrase, e o `LOC-15` continua igual: a locação congela o valor do dia da confirmação, e o agendado nunca muda locação confirmada. A rotina `veiculos.consolidar_precos_agendados`, diária às 00:05 por schema (ADR 0012), passa o agendado vencido para `valor_centavos`/`caucao_centavos`, limpa os três campos e grava histórico (`origem = agendamento`, `por` nulo) e auditoria do Sistema. Ela é idempotente e só arruma a tabela; a regra é a leitura por data.

- `CHECK` do período: `diaria` ↔ `dia`, `semanal` ↔ `semana`, `mensal` ↔ `mes`; `como_paga` compatível com o `periodo` (`dia` só `tudo_na_retirada`, `semana` só `semana_adiantado`, `mes` um dos três `mes_*`).
- `CHECK` do ligar: `ligado` exige `valor_centavos > 0`, `cardinality(formas_aceitas) >= 1` e `caucao_centavos IS NOT NULL`. O serviço recusa antes, no campo (400), com o texto da `VEI-12`; o `CHECK` é a rede.
- `CHECK`: `tipo = 'outro'` exige `nome <> ''`; nos outros tipos, `nome = ''`.
- Únicos parciais: `(veiculo, tipo)` com `ativo AND tipo <> 'outro'`; `(veiculo, Lower(nome))` com `ativo AND tipo = 'outro'`. Plano `outro` retirado vira `ativo = false` (nada se apaga); os outros tipos não se retiram, só se desligam.
- Índice parcial `(veiculo)` com `ativo AND ligado` (a Nova locação e o "sem preço").

#### `veiculos.RegrasVeiculo` · um por veículo (`VEI-14`)

| Campo | Tipo | Observação |
| --- | --- | --- |
| `veiculo` | `OneToOneField` → `Veiculo` | `related_name="regras"` |
| `km_excedente_centavos` | centavos, padrão 0 | por km; só guardado (ponto em aberto, padrão B) |
| `dia_atraso_centavos` | centavos, padrão 0 | o valor da `LOC-10` |
| `multa_minima_centavos` | centavos, padrão 0 | mínimo da multa da devolução antecipada (`LOC-12`), separado do dia de atraso |
| `desconto_sem_aprovacao_pct` | pct, padrão 5.00, `CHECK 0..100` | o limite da `LOC-03` e da `APR-01` |
| `prazo_devolucao_caucao_dias` | smallint, nulo | nulo = sem prazo (padrão A) |

#### `veiculos.CustosVeiculo` · um por veículo (`VEI-13`)

| Campo | Tipo | Observação |
| --- | --- | --- |
| `veiculo` | `OneToOneField` → `Veiculo` | `related_name="custos"` |
| `manutencao_mes_centavos`, `seguro_mes_centavos`, `rastreador_mes_centavos` | centavos, padrão 0 | por mês |
| `ipva_ano_centavos` | centavos, padrão 0 | digitado pelo ano; entra ÷ 12 no cálculo |
| `revenda_estimada_centavos` | centavos, nulo | "Revenda estimada em 24 meses" (padrão A); nulo = sem desvalorização |
| `ocupacao_esperada_pct` | pct, nulo, `CHECK 0..100` | nulo = margem não calculada ("Informe a ocupação") |

- O **valor de venda** não é campo novo: é o `Veiculo.valor_venda_centavos` que já existe (`VEN-01`). O **pago na moto** não se grava: é `Veiculo.valor_compra_centavos` + `despesas_do_veiculo` na hora da leitura.

#### `veiculos.PlanoCompraVeiculo` · um por veículo (`VEI-16`, detalha a `LOC-16`)

| Campo | Tipo | Observação |
| --- | --- | --- |
| `veiculo` | `OneToOneField` → `Veiculo` | `related_name="plano_compra"` |
| `ligado` | bool, padrão `false` | |
| `periodicidade` | enum `diaria`, `semanal`, `quinzenal`, `mensal` | quinzenal a cada 14 dias (padrão A) |
| `parcelas` | smallint, `CHECK 2..1000` | 730 diárias cabem |
| `entrada_centavos` | centavos, padrão 0 | menor que o valor de venda (serviço) |
| `juros_mes_pct` | pct, padrão 0.00, `CHECK >= 0` | no modo `digitar`, o achado pela bisseção, com 2 casas |
| `modo` | enum `calcular`, `digitar` | |
| `parcela_moto_centavos` | centavos | sempre gravada: no `calcular`, o PMT arredondado (`ROUND_HALF_UP`); no `digitar`, o digitado |
| `adicional_centavos` | centavos, padrão 0 | por parcela |
| `caucao_centavos` | centavos, padrão 0 | abatida da última parcela (padrão A) |

- `CHECK`: `ligado` exige `parcela_moto_centavos > 0`. "Ligar exige valor de venda" e "entrada menor que a venda" estão em duas tabelas: ficam no serviço (400 no campo).
- A parcela do cliente (`parcela_moto + adicional`) não se grava: é soma.

#### `veiculos.HistoricoPrecoVeiculo` · imutável (`VEI-17`)

| Campo | Tipo | Observação |
| --- | --- | --- |
| `veiculo` | FK → `Veiculo` | |
| `em` | momento | relógio do domínio |
| `por` | FK → `Usuario`, nulo | nulo = Sistema ou migração |
| `origem` | enum `tela_precos`, `ficha`, `cadastro`, `importacao`, `migracao`, `agendamento` | |
| `alvo` | enum `plano`, `regras`, `custos`, `plano_compra`, `valor_venda` | |
| `alvo_id` | bigint, nulo | o `PlanoVeiculo` mudado |
| `alvo_nome` | texto(60) | "Semanal", "Entregador", nome do `outro` (copiado) |
| `campo` | texto(40) | `valor_centavos`, `ligado`, `juros_mes_pct` |
| `de`, `para` | json, nulo | o valor cru (centavos, pct em texto, bool) |
| `lote` | UUID | as linhas de uma mesma gravação |

- Uma linha por campo mudado; índice `(veiculo, em)`. Só o serviço escreve; não há update nem delete.
- Junto, um `EventoAuditoria` por gravação (não por campo), categoria operação, com o `lote`, pelo mecanismo de sempre (`AUD-01`). No juro acima de 1% ao mês, o evento leva `juros_confirmados: {pct, por, em}` (item 4).

### 2. A categoria vira "Tipo de veículo"; as tabelas antigas ficam paradas, não apagadas

- **`veiculos.Categoria` não muda de nome no código nem de tabela.** Trocar o model mexeria nas FKs de `Veiculo`, `TransferenciaVeiculo`, `PlanoEspecial`, `PlanoCompra`, importação e assistente, sem ganho. Muda o `verbose_name` ("tipo de veículo"), os textos da API e das telas, e o papel: guarda `nome` e `tipo_veiculo` (moto ou carro, padrão A do ponto em aberto; `VEI-11`, `CLI-02` e `VIS-01` não mudam). O campo do veículo continua `categoria`; o contrato expõe `tipo_de_veiculo` como apelido só nos serializers novos.
- **`Categoria.filial` (a tabela da filial)** fica na tabela, sem leitura de preço. As categorias por filial continuam valendo como tipo (e na regra `IMP-08`); juntar categorias de mesmo nome entre filiais é decisão de "Preços da frota", não desta ADR.
- **`PrecoCategoria`** não se apaga (as locações antigas guardam `precos_de`, e "nada de negócio é apagado"). Deixa de ser lido por `locacoes`, pela ficha e pela Frota. A tela antiga `Precos` fica só na Administração, com aviso, e continua gravando nela; o único uso do valor dali é de **modelo de preço**: o cadastro, a importação e o assistente (passo 8) pré-preenchem os planos do veículo novo com o preço vigente da categoria escolhida, por `veiculos.services.planos_do_modelo(categoria)`, na criação do veículo e só nela. A tela do veículo não aplica modelo.
- **`locacoes.PlanoCompra`** para de receber cadastro: `POST`/`PUT` respondem 410 com `{"codigo": "VEI-16", "mensagem": "O plano de compra agora é de cada veículo. Use Planos e preços do veículo."}`; o `GET` continua (as locações antigas apontam para ele). A FK `Locacao.plano_compra` fica.
- **`locacoes.PlanoEspecial`** some da `LOC-01` nova: a Nova locação não oferece mais plano especial (o "Entregador" virou tipo de plano do veículo). O model e a FK `Locacao.plano_especial` ficam para as locações antigas; cadastro novo responde 410 como o `PlanoCompra`. As regras do PR #612 não dizem se o plano especial de preço fixo deve virar plano `entregador` dos veículos na migração; **a migração não o converte** (decisão do dono de 18 nov 2026): o veículo que fica sem plano ligado mostra o aviso de tabela não preenchida (item 4).

#### O que deixa de valer na ADR 0037

- **Item 2 inteiro** (`locacoes.PlanoCompra` por categoria, cadastrado em `Precos`): substituído pelo `PlanoCompraVeiculo` do item 1 acima.
- **Item 1, a origem do valor e da caução:** o valor vem do plano do veículo, e a caução é a do plano de compra do veículo, não a da categoria. Os campos congelados da `Locacao` continuam e ganham os do item 5 abaixo. O `CHECK` muda: `intencao_compra` exige `plano_compra` **ou** `plano_compra_veiculo` (as antigas têm o primeiro, as novas o segundo).
- **Item 1, `periodicidade`:** o enum de `Locacao.periodicidade` ganha `quinzenal`, usado só na compra (a comum continua com diária, semanal e mensal).
- Continuam valendo os itens 3 a 6 (contrato `locacao_compra`, quitação por evento, `Venda` da quitação, tarefa da transferência), a caução abatida só na última parcela com a sobra devolvida (CA-420-14, padrão A) e o `if` único do tipo.

### 3. Migração de dados idempotente e a ordem das migrations

Ordem (cada passo roda por schema no `migrate_schemas`; nenhuma migration de `veiculos` depende de `locacoes`):

1. **`veiculos` 0009 (schema):** cria os cinco models e o enum. Nada é removido.
2. **`empresas` 00NN (schema):** `ConfiguracaoEmpresa.margem_minima_pct` nulo.
3. **`veiculos` 0010 (dados, `RunPython`, reversa = `noop`):** para cada `Veiculo` sem `RegrasVeiculo`:
   - acha o `PrecoCategoria` vigente da categoria na data de hoje em `America/Sao_Paulo` (a migration não tem o relógio do domínio; usa `timezone.now()`, e o `GIRO_DATA_REFERENCIA` não vale aqui);
   - cria `PlanoVeiculo` `diaria`, `semanal` e `mensal` com o valor da categoria, `caucao_centavos` da categoria, `caucao_parcelas = 1`, `como_paga` padrão do período (`tudo_na_retirada`, `semana_adiantado`, `mes_uma_parcela`), `formas_aceitas` = as quatro, franquia livre, sem prazo mínimo e `ligado = valor > 0`;
   - o primeiro `PrecoCategoria` com `vigente_desde` no futuro vira o agendado de cada plano (`valor_agendado_centavos`, `caucao_agendada_centavos`, `agendado_para = vigente_desde`); um segundo preço futuro, se houver, não cabe (um agendado por plano) e a migration o lista;
   - cria `RegrasVeiculo` com `dia_atraso_centavos` e `multa_minima_centavos` = diária da categoria, 5.00, km excedente 0 e prazo nulo; cria `CustosVeiculo` vazio;
   - grava `HistoricoPrecoVeiculo` com `origem = migracao`, `por` nulo, um `lote` por veículo;
   - **idempotência:** a chave é "o veículo já tem `RegrasVeiculo`"; o `get_or_create` por `(veiculo, tipo)` protege uma rodada interrompida no meio. Rodar de novo não duplica nem sobrescreve o que a locadora já editou.
   - Categoria sem preço vigente (nem futuro): os planos nascem desligados com valor 0, e o veículo fica com o aviso de tabela não preenchida (item 4). Só com preço futuro: os planos nascem desligados com o agendado preenchido, e o comando do passo 6 os liga no dia, pela consolidação.
4. **`locacoes` 00NN (dados, `RunPython`, depende da `veiculos` 0010):** copia o `PlanoCompra` ativo mais recente de cada categoria para o `PlanoCompraVeiculo` de cada veículo dela que ainda não tem um: desligado, `modo = digitar`, `parcela_moto_centavos` = `valor_parcela_centavos`, periodicidade e parcelas do antigo, entrada 0, adicional 0, caução = a da categoria (padrão A); imprime os outros planos da categoria que não foram. Escreve num model de `veiculos` de dentro de uma migration de `locacoes`: é a única exceção ao "só por serviço", porque migration não chama serviço e a dependência vai no sentido permitido.
5. **`locacoes` 00NN+1 (schema):** campos novos da `Locacao` (item 5), `quinzenal` no enum, o `CHECK` novo do tipo. Todos nulos ou com padrão: as locações confirmadas não mudam (`LOC-15`); `valor_periodo_centavos`, `diaria_centavos`, `caucao_centavos`, `compra_*` e `precos_de` delas ficam como estão.
6. **Depois do `migrate_schemas`, comando `alinhar_veiculos_sem_preco`** (idempotente, no deploy e no `make seed`): pelo serviço do item 4, leva a `indisponivel` "sem preço" os veículos `disponivel` sem plano ligado, com histórico de status e auditoria do Sistema. Fica fora da migration porque a mudança de status só sai por serviço e gera evento (padrão do repositório).

Nenhum campo de preço é removido nesta leva. Tirar `PrecoCategoria`, `PlanoCompra` e `PlanoEspecial` do banco, se um dia for o caso, pede outra ADR.

### 4. API e serviço de domínio

**Onde mora o cálculo:** `veiculos/precos.py`, módulo puro (sem banco, sem Django), com `Decimal` nas contas intermediárias e `ROUND_HALF_UP` só na parcela gravada e na exibição (ADR 0009): `custo_mes`, `receita_mes`, `margem`, `meses_do_prazo`, `taxa_periodo`, `pmt`, `juros_por_bissecao` (0 a 20% ao mês, tolerância de meio centavo na parcela, até 100 iterações), `simular_compra` e `simular(entrada) -> Resultado`. Os casos da descrição do dono e da `dados-de-teste.md` viram testes dele (`test_vei_16_pop_semanal_104`, `test_vei_16_digitar_170_acha_1_46`, `test_vei_16_cg_venda_abaixo_do_pago`), com o "recebe pela moto" pela parcela arredondada (padrão A: Pop R$ 17.768,96).

**Serviço:** `veiculos.services.salvar_precos(veiculo, dados, por, origem, confirmar_juros=False)`, numa transação, com `select_for_update` no veículo:

1. valida (400 no campo; textos da `VEI-12` e da `VEI-16`);
2. chama `precos.simular` com os dados novos; com `juros_mes_pct > 1.00` (no `calcular` o digitado, no `digitar` o achado) e o plano de compra ligado e com juros mudados desde a última gravação, sem `confirmar_juros` responde 409 `{"codigo": "VEI-16", "mensagem": "<texto da VEI-16>", "juros_mes_pct": "1.46"}`;
3. grava os models, compara campo a campo e grava o `HistoricoPrecoVeiculo` e um `EventoAuditoria`;
4. chama `_alinhar_status_sem_preco(veiculo)` (abaixo).

**Sem preço (`VEI-15`):** `tem_plano_ligado(veiculo)` = algum `PlanoVeiculo` ativo e ligado ou o `PlanoCompraVeiculo` ligado. A constante `MOTIVO_SEM_PRECO = "Sem preço · ligue um plano"` vai em `motivo_status`.

- `disponivel` e sem plano → `transicionar(veiculo, INDISPONIVEL, origem=MANUAL, motivo=MOTIVO_SEM_PRECO, acao="sem_preco")` na mesma transação.
- `indisponivel` com `motivo_status == MOTIVO_SEM_PRECO` e com plano → `disponivel`. Outro motivo (bloqueio, documento vencido) não volta sozinho.
- **Aviso de tabela não preenchida** (decisão do dono de 18 nov 2026; `VEI-15`, `LOC-09`, `VEN-01`): não é status. `veiculos.selectors` anota `tem_plano_ligado` (`Exists` no índice parcial) na Frota, nas listas e na ficha, e o serializer devolve `aviso_preco: "A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda."` ou `null`, em qualquer status. Três ações recusam o veículo sem plano ligado com 409 `{"codigo": "VEI-15", "mensagem": <o aviso>}`: entrar na Nova locação (rascunho e confirmação), ser o veículo novo da troca (`LOC-09`, sem plano ligado **do mesmo tipo** do contratado) e "Colocar à venda" (`veiculos.services.colocar_a_venda`, `VEN-01`). A lista de veículos da Nova locação já os tira pelo filtro.
- `reservado`, `alugado` ou `em_manutencao`: o status fica, o aviso aparece. Na volta, `veiculos.services.transicionar(..., DISPONIVEL)` passa a conferir `tem_plano_ligado`: sem plano, o destino vira `INDISPONIVEL` com o motivo. A conferência fica dentro de `transicionar`, num lugar só, e cobre todos os caminhos que devolvem o veículo à frota (devolução, fim de manutenção, chegada de movimentação). A tabela de transições já tem `alugado` → `indisponivel`; as outras origens (`em_manutencao`, `em_movimentacao`) já permitem `indisponivel`.

**Rotas** (em `apps/veiculos/api`, sob o recurso do veículo; contrato em `docs/api/veiculos.md`, seção "Preços", escrito pelo backend na primeira tarefa a partir daqui):

| Rota | Quem | O que faz |
| --- | --- | --- |
| `GET /api/veiculos/{id}/precos/` | quem vê o veículo na filial | planos (ativos), regras, plano de compra e os resultados calculados (margem por plano, resultado da compra, parcela nas 4 periodicidades, alertas). `custos`, `pago_na_moto`, lucro e margem só para administrador, gerente e financeiro (`VEEM_CUSTO`); para os outros a chave não vem. Traz `ocupacao_real_90d_pct` (`VEI-06`), `fipe_centavos`, `margem_minima_pct` e `pode_editar` |
| `PUT /api/veiculos/{id}/precos/` | administrador | substitui o documento inteiro (`valor_venda_centavos`, `custos`, `planos[]` com `id` nulo para `outro` novo e `ativo: false` para retirar, `regras`, `plano_compra`) e `confirmar_juros`; devolve o mesmo corpo do `GET` |
| `POST /api/veiculos/{id}/precos/simular/` | quem pode editar | o mesmo corpo do `PUT`, sem gravar; devolve os resultados e `pede_confirmacao_juros`. Segue a ADR 0005 (`POST .../simular/`) |
| `POST /api/veiculos/{id}/precos/planos/{plano_id}/ligado/` | administrador | `{ "ligado": false }`, o liga e desliga do cartão da ficha, com o mesmo serviço (histórico, auditoria, sem preço) |

- Erros de negócio com código: `VEI-12` (ligar sem valor, forma ou caução; prazo mínimo), `VEI-15` (renovar ou criar com plano desligado), `VEI-16` (409 dos juros; venda ausente; parcela menor que financiado ÷ `n`). O suporte Giro recebe 403 `PLT-07`. Gerente recebe 403 no `PUT` (padrão A de "quem edita").
- A tela não calcula: o `simular` é chamado a cada mudança, com debounce no frontend.

**Como a nova locação lê o preço.** `veiculos.selectors` ganha a interface para os outros apps, no lugar de `preco_vigente`:

- `planos_para_locacao(veiculo, dia) -> list[PrecoDoPlano]` (só ativos e ligados) e `plano_para_locacao(veiculo, plano_id, dia) -> PrecoDoPlano` (levanta `ErroDeRegra("VEI-15")` se desligado);
- `PrecoDoPlano` é um `dataclass(frozen=True)` com `plano_id`, `tipo`, `nome`, `periodo`, `valor_centavos`, `como_paga`, `formas_aceitas`, `caucao_centavos`, `caucao_parcelas`, `franquia_km`, `prazo_minimo_periodos`, com valor e caução já resolvidos para o dia pedido (`valor_em(dia)`, item 1), mais as regras do veículo (`dia_atraso_centavos`, `multa_minima_centavos`, `desconto_sem_aprovacao_pct`, `km_excedente_centavos`, `prazo_devolucao_caucao_dias`);
- `plano_compra_para_locacao(veiculo) -> PrecoDaCompra` (parcela do cliente, parcelas, periodicidade, entrada, caução, valor de venda, juros).

`locacoes` deixa de receber `periodicidade` e `plano_especial` no rascunho e passa a receber `plano_veiculo_id` (comum) ou nada além do veículo (compra). A `periodicidade` da locação sai do `periodo` do plano, e `parcelamento_mensal` do `como_paga` (`mes_quatro_semanais` → `quatro_semanais`; `mes_duas_quinzenais` é valor novo do enum). A Nova locação lista veículos com `tem_plano_ligado` (só com compra ligada: aparece só no tipo compra).

### 5. Campos congelados da locação (`LOC-15`)

`locacoes.Locacao` ganha, todos nulos ou com padrão, preenchidos na confirmação e nunca mais mudados por mudança de preço:

| Campo | Tipo | De onde |
| --- | --- | --- |
| `plano_veiculo` | FK → `veiculos.PlanoVeiculo`, nulo | só referência; o valor está nos campos |
| `plano_compra_veiculo` | FK → `veiculos.PlanoCompraVeiculo`, nulo | compra nova |
| `caucao_parcelas` | smallint, padrão 1 | `LOC-04` |
| `franquia_km` | int, nulo | `VEI-12` |
| `km_excedente_centavos` | centavos, padrão 0 | guardado para a tarefa da cobrança (padrão B) |
| `desconto_sem_aprovacao_pct` | pct, nulo | `LOC-03`; nulo nas antigas = 5.00 |
| `multa_minima_centavos` | centavos, nulo | `LOC-12`; nulo nas antigas = `diaria_centavos` (o comportamento de antes) |
| `prazo_devolucao_caucao_dias` | smallint, nulo | `DEV-02` |
| `compra_entrada_centavos`, `compra_adicional_centavos` | centavos, nulo | `LOC-16` |
| `compra_valor_venda_centavos` | centavos, nulo | `VEI-16` |
| `compra_juros_mes_pct` | pct, nulo | `VEI-16` |

- `valor_periodo_centavos` = valor do plano; `caucao_centavos` = caução do plano; `diaria_centavos` passa a guardar o **dia de atraso** do veículo (base só da `LOC-10`; a multa mínima tem o campo próprio acima); `compra_valor_parcela_centavos` = parcela do cliente; `precos_de` = data da confirmação.
- Renovação (`LOC-08`) usa o plano do mesmo `plano_veiculo`, com o valor novo; desligado ou retirado, 409 `VEI-15`.

## Pontos em aberto da T-491: os padrões adotados

Todos adotados como estão. Os que mexem no desenho:

- **Datas das parcelas divididas e caução parcelada (A):** a caução em `caucao_parcelas > 1` vira várias contas de caução no `financeiro`, a 1ª na retirada e as outras junto com os próximos vencimentos do aluguel. Muda a geração de contas de `locacoes` (hoje uma conta de caução) e o acerto da devolução (`DEV-02` soma as contas de caução pagas). O `mes_duas_quinzenais` é um terceiro valor do `parcelamento_mensal`.
- **Quinzenal 14 dias (A):** só no plano de compra; o calendário da `LOC-05` ganha o passo de 14 dias.
- **Revenda (A), margem mínima (A):** campos novos nos itens 1 (`CustosVeiculo`, `ConfiguracaoEmpresa`).
- **Plano de compra na migração (A), valores iniciais (A):** passo 3 e 4 da migração.
- **Km excedente (B):** só o campo, sem linha no acerto. Se o dono escolher A, entra em `devolucoes` sem mudar model (os campos já estão congelados na locação).
- **Caução "das últimas parcelas" (A), arredondamento (A), quem edita (A), tipo guarda moto ou carro (A):** sem efeito no desenho além do já dito. A escolha B da caução mudaria só a geração das parcelas e a quitação, não os models.

## Consequências

- A ordem dos apps não muda. `veiculos` ganha uma leitura registrada de `financeiro` (ADR 0015) e cinco tabelas.
- `preco_vigente` e `precos_vigentes` saem da interface de `veiculos` para os outros apps; ficam só para a tela antiga e o "modelo de preço" do cadastro.
- O assistente de implantação (passo 8, tabela de preços) continua gravando `PrecoCategoria`, agora como modelo para os veículos que vierem depois; os veículos importados no passo 11 recebem os planos do modelo.
- O seed Moto Rápida cria os planos, regras, custos e o plano de compra dos veículos com os números da `dados-de-teste.md` (TBC-5H21, QXA-4B21) e roda o `alinhar_veiculos_sem_preco`.

### Riscos

1. **Empresas com plano especial em uso** (Entregador) perdem a oferta na Nova locação até cadastrar o plano `entregador` nos veículos; o aviso da tabela não preenchida só aparece se o veículo ficar sem nenhum plano ligado. Avisar as empresas em produção (giro.ceo) antes do deploy da tarefa 2.
2. **Segundo preço futuro da categoria** não cabe no agendado único do plano; a migration lista os casos. Raro (a tela antiga agenda um por vez).
3. **Rotina de consolidação parada** não erra preço (a leitura é por data), mas deixa o agendado vencido na tela de edição: a tela mostra o valor efetivo pela API, nunca o campo cru.
4. **`transicionar` com a conferência do sem preço** muda o destino de todo caminho que devolve o veículo. Os testes de devolução, manutenção e movimentação precisam de veículo com plano ligado no `factory`.

## Divisão das tarefas seguintes (rascunho; o orquestrador decide números e ordem)

1. **Backend: preços do veículo** (`veiculos`, `empresas`, `financeiro.leituras`): models (com o preço agendado e a multa mínima), migrations 1 a 3 (com o agendado vindo do preço futuro), `precos.py` com os casos de teste, `salvar_precos`, sem preço em `transicionar`, `aviso_preco` na leitura do veículo, 409 `VEI-15` no "Colocar à venda" (`VEN-01`), rotina `consolidar_precos_agendados` no Beat, rotas do item 4, `docs/api/veiculos.md`, OpenAPI. Regras `VEI-12` a `VEI-17`.
2. **Backend: locação lê o plano do veículo** (`locacoes`, `financeiro`): migrations 4 e 5, interface `planos_para_locacao`, rascunho, confirmação, renovação e troca lendo `valor_em(dia)` e recusando sem plano ligado (troca: do mesmo tipo, `LOC-09`), `LOC-03`, `LOC-12` pela multa mínima congelada, `LOC-04` (caução parcelada), `LOC-10`, `LOC-16` pelo `PlanoCompraVeiculo`, quinzenal e `mes_duas_quinzenais` no calendário; 410 no cadastro de `PlanoCompra` e `PlanoEspecial`; comando `alinhar_veiculos_sem_preco` e seed. Depende da 1.
3. **Design system + frontend: tela e componente** (`/veiculos/[id]/precos` e "Preços desta moto" na ficha), sobre o contrato da 1, com o `simular` e o 409 dos juros. Pode começar com o contrato escrito, antes do merge da 1.
4. **Frontend: Nova locação e cadastro** (planos do veículo na Nova locação, "Tipo de veículo" no cadastro, editar e importação, a tela antiga `Precos` só na Administração com aviso). Depende da 2.
5. **Desvinculação da tabela antiga** (backend e frontend): tirar `preco_vigente` da ficha, da Frota, da importação e do assistente (no lugar, `planos_do_modelo`), conferir com `grep` que nada de locação lê `PrecoCategoria`, `PlanoCompra` ou `PlanoEspecial`; QA com os casos da `dados-de-teste.md`. Fecha a decisão.

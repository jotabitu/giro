# app `veiculos`

**Schema:** empresa
**Escopo:** Categorias e tabela de preços, veículos, documentos, leitura de km, histórico de status.
**Regras:** VEI (ver `docs/regras-de-negocio.md`)
**Telas:** Frota, Veiculo, Precos (ver `docs/telas/README.md`)

## Estrutura esperada

```
veiculos/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/veiculos.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-013)

- `models.py`:
  - `Categoria`, com nome único por filial sem diferenciar maiúsculas; `filial` nula vale para a empresa toda;
  - `PrecoCategoria`, com uma vigência por data (`LOC-15`);
  - `Extra` (`LOC-02`);
  - `Veiculo`, uma máquina de estados (`TRANSICOES_VEICULO`, `REGRA_TRANSICAO = "transicao_veiculo"`). Placa e chassi são únicos em qualquer estado, e o banco tem um `CHECK` de 17 caracteres no chassi;
  - os apoios `HistoricoStatusVeiculo`, `LeituraKm` e `TransferenciaVeiculo`, com a origem genérica (`origem_tipo`, `origem_id`, `origem_codigo`).
- `services.py`:
  - `transicionar`, o único caminho para mudar o status. Ela grava o histórico e a auditoria, e devolve ou ocupa a vaga do plano ao entrar em `vendido` ou `baixado` ou sair deles;
  - as ações `bloquear`, `desbloquear`, `colocar_a_venda`, `voltar_para_frota` e `baixar`;
  - `cadastrar` (`VEI-01`, `PLT-03`), `editar` e `corrigir_identificacao`;
  - `receber_na_troca` (`VEI-07`) e `transferir` (`VEI-04`);
  - `atualizar_km`, `corrigir_km` e `pedir_correcao_km`, que abre o pedido `APR-06` pela porta `comum.aprovacoes` (ADR 0019);
  - categorias, preços (`criar_preco`, `trocar_preco_futuro`) e extras.
- `selectors.py`:
  - `preco_vigente(categoria, data)`;
  - a representação, com `acoes` e `situacao`, e a lista com as contagens das abas;
  - `ocupacao` do veículo e `ocupacao_da_frota` da filial (`VEI-06`);
  - as categorias e o histórico de preços.
- `api/`: as rotas de `docs/api/veiculos.md`, menos documentos e exportação.

## Implementado (T-079)

- `DocumentoVeiculo` (`VEI-03`): um ativo por tipo; renovar deixa o anterior `ativo=False`. O `arquivo` fica no armazenamento privado de `comum.arquivos` (`AUD-05`).
- `services.enviar_documento`, `situacao_do_documento` (no dia da validade já é `vencido`) e a recusa 422 `VEI-03` do `desbloquear` com CRLV ou seguro ativo vencido.
- `services.aplicar_vencimento_de_documentos` e a tarefa `aut_06_vencimento_de_documentos` (Beat às 07:00, uma por empresa):
  - 30 dias antes, alerta no sino dos gerentes da filial (`FIL-02`), uma vez por documento, e o evento `veiculos.documento_vencendo`;
  - no dia, CRLV ou seguro: `disponivel` vai para `indisponivel` ("Seguro vencido"), com a origem `documento`; `alugado`, `reservado` e `em_manutencao` não mudam, e os gerentes recebem uma tarefa urgente (T-085).
- `selectors.resumos_de_documentos` (o `documentos_resumo` da ficha e da lista) e `representacao_documento`, com a URL assinada nova a cada leitura.
- `selectors.ve_valores` e `sem_valores` (D-25, `USR-09`): o vistoriador recebe frota, ficha e categorias sem `_centavos` nem blocos de preço, aplicado depois do serializer; preços e extras respondem 403 a ele.
- Rotas: `GET` e `POST /api/veiculos/{id}/documentos/` (multipart) e `GET .../documentos/historico/`.

## Implementado (T-083)

- `transferir` pede `categoria_id` quando a categoria atual é só da filial de origem (`VEI-04`, `FIL-04`): uma categoria ativa, do mesmo tipo, da empresa ou do destino. Categoria da empresa passa direto. A `TransferenciaVeiculo` guarda `categoria_origem` e `categoria_destino`.

## Para os outros apps

- Para mudar o status: `services.transicionar(veiculo, "alugado", origem=services.OrigemDaMudanca("locacao", id, "LOC-2856"))`. Transição fora da tabela: 409 `transicao_veiculo`, com `detalhes = {de, para}`.
- Vistoria e OS gravam o km por `services.atualizar_km(veiculo, km, origem=...)`. Km menor responde 422 `VEI-01`.
- Para o preço numa data, use `selectors.preco_vigente(categoria, data)`. A locação copia o preço na assinatura (`LOC-15`).
- Blocos da representação (ADR 0015), no alvo `"veiculos.Veiculo"`: `locacao_atual`, `manutencao` e `indicadores_financeiros`. O `documentos_resumo` vem do próprio app (T-079). Cada bloco pode ter `alerta: {codigo?, rotulo, tom}`, e o de maior gravidade vira a `situacao`. O `indicadores_financeiros` só sai na ficha para administrador, gerente e financeiro (`VEEM_CUSTO`); para os demais a chave fica ausente (`USR-09`, T-156).
- `locacoes` registra o contador `("veiculos.Categoria", "locacoes_em_andamento")`, que a resposta de preço novo mostra em `locacoes_em_andamento_mantidas`.

## Fornecido a outros apps

- Para o plano (`PLT-03`): `registrar_contador("veiculos", ...)`, que conta os veículos fora de `vendido` e `baixado`.
- Para as filiais: o contador `veiculos` da operação que impede desativar (`FIL-06`) e os `indicadores` `veiculos` e `ocupacao_pct`.

## Eventos publicados

| Evento | Dados |
| --- | --- |
| `veiculos.km_atualizado` | `veiculo_id`, `km` (cada leitura e correção, para `MAN-03`) |
| `veiculos.documento_vencendo` | `documento_id`, `veiculo_id`, `tipo`, `validade` (alerta de 30 dias, `AUT-06`) |

Assina `aprovacoes.pedido_decidido` em `eventos.py` (T-081): `APR-06` aprovado chama `services.aplicar_correcao_aprovada`, que corrige o km como o gerente faria, com a aprovação como origem da leitura. Se o km mudou depois do pedido, responde 409 `km_mudou` e a aprovação volta.

## Catálogo de marcas e modelos (T-257)

- `catalogo.py`: lê `dados/catalogo_modelos.csv` uma vez por processo (`modelos()`, com `cache`); `listar` para `GET /api/veiculos/modelos/` e `achar_modelo` para a leitura do CRLV-e (`VEI-08`, ADR 0026, item 7). Sem tabela nem migração.
- `management/commands/atualizar_catalogo_modelos.py`: regrava o CSV a partir da tabela FIPE baixada pela equipe, sem duplicata e em ordem. Nada consulta a internet.

## Falta

- O e-mail ao gerente da `AUT-06` entra com o contrato de notificações; hoje o aviso é só no sino.
- A exportação (`AUD-07`) e a recusa `VEN-10` do `voltar-para-frota` entram com os apps delas.

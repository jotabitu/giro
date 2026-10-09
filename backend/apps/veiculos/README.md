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

## Para os outros apps

- Para mudar o status: `services.transicionar(veiculo, "alugado", origem=services.OrigemDaMudanca("locacao", id, "LOC-2856"))`. Transição fora da tabela: 409 `transicao_veiculo`, com `detalhes = {de, para}`.
- Vistoria e OS gravam o km por `services.atualizar_km(veiculo, km, origem=...)`. Km menor responde 422 `VEI-01`.
- Para o preço numa data, use `selectors.preco_vigente(categoria, data)`. A locação copia o preço na assinatura (`LOC-15`).
- Blocos da representação (ADR 0015), no alvo `"veiculos.Veiculo"`: `locacao_atual`, `manutencao`, `indicadores_financeiros` e `documentos_resumo`. Cada bloco pode ter `alerta: {codigo?, rotulo, tom}`, e o de maior gravidade vira a `situacao`.
- `locacoes` registra o contador `("veiculos.Categoria", "locacoes_em_andamento")`, que a resposta de preço novo mostra em `locacoes_em_andamento_mantidas`.

## Fornecido a outros apps

- Para o plano (`PLT-03`): `registrar_contador("veiculos", ...)`, que conta os veículos fora de `vendido` e `baixado`.
- Para as filiais: o contador `veiculos` da operação que impede desativar (`FIL-06`) e os `indicadores` `veiculos` e `ocupacao_pct`.

## Eventos publicados

| Evento | Dados |
| --- | --- |
| `veiculos.km_atualizado` | `veiculo_id`, `km` (cada leitura e correção, para `MAN-03`) |

Assina `aprovacoes.pedido_decidido` em `eventos.py` (T-081): `APR-06` aprovado chama `services.aplicar_correcao_aprovada`, que corrige o km como o gerente faria, com a aprovação como origem da leitura. Se o km mudou depois do pedido, responde 409 `km_mudou` e a aprovação volta.

## Falta

- Documentos, arquivo privado e `AUT-06` ficam para a T-079. Com eles entra a recusa `VEI-03` do `desbloquear`.
- A exportação (`AUD-07`) e a recusa `VEN-10` do `voltar-para-frota` entram com os apps delas.

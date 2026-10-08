# Pedido de aprovação aberto por uma porta em `comum`

**Status:** aceita · 09 out 2026 · detalha a 0011 (T-080)

## Contexto

Os pedidos de aprovação nascem nos módulos de origem (`APR-01` a `APR-06`), e o app `aprovacoes` guarda e decide (`docs/api/aprovacoes.md`). A volta já está resolvida pela ADR 0011: `aprovacoes` publica `aprovacoes.pedido_decidido` e o app da origem aplica o efeito na mesma transação. Faltava a ida.

Pela ordem da 0011, `aprovacoes` está no nível 7. `financeiro` (8), `manutencao` (9), `locacoes` (10) e `vendas` (12) ficam abaixo dele e poderiam chamar `aprovacoes.services`. Já `clientes` e `veiculos` (nível 6) ficam acima e não podem importar `aprovacoes`. Mesmo assim, os dois abrem pedidos: desbloqueio de cliente pedido pelo vendedor (`APR-05`) e correção de km para baixo pedida pelo vistoriador (`APR-06`, CA-013-16).

Um evento não serve para a ida, porque `comum.eventos.publicar` não devolve valor. O vistoriador precisa receber, na mesma resposta, o 202 com o `id` do pedido (`docs/api/veiculos.md`).

## Decisão

### 1. Uma porta em `comum`, registrada por `aprovacoes`

`comum/aprovacoes.py` define a única forma de abrir, consultar e cancelar pedidos a partir de outro app. Segue o mesmo padrão de `comum.permissoes.registrar_pode` e `comum.empresa.registrar_exige_2fa_todos`: `comum` declara a função, e o app de baixo registra a implementação no `AppConfig.ready()`.

```python
@dataclass(frozen=True)
class PedidoRef:
    id: int
    tipo: str        # "APR-01" a "APR-06"
    status: str      # "pendente" (na criação)

def pedir(*, tipo: str, origem_tipo: str, origem_id: int, origem_codigo: str | None,
          filial_id: int, solicitante, titulo: str, detalhe: str,
          motivo: str | None = None, valor_centavos: int | None = None,
          pct: Decimal | None = None, dados: dict | None = None) -> PedidoRef: ...

def pendente(*, tipo: str, origem_tipo: str, origem_id: int) -> PedidoRef | None: ...

def cancelar_pendentes(*, origem_tipo: str, origem_id: int, motivo: str) -> int: ...
```

- `aprovacoes.apps.AprovacoesConfig.ready()` registra `aprovacoes.services.pedir`, `selectors.pendente` e `services.cancelar_pendentes` com `comum.aprovacoes.registrar(...)`.
- Sem implementação registrada, `pedir` levanta `RuntimeError`, e o erro aparece na hora. Não existe valor padrão em silêncio, porque um pedido perdido liberaria uma ação que precisava de aprovação.
- A origem é a genérica da 0011: `origem_tipo` (enum fechado, já com `veiculo` e `cliente`), `origem_id` e `origem_codigo` copiado (ex.: `SAK1D39`, `LOC-2836`).
- `filial_id` é a filial da origem (veículo, locação, venda, despesa, OS, caixa). Cliente é da empresa, sem filial: no `APR-05`, vale a filial da requisição de quem pediu (`filial_da_requisicao`). É por ela que o gerente vê e decide o pedido.
- `titulo` e `detalhe` são textos prontos que o app da origem monta, porque `aprovacoes` não conhece a origem. Ex.: "Correção de km para baixo" e "SAK1D39 · 3.500 → 3.400 km · Erro de digitação". Ficam gravados no pedido.
- `dados` guarda o que a origem precisa para aplicar o efeito na aprovação, sem a origem ter de guardar estado pendente. Ex. do `APR-06`: `{ "km_novo": 3400, "km_anterior": 3500 }`. Pode ter só chaves fixas por `tipo` e nunca dado pessoal ou sensível (vai para a auditoria, ADR 0014).
- `pedir` roda na transação de quem chama, grava o evento de auditoria (`APR-10`) e agenda o aviso ao gerente com `on_commit` (ADR 0011, item 3).
- Um só `pendente` por `(tipo, origem_tipo, origem_id)` (restrição do modelo). Um pedido repetido levanta `PedidoPendente`, que a API responde com 409 `{ "codigo": "pedido_pendente", "mensagem": "Já existe um pedido aguardando o gerente", "detalhes": { "pedido_id": 88 } }`.

### 2. O mesmo caminho para todos os apps de origem

`clientes`, `veiculos`, `financeiro`, `manutencao`, `locacoes` e `vendas` abrem pedidos **só** por `comum.aprovacoes.pedir`, inclusive os que a 0011 deixaria importar `aprovacoes.services`. Assim existe um caminho único, testado uma vez, e mudar a ordem dos apps não muda o fluxo. Ler a lista e decidir os pedidos continua sendo da API de `aprovacoes`.

O teste de limites (`tests/test_limites_entre_apps.py`) passa a recusar também `import aprovacoes` nesses seis apps. A exceção são os assinantes em `<app>/eventos.py`, que recebem o evento sem importar nada.

### 3. A volta continua por evento

`aprovacoes.pedido_decidido(pedido_id, tipo, status, origem_tipo, origem_id, dados, decidido_por_id, motivo)` é publicado na decisão (aprovar, recusar, cancelar). Cada app de origem tem um assinante em `<app>/eventos.py` que filtra pelo próprio `origem_tipo` e pelos tipos que abre, e aplica o efeito na mesma transação, chamando o próprio serviço (ex.: `veiculos.services.corrigir_km(..., aprovado_por=...)`). Se o assinante falhar, a decisão inteira volta.

### 4. A resposta 202

O endpoint da origem chama `pedir` dentro do próprio serviço e responde 202 com o `PedidoRef`:

```json
{ "pedido_aprovacao": { "id": 88, "tipo": "APR-06", "status": "pendente" } }
```

A origem não muda: o km continua 3.500 até a aprovação (CA-013-16). Quando a tela mostra que existe pedido em aberto, a representação da origem usa `comum.aprovacoes.pendente(...)`, ou uma anotação da 0015 quando for lista.

## Consequências

- `clientes` e `veiculos` abrem pedidos sem ferir a ordem da 0011, e os outros quatro apps usam o mesmo caminho.
- O `PedidoAprovacao` do modelo de dados ganha `filial` (FK, para "gerente decide pedidos das suas filiais"), `motivo_pedido`, `titulo` e `detalhe`, que o contrato já mostrava e o modelo não tinha.
- O app `aprovacoes` precisa existir com model, porta e `pedir` antes do primeiro app de origem que abre pedido, que é a T-013 (`APR-06`). Decidir pedidos (aprovar, recusar, cancelar e o evento) pode vir depois, numa tarefa própria.
- Testes obrigatórios:
  - `pedir` sem implementação registrada falha;
  - pedido repetido responde 409 `pedido_pendente`;
  - quem pediu não aprova (`APR-09`, `CHECK` no banco);
  - auditoria do pedido (`APR-10`);
  - teste de limites recusando `import aprovacoes` nos seis apps de origem.

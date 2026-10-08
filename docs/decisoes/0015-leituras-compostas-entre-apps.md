# Leituras compostas entre apps por registro de anotações

**Status:** aceita · 07 out 2026 · detalha a 0011

## Contexto

A ADR 0011 proíbe um app de importar de outro que esteja abaixo dele na ordem. Várias telas, porém, mostram numa lista do app de cima dados que pertencem aos de baixo: a `Frota` (app `veiculos`) mostra a locação atual e o cliente (`locacoes`) e a próxima revisão (`manutencao`); `Filiais` mostra veículos e locações por filial; `Clientes` mostra locação atual, total pago e valor em aberto (`locacoes`, `financeiro`). Fazer uma chamada por coluna no frontend é lento e espalha regra de exibição, e mandar tudo para `relatorios` tira a lista principal do app dono.

## Decisão

1. `comum/leituras.py` mantém um registro de **anotações de leitura**: `registrar_anotacao(alvo="veiculos.Veiculo", bloco="locacao_atual", anotar=func_queryset, montar=func_bloco)`.
   - `anotar(queryset) -> queryset` acrescenta `Subquery`/`annotate` (uma query para a lista inteira, sem N+1).
   - `montar(objeto) -> dict | None` monta o bloco JSON a partir das anotações.
2. O app de baixo registra suas anotações no `AppConfig.ready()`, em `<app>/leituras.py`. O app de cima só chama `comum.leituras.aplicar(alvo, queryset)` no selector e `comum.leituras.blocos(alvo, objeto)` no serializer; não importa nada do app de baixo.
3. O contrato do módulo dono da lista descreve cada bloco e diz qual app o fornece. Enquanto o app fornecedor não existe, o bloco vem `null`; o frontend trata `null` como "sem informação".
4. Um bloco pode trazer `alerta: { rotulo, tom }`. O serializer do app de cima usa o alerta de maior gravidade (`perigo` > `alerta` > `info`) para a `situacao` da linha, sem conhecer os status do outro app. Ex.: `locacoes` marca "Atrasado" (`perigo`) quando a locação atual está `devolucao_atrasada`.
5. Filtros e ordenação por campos de bloco só existem quando o contrato lista; o fornecedor registra também o filtro (`registrar_filtro(alvo, nome, func)`).
6. Anotação é só leitura. Escrever continua sendo por serviço e no sentido da ordem.

## Consequências

- As listas principais continuam no app dono, com uma chamada só.
- O teste de limites entre apps (0011) continua valendo: o registro passa por `comum`.
- Cada anotação tem teste de quantidade de queries (`django_assert_num_queries`) na lista.
- Os indicadores da tela `Filiais` (veículos, locações, ocupação) passam a usar este mecanismo, em vez de `GET /api/relatorios/filiais/` (ajustado em `docs/api/filiais.md`).

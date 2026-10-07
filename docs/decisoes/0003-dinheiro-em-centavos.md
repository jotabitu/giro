# Dinheiro em centavos inteiros

**Status:** aceita · 07 out 2026

## Contexto

Cálculos de parcelas, multas, comissões e DRE precisam bater ao centavo com os casos de referência.

## Decisão

Todo valor monetário é inteiro em centavos (`*_centavos`). Percentuais em `Decimal(5,2)`. Arredondamento só na exibição e, quando a regra dividir valores (parcelas), a diferença vai para a última parcela.

## Consequências

Sem erro de ponto flutuante; os testes comparam inteiros.

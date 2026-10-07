# Regras de negócio só na API

**Status:** aceita · 07 out 2026

## Contexto

Telas em desktop e celular, e no futuro portal do cliente e site de vendas.

## Decisão

Cálculos, mudanças de status e validações finais acontecem no backend, em `services.py`. O frontend exibe o que a API devolve e usa endpoints de simulação quando precisa mostrar um valor antes de salvar.

## Consequências

Uma só implementação de cada regra, testada uma vez. O frontend fica mais simples e depende do contrato da API.

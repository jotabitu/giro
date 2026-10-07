# Contrato da API antes do código

**Status:** aceita · 07 out 2026

## Contexto

Backend e frontend são agentes diferentes trabalhando em paralelo.

## Decisão

O arquiteto escreve `docs/api/<modulo>.md` antes do módulo começar. O backend publica o OpenAPI gerado; o frontend gera o cliente tipado a partir dele. O CI falha se o OpenAPI do repositório estiver desatualizado.

## Consequências

Menos retrabalho e menos mensagens entre agentes; o contrato vira o ponto de encontro.

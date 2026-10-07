# Monólito modular em Django

**Status:** aceita · 07 out 2026

## Contexto

Equipe pequena de agentes, muitos módulos que se cruzam (locação gera parcela, que gera comissão).

## Decisão

Um único projeto Django com um app por domínio em `backend/apps/`. Apps conversam só pela camada de serviços ou por eventos. Separar em serviços só se um módulo tiver carga muito diferente dos outros.

## Consequências

Deploy e testes simples; o Django Admin dá telas de apoio de graça. O custo é disciplina nos limites entre apps, que o arquiteto revisa.

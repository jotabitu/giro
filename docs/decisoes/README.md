# Decisões de arquitetura (ADRs)

Uma decisão por arquivo. Para mudar uma decisão, escreva uma nova ADR que substitui a anterior; não edite a antiga.

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-monolito-modular-django.md) | Monólito modular em Django | aceita |
| [0002](0002-multiempresa-schema-por-empresa.md) | Multiempresa com um schema por empresa (django-tenants) | aceita |
| [0003](0003-dinheiro-em-centavos.md) | Dinheiro em centavos inteiros | aceita |
| [0004](0004-white-label-por-tokens.md) | White label por tokens de cor e slot de logo | aceita |
| [0005](0005-regras-na-api.md) | Regras de negócio só na API | aceita |
| [0006](0006-contrato-de-api-primeiro.md) | Contrato da API antes do código | aceita |

| [0007](0007-pagamentos-asaas.md) | Pagamentos pelo Asaas, com subconta por locadora | aceita |

O modelo de dados detalhado fica em `modelo-de-dados.md` (tarefa T-006 do arquiteto).

Modelo para uma nova ADR: título, status e data, contexto, decisão, consequências.

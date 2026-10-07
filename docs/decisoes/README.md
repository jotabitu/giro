# Decisões de arquitetura (ADRs)

Uma decisão por arquivo. Para mudar uma decisão, escreva uma nova ADR que substitui a anterior; não edite a antiga.

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-monolito-modular-django.md) | Monólito modular em Django | aceita, detalhada pela 0011 |
| [0002](0002-multiempresa-schema-por-empresa.md) | Multiempresa com um schema por empresa (django-tenants) | aceita, detalhada pelas 0008 e 0012 |
| [0003](0003-dinheiro-em-centavos.md) | Dinheiro em centavos inteiros | aceita, complementada pela 0009 |
| [0004](0004-white-label-por-tokens.md) | White label por tokens de cor e slot de logo | aceita |
| [0005](0005-regras-na-api.md) | Regras de negócio só na API | aceita |
| [0006](0006-contrato-de-api-primeiro.md) | Contrato da API antes do código | aceita |
| [0007](0007-pagamentos-asaas.md) | Pagamentos pelo Asaas, com subconta por locadora | aceita |
| [0008](0008-usuarios-e-autenticacao-por-schema.md) | Usuários e autenticação por schema | aceita, complementada pela 0013 |
| [0009](0009-fundacao-comum.md) | Fundação comum dos models (`backend/comum/`) | aceita |
| [0010](0010-auditoria-imutavel.md) | Auditoria imutável em cada schema | aceita; item 7 substituído pela 0014 |
| [0011](0011-apps-e-limites.md) | Apps Django, dependências e comunicação entre apps | aceita (Admin fora de `TENANT_APPS` pela 0013) |
| [0012](0012-tarefas-celery-por-empresa.md) | Tarefas Celery por empresa | aceita |
| [0013](0013-endurecimento-da-autenticacao.md) | Endurecimento da autenticação (tokens, suporte, 2 etapas, Admin, cookie) | aceita, complementada pela 0014 |
| [0014](0014-sessoes-e-dados-sensiveis.md) | Sessões revogáveis e dados sensíveis (cifra, HMAC, auditoria) | aceita |
| [0015](0015-leituras-compostas-entre-apps.md) | Leituras compostas entre apps por registro de anotações | aceita |

O modelo de dados detalhado fica em [`modelo-de-dados.md`](modelo-de-dados.md).

Modelo para uma nova ADR: título, status e data, contexto, decisão, consequências.

## Revisão de 07 out 2026 (T-006)

As ADRs 0001 a 0007 continuam válidas. O que faltava foi coberto por ADRs novas, sem editar as antigas:

| ADR revisada | Ponto encontrado | Onde foi resolvido |
| --- | --- | --- |
| 0001 | "Serviços ou eventos" sem ordem de dependência entre apps; risco de import e migração circulares; contrato preso em `locacoes` | 0011 (ordem dos apps, origem genérica, eventos em processo, app `contratos`) |
| 0002 | Não dizia onde ficam os usuários, como o token se prende à empresa nem como o Celery entra no schema | 0008 e 0012 |
| 0003 | "Arredondamento só na exibição" não cobre percentuais que geram fração de centavo (desconto, multa, comissão, juros); faltava o tipo de campo para valores com sinal | 0009 (`ROUND_HALF_UP` no centavo, `CentavosField` e `CentavosComSinalField`) |
| 0004 | Sem lacunas. Os campos de marca ficam em `empresas.ConfiguracaoEmpresa` | modelo de dados |
| 0005 | Sem lacunas. Endpoints de simulação seguem `POST /api/<recurso>/simular/` | contratos de módulo |
| 0006 | Sem lacunas | — |
| 0007 | Não dizia onde fica a chave da subconta nem como o webhook encontra a empresa | modelo de dados: `plataforma.ContaPagamento` no `public` (id da subconta, chave cifrada, token do webhook); o webhook entra pelo `public` e só depois muda para o schema da empresa |
| README | A linha da 0007 estava fora da tabela (linha em branco no meio) | corrigido aqui |

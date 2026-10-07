# Documentação

| Documento | Para quê | Dono |
| --- | --- | --- |
| [regras-de-negocio.md](regras-de-negocio.md) | Estados, cálculos e regras com código (`LOC-07`). Fonte única. | produto |
| [plano.md](plano.md) | Visão, módulos, arquitetura, roadmap e riscos | produto |
| [design-system/](design-system/README.md) | Tokens, componentes e guia visual white label | design-system |
| [telas/](telas/README.md) | 123 telas de referência por módulo, com rota e regras | design-system |
| [marca/](marca/README.md) | Marca Giro e kit de logotipo | design-system |
| [decisoes/](decisoes/README.md) | ADRs e modelo de dados | arquiteto |
| [api/](api/README.md) | Contratos por módulo e OpenAPI gerado | arquiteto, backend |
| [agentes/](agentes/protocolo.md) | Protocolo entre agentes e montagem no Maestri | orquestrador |
| qa/ | Cobertura de regras por teste | qa |
| seguranca/ | Relatórios de revisão | seguranca |

Ordem de precedência quando dois documentos discordam: regras de negócio > decisões (ADRs) > contrato da API > telas > plano.

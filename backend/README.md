# Backend

Django 5 + Django REST Framework + django-tenants + Celery, sobre PostgreSQL 16 e Redis. Dono: agente **backend**. Leia `CLAUDE.md` e `.claude/agents/backend.md` antes de mexer aqui.

## Estrutura

```
backend/
├── config/            settings (base, dev, test, prod), urls, celery, asgi/wsgi
├── apps/              um app por domínio (tabela abaixo)
├── comum/             base de models (auditoria automática, códigos sequenciais, dinheiro), permissões, erros de negócio
├── integracoes/       interfaces + implementações falsas: pagamento, assinatura eletrônica, WhatsApp, NF-e, FIPE
├── templates/pdf/     modelos de contrato, recibo e termo (WeasyPrint)
├── seed/              empresa de exemplo Moto Rápida (agente qa)
└── tests/             testes transversais: isolamento entre empresas, permissões por perfil
```

## Apps

| App | Schema | Regras | Escopo |
| --- | --- | --- | --- |
| `plataforma` | public | PLT, IMP | Planos, empresas (tenants), faturas da assinatura, usuários da plataforma, acesso de suporte, implantações e chamados. |
| `contas` | empresa | USR | Usuários da empresa, perfis, permissões extras, filiais do usuário, convites, sessões, 2FA, login. |
| `empresas` | empresa | IMP | Dados da empresa, marca (cor, logo, nome), configurações gerais, assistente de implantação, integrações. |
| `filiais` | empresa | PLT-03 (limite) | Filiais, matriz, horário de funcionamento. |
| `veiculos` | empresa | VEI | Categorias e tabela de preços, veículos, documentos, leitura de km, histórico de status. |
| `clientes` | empresa | CLI, AUD-04, AUD-06 | Clientes PF/PJ, CNH, documentos, contatos, bloqueio, consentimento LGPD. |
| `locacoes` | empresa | LOC | Planos especiais, locações, reservas, contratos e modelos de contrato, renovação, cancelamento. |
| `vistorias` | empresa | VIS, DEV | Vistoria de saída e de devolução, fotos, avarias, acerto da devolução e da caução. |
| `vendas` | empresa | VEN | Propostas, funil, simulação de pagamento, troca, venda, recibo. |
| `aprovacoes` | empresa | APR | Pedidos de aprovação (desconto, cancelamento, despesa, correção de km), prazos e lembretes. |
| `financeiro` | empresa | FIN | Contas a receber (parcelas), despesas, caixa do dia, movimentos, conciliação bancária, comissões, DRE. |
| `manutencao` | empresa | MAN | Ordens de serviço, oficinas, preventivas por km e data. |
| `notificacoes` | empresa | AUT (canais) | Envio por WhatsApp, e-mail e push com a marca da locadora; preferências por pessoa; sino. |
| `automacoes` | empresa | AUT | Tarefas Celery AUT-01 a AUT-15, agendadas por empresa no fuso America/Sao_Paulo. |
| `auditoria` | empresa + public | AUD | Eventos imutáveis, exportação de dados, anonimização LGPD, retenção após cancelamento. |
| `relatorios` | empresa | FIN-13, relatórios | Indicadores das telas iniciais, relatórios e DRE (só leitura, a partir dos outros apps). |

A estrutura será criada na tarefa T-001. Os `README.md` de cada app já descrevem o escopo.

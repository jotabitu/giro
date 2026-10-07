# Giro: instruções para todos os agentes

Giro é um SaaS white label para locadoras e revendas de motos e carros: locação, venda, vistoria, financeiro, manutenção e a gestão da própria plataforma (empresas, planos, cobrança, suporte). Este arquivo vale para qualquer agente que trabalhe neste repositório, de qualquer função. As instruções da sua função ficam em `.claude/agents/<funcao>.md`.

## Leia antes de qualquer tarefa

1. `docs/regras-de-negocio.md`: é a fonte única da lógica de negócio. Regras têm código (`LOC-07`, `FIN-09`) e devem ser citadas em código, testes, commits e tarefas.
2. `tarefas/README.md`: como pegar, executar e entregar uma tarefa.
3. O trecho de `docs/telas/README.md` que cobre o módulo da sua tarefa, e as telas HTML citadas.
4. `docs/decisoes/`: decisões de arquitetura já tomadas. Não reabra uma decisão sem escrever uma nova ADR.

Se a tela e a regra discordarem, vale a regra. Se a regra não cobrir o caso, **não invente**: registre a dúvida em `tarefas/backlog.md` com a etiqueta `[decisão]` e avise o agente **produto**.

## Mapa do repositório

| Pasta | O que tem | Dono |
| --- | --- | --- |
| `docs/regras-de-negocio.md` | regras, estados, cálculos, dados de teste | produto |
| `docs/plano.md` | visão do produto, módulos, roadmap | produto |
| `docs/design-system/` | tokens, componentes, guia de uso, `wl-theme.css` | design-system |
| `docs/telas/` | 123 telas HTML de referência (desktop e celular) e o índice | design-system |
| `docs/marca/` | marca Giro e kit de logotipo | design-system |
| `docs/decisoes/` | ADRs | arquiteto |
| `docs/api/` | contrato da API (OpenAPI gerado) | backend |
| `docs/agentes/` | como os agentes colaboram e o layout no Maestri | orquestrador |
| `backend/` | Django 5 + DRF + django-tenants | backend |
| `frontend/` | Next.js + TypeScript + Tailwind + shadcn/ui | frontend |
| `infra/`, `.github/` | Docker, CI/CD, ambientes | devops |
| `tarefas/` | quadro de tarefas compartilhado | orquestrador |

## Stack

- **Backend:** Python 3.12, Django 5, Django REST Framework, django-tenants (um schema PostgreSQL por empresa), PostgreSQL 16, Celery + Redis (+ Celery Beat), drf-spectacular (OpenAPI), djangorestframework-simplejwt, django-otp (2FA), Argon2, WeasyPrint (PDF), armazenamento compatível com S3.
- **Frontend:** Next.js (App Router) + TypeScript estrito, Tailwind, shadcn/ui por cima dos tokens do design system, TanStack Query, cliente tipado gerado do OpenAPI, React Hook Form + Zod.
- **Infra:** Docker Compose no desenvolvimento, GitHub Actions, Sentry.

## Convenções que ninguém quebra

- **Multiempresa:** dado de negócio vive no schema da empresa. Nada consulta entre empresas. O painel da plataforma usa o schema público.
- **Dinheiro em centavos** (`valor_centavos: int`). Nunca `float`. Percentuais com 2 casas (`Decimal`).
- **Datas** em UTC no banco, exibidas em `America/Sao_Paulo`. Vencimento é data sem hora.
- **Status** com valores fechados (enum, conforme as regras). Mudança de status só por serviço de domínio (`services.py`), nunca por `update()` direto, e sempre gera evento de auditoria.
- **Nada de negócio é apagado.** Use `ativo=False` ou status cancelado. Registro financeiro pago só se corrige com estorno.
- **Códigos legíveis** sequenciais por empresa: `LOC-2856`, `VEN-0177`, `OS-118`, `FAT-2209`.
- **A API decide, a tela mostra.** O frontend nunca calcula valor, desconto, multa ou status por conta própria; ele exibe o que a API devolve.
- **Textos ao usuário** em português do Brasil, "você", frases curtas, sem emoji e sem exclamação. Use as palavras das telas ("devolução", não "check-in"; "caução", não "depósito").
- **White label:** dentro do sistema da locadora aparece a marca da locadora. A marca Giro só aparece no painel da plataforma, nas telas de compra, no assistente de implantação e no rodapé "Tecnologia Giro". Logo sempre por SVG, nunca texto digitado; nunca verde-limão sobre branco.
- **Dados de teste:** a empresa de exemplo Moto Rápida (seção "Dados de referência para testes" das regras) é o seed de desenvolvimento, e os cálculos têm que chegar exatamente naqueles números.

## Código

- Código, nomes de tabelas, campos e variáveis em português sem acento quando forem conceitos do negócio (`locacao`, `valor_centavos`, `devolver_caucao`); termos técnicos em inglês quando forem do framework (`serializer`, `viewset`, `hook`).
- Commits no formato `tipo(modulo): descrição [REGRA-NN]`, por exemplo `feat(locacoes): calcula diária de atraso [LOC-10]`.
- Uma tarefa = uma branch `t-<numero>-<slug>` = um pull request.
- Teste junto com o código. Regra com código precisa de pelo menos um teste com o código no nome (`test_loc_10_diaria_de_atraso`).
- Não adicione dependência nova sem registrar o motivo no PR. Dependência de infraestrutura nova pede ADR.

## Quando terminar

Atualize a tarefa em `tarefas/`, escreva o handoff (modelo em `tarefas/README.md`) e avise o próximo agente pelo nome. Não marque como feito o que não roda ou não tem teste.

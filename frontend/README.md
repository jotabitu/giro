# Frontend

Next.js (App Router) + TypeScript estrito + Tailwind + shadcn/ui + TanStack Query. Dono: agente **frontend** (exceto `src/design-system/`, que é do agente **design-system**). Leia `CLAUDE.md` e `.claude/agents/frontend.md` antes de mexer aqui.

## Estrutura

```
frontend/
├── src/
│   ├── app/
│   │   ├── (publico)/       entrar, convite, primeiro acesso, compra (marca Giro)
│   │   ├── (empresa)/       sistema da locadora (marca da locadora)
│   │   │   ├── inicio/          visão geral e inícios por perfil
│   │   │   ├── implantacao/     assistente de 8 passos (marca Giro)
│   │   │   ├── veiculos/  clientes/  locacoes/  vendas/  manutencoes/
│   │   │   ├── financeiro/      caixa, receber, despesas, comissoes, conciliacao
│   │   │   ├── relatorios/
│   │   │   └── admin/           configuracoes, marca, filiais, usuarios, precos,
│   │   │                        contratos, integracoes, assinatura, auditoria, exportar
│   │   └── (plataforma)/    painel do dono do produto (marca Giro)
│   ├── design-system/       tokens e componentes (porta de docs/design-system)
│   ├── components/          componentes de negócio montados com o design system
│   ├── lib/api/             cliente gerado do OpenAPI + hooks TanStack Query
│   ├── lib/formatos.ts      dinheiro, km, datas, placas
│   └── lib/marca.ts         aplica a cor e o logo da empresa (white label)
├── public/marca/            SVGs da marca Giro (de docs/marca/kit)
└── e2e/                     Playwright (agente qa)
```

O mapeamento tela → rota está em `docs/telas/README.md`. O esqueleto (T-002) existe; as páginas dos grupos de rota são marcadores até as telas das tarefas T-020 em diante.

## Comandos

`npm run dev | lint | typecheck | test | build | api:gerar` (ou `make frontend-check`). `npm run api:gerar` gera `src/lib/api/schema.d.ts` de `docs/api/openapi.yaml`; `node scripts/gerar-tokens.mjs` regenera `src/design-system/tokens.ts` de `docs/design-system/tokens.json`.

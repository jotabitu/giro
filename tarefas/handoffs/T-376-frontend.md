# Handoff · T-376 · Next, postcss e zod sem as falhas do npm audit (frontend)

- **Agente:** frontend
- **Branch:** `t-376-audit-frontend`
- **Origem:** job de auditoria da T-361 (PR #397)

## Versões

| Pacote | Antes | Depois | Como |
| --- | --- | --- | --- |
| `next` | 15.5.27 | 15.5.28 | `npm audit fix` (dentro da faixa `^15.5.0`) |
| `zod` | 4.6.5 | 4.6.7 | `npm audit fix` (dentro de `^4.6.5`) |
| `postcss` embutido no `next` | 8.4.31 | 8.5.29 | `overrides: { next: { postcss: "$postcss" } }` em `package.json` |
| `vitest` | 3.2.7 (`^3.2.4`) | 5.0.5 (`^5.0.5`) | sobe de major, ver abaixo |
| `vite` (via vitest) | 7.3.7 | 8.3.5 | junto com o `vitest` |
| `tinypool` (via vitest) | 1.1.1 | sai da árvore | junto com o `vitest` |

O `postcss` da raiz (8.5.29) já estava fora da faixa afetada; o que aparecia era a cópia 8.4.31 que o `next` traz embutida e fixa. O `override` aponta para o `postcss` da raiz.

## Fora da faixa: `vitest` 3 para 5

- **Motivo:** o `tinypool` (crítico, execução remota de código por poluição de protótipo nas opções do worker) e o `@vitest/mocker` só saem com o `vitest` 5. É dependência de desenvolvimento: não vai para o build nem para produção, mas o `npm audit --audit-level=high` falhava por ela.
- **Mudança de código:** só `frontend/vitest.config.ts`. O `vite` 8 trocou o `esbuild` pelo `oxc`, então `esbuild: { jsx: "automatic" }` virou `oxc: { jsx: { runtime: "automatic" } }`. Nenhum teste mudou.
- **Node:** o `vitest` 5 pede Node `^22.12 || ^24`. O projeto usa Node 22 (retomada.md); confira que o CI usa 22.12 ou mais.
- O `vitest` imprime um aviso sobre `configLoader: 'native'` (config em ESM carregada como CommonJS). É só aviso; não mexi.

## Resultado do `npm audit`

- `npm audit --audit-level=high`: sem falha alta nem crítica (sai com código 0).
- Sobram 3 vulnerabilidades **moderadas**, em `postcss-selector-parser` via `tailwindcss` 3 (`postcss-nested`). A correção é `tailwindcss` 4, mudança grande de configuração; não faz parte desta tarefa. Sugiro tarefa própria.

## Verificação

- `npx tsc --noEmit`: limpo. `npm run lint`: limpo.
- `npx vitest run`: 74 arquivos, 700 testes passando (na base da `main` desta branch).
- `npm run build`: concluído, todas as rotas geradas.
- `npm ci` rodado no fim, para o `node_modules` ficar igual ao lock novo.
- Nenhuma tela de Veículos foi tocada.

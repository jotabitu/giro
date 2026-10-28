# T-403 · Correções do E2E no frontend · frontend → orquestrador

**Branch:** `t-403-correcoes-e2e`, a partir da `origin/main`. Itens 1, 3 e 6 de `tarefas/handoffs/T-375-qa-e2e.md`.

## O que mudou
1. **`/admin/suporte`:** `rotaPermitida` (`frontend/src/lib/menu.ts`) ganhou o caso, só para `pode.administracao`. Teste em `menu.test.ts` (administradora abre; gerente e financeiro não).
3. **Tabela de preços:** `PassoPrecos.tsx` invalida `["implantacao"]` quando a categoria é salva, e o Continuar e a mensagem se atualizam sem reload (IMP-07). Teste novo em `PassoPrecos.test.tsx`.
6. **Visual:** busca de Reembolsos (300 px) e Pendências (340 px) no desktop, sem cortar o placeholder; abas com `whitespace-nowrap` e padding menor no celular. Ajuste local nas duas listas, sem mexer no design system.

## Conferência
- `vitest` de menu, implantação e financeiro: 153 testes passando; `tsc` e `eslint` sem erro.
- **Não conferi no navegador a 1440 e 390** o item 6: confirme com o QA.

## Fora desta tarefa
Itens 2 (menu da API), 4 (`exp` do suporte) e 5 (catálogo CRLV-e) são do backend/arquiteto.

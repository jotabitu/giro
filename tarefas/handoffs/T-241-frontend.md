# T-241 · Contador de Aprovações no menu demora a mudar · frontend → orquestrador, qa

**O que foi feito:** `atualizarAposDecisao` (lib/aprovacoes.ts) lê de novo aprovações, despesas e contadores do menu na hora; a lista de Aprovações e o detalhe da despesa (aprovar, recusar, pagar) usam ela. A varredura achou o mesmo atraso em outros pontos, corrigidos: detalhe da despesa não relia as Aprovações; lançar despesa acima de R$ 500 e fechar o caixa com diferença (criam pedido) não relíam Aprovações nem o menu; baixa, recebimento no caixa, detalhe da conta e Novo lançamento em contas a receber não relíam os contadores.
**Onde:** frontend/src/lib/aprovacoes.ts e `aprovacoes.test.ts`; components/aprovacoes/ListaAprovacoes.tsx; components/financeiro/{DetalheDaDespesa,NovaDespesa,CaixaDoDia,BaixaDaConta,ReceberNoCaixa,DetalheDaConta,NovoLancamento}.tsx
**Regras cobertas:** APR-12, FIN-15 (teste: `atualizarAposDecisao` com staleTime e intervalo de 60 s relê os contadores sem esperar).
**O que ficou de fora:** o teste é do helper com QueryClient real; não há teste de clique (sem jsdom). Contadores continuam com refetch de 60 s para mudanças feitas por outras pessoas.
**Próximo passo para quem recebe:** orquestrador abre o PR; qa confere no navegador que Aprovações, Despesas e Contas a receber mudam no menu ao agir.

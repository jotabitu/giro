# T-107 · Telas de referência com a LOC-2836 até 14 out · design-system → orquestrador

**O que foi feito (opção B da T-104, nenhum valor mudou):**
- `Locacoes` (desktop e celular): LOC-2836 com "30 set → 14 out 18:00", situação "Ativa" (sem "Devolve hoje") e ação "Abrir" (quieta, abre o detalhe).
- `Locacao-Detalhe` (desktop e celular): selo "Ativa" no cabeçalho, período "30 set → 14 out 18:00" e o cartão escuro "Devolução em 14 out às 18:00 · faltam 7 dias" no lugar de "Devolve hoje às 18:00 · faltam 6 h". A linha de multa por atraso não mudou.
- `Clientes` (desktop e celular): "LOC-2836 · Factor 150 · devolve em 14 out" (texto do T-014).

**Onde:** `docs/telas/html/{Locacoes,Locacao-Detalhe,Clientes}-{Desktop,Mobile}.dc.html`, `tarefas/em-andamento.md`.

**O que ficou de fora:**
- **`Cliente-Detalhe-Desktop` e `-Mobile`:** ainda não estão na origin/main (entram pelo PR #106), então não editei. Na cópia principal, só leitura, ainda trazem "30 set → hoje 18:00" (desktop duas vezes, celular uma) e "Devolve hoje" (selo e, no desktop, mais uma vez). Depois do merge do #106: merge da origin/main na branch e trocar para "30 set → 14 out 18:00", selo "Ativa" e sem "Devolve hoje".
- **`Locacoes-Desktop`:** a aba "Devolvem hoje 4" não mudou; o seed de 07 out não tem devolução no dia (T-104), então o número merece revisão do produto.

**Verificação:** busca por texto; não restam "Devolve hoje" nem "hoje 18:00" nas telas editadas. Não há teste para HTML de referência.
**Próximo passo:** orquestrador abre o PR, avisa quando o #106 entrar para eu fechar as duas telas de `Cliente-Detalhe`, e decide sobre a aba "Devolvem hoje".

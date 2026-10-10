# T-107 · Telas de referência com a LOC-2836 até 14 out · design-system → orquestrador

**O que foi feito (opção B da T-104, nenhum valor mudou):**
- `Locacoes` (desktop e celular): LOC-2836 com "30 set → 14 out 18:00", situação "Ativa" (sem "Devolve hoje") e ação "Abrir" (quieta, abre o detalhe).
- `Locacao-Detalhe` (desktop e celular): selo "Ativa" no cabeçalho, período "30 set → 14 out 18:00" e o cartão escuro "Devolução em 14 out às 18:00 · faltam 7 dias" no lugar de "Devolve hoje às 18:00 · faltam 6 h". A linha de multa por atraso não mudou.
- `Cliente-Detalhe` (desktop e celular, depois do merge do #106): período "30 set → 14 out 18:00", selo "Ativa" na tabela e "Devolução em 14 out às 18:00" no cabeçalho da locação atual.
- `Clientes` (desktop e celular): "LOC-2836 · Factor 150 · devolve em 14 out" (texto do T-014).

**Onde:** `docs/telas/html/{Locacoes,Locacao-Detalhe,Clientes,Cliente-Detalhe}-{Desktop,Mobile}.dc.html`, `tarefas/em-andamento.md`.

**O que ficou de fora:**
- **`Locacoes-Desktop`:** a aba "Devolvem hoje 4" não mudou; o seed de 07 out não tem devolução no dia (T-104), então o número merece revisão do produto.

**Verificação:** busca por texto; não restam "Devolve hoje" nem "hoje 18:00" nas telas editadas. Não há teste para HTML de referência.
**Próximo passo:** orquestrador abre o PR e decide sobre a aba "Devolvem hoje".

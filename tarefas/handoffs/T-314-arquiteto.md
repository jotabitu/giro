# T-314 · Pontos da T-288 parte 1 · arquiteto → orquestrador, backend (T-288), frontend (T-289), qa

Origem: "Decisões e pontos para o arquiteto" do handoff `tarefas/handoffs/T-288-backend.md` (PR #324). A branch `t-314-pontos-movimentacoes` saiu da `origin/main` e recebeu a `origin/t-288-movimentacoes-backend`, porque o #324 ainda não estava na main.

**As três respostas:**

1. **Posição de `movimentacoes` nos `menu_inicio`:** fica como o backend fez. No gerente e no vendedor, vai no fim da Operação; no vistoriador, no fim do menu. É apresentação, não regra. As telas `Gerente`, `Vendedor` e `Vistoriador` não têm o item, e o fim do grupo não desloca nada do que elas mostram. A regra (`MOV-02`) só diz que o item aparece no menu do perfil e no completo enquanto a pessoa leva uma movimentação, e isso não muda.
   - **Em `docs/api/contas.md`:**
     - a tabela dos `menu_inicio` e a nota com o filtro (gerente sempre; vendedor e vistoriador só com movimentação aberta que levam, com contador; financeiro nunca);
     - o vistoriador com `movimentacoes` no menu único;
     - `movimentacoes` → `movimentacoes` no `GIRO_MODULOS_ATIVOS`, que entra com as telas da T-289, como o backend decidiu.

2. **Editar a agendada apaga as paradas antigas:** não fere o "nada de negócio é apagado", com uma condição. As paradas da agendada são o plano da rota: não têm chegada, saída, valor pago nem despesa, e não há fato que se perca. O que a convenção protege é o histórico: o que se planejou antes precisa ficar visível. Por isso não há `ativo` na parada, que só complicaria as consultas da ordem e da `proxima_etapa`. A exigência fica na auditoria.
   - **No contrato (`movimentacoes.md`, `PATCH`):** o evento `movimentacao.editar` leva no antes e no depois a lista `paradas` (`local_id`, `servico`, `categoria`, `valor_previsto_centavos`, na ordem). Depois de iniciada, nenhuma parada é apagada nem trocada.
   - **O código de hoje não atende:** o `auditar` só faz o retrato da `Movimentacao`, então as paradas antigas somem sem rastro. Isso vira tarefa de backend (abaixo).

3. **Auditoria da baixa sem `detalhes.origem`:** basta o motivo. O contrato muda: sai o `detalhes: { origem: "baixa_veiculo", ... }` da T-311. O `movimentacao.cancelar` da baixa leva o motivo "Veículo baixado: roubo", a regra `MOV-03` e o antes e depois com o status de origem e o `motivo_cancelamento`, como o backend já faz (`mais_campos`). O CA-246-22 pede só que a auditoria tenha a baixa e o cancelamento. Não vale abrir campo livre de detalhes no evento de auditoria por isso.

**Nada virou `[decisão]`:** os três pontos são de contrato e de convenção técnica, sem regra de negócio nova.

**Onde:** `docs/api/contas.md`, `docs/api/movimentacoes.md`, `tarefas/feito.md`.
**Contrato:** sem rota nova; OpenAPI sem mudança.
**Regras:** MOV-01, MOV-02, MOV-03.

**Tarefa de backend (cabe na T-288 parte 2, ou o orquestrador numera):**

> **Paradas antigas na auditoria da edição** · **Agente:** backend · **Regras:** MOV-01 · **Pronto quando:** `movimentacoes.services.editar` grava o `movimentacao.editar` com `paradas` no antes e no depois (lista na ordem com `local_id`, `servico`, `categoria`, `valor_previsto_centavos`), junto dos campos da movimentação. Pode ser pelo `registrar_evento` com `antes` e `depois` montados, ou por um parâmetro de campos extras no `auditar`, à escolha do backend, sem mudar o formato do evento. Teste `test_mov_01_editar_agendada_guarda_paradas_antigas_na_auditoria`.

**Próximo passo para quem recebe:**
- **Backend (T-288):** a tarefa acima. O menu e a auditoria da baixa já estão como o contrato agora diz.
- **Frontend (T-289):** ao ligar as telas, `movimentacoes` entra no `GIRO_MODULOS_ATIVOS` (`config/settings/base.py`, junto com o devops se o `.env.example` listar).
- **QA:** CA-246-22 confere o motivo e a regra no `movimentacao.cancelar`, sem `origem`.
- **Orquestrador:** abrir o PR desta branch depois do #324 (ela já o contém).

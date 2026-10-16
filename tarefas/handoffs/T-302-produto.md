# T-302 · Pontos da T-300 e item 5 da T-289 (movimentações) · produto → orquestrador, arquiteto, backend (T-288), frontend (T-289), qa

Respostas aos "pontos para o produto" do handoff da T-300 (`origin/t-300-movimentacoes-pessoas`, `tarefas/handoffs/T-300-arquiteto.md`) e ao item 5 do handoff da T-289. Tarefa numerada pelo orquestrador, sem seção no backlog.

**O que foi feito:**

1. **Financeiro como recebedor: não recebe** (a regra já respondia). A chegada da transferência tem a vistoria rápida (`MOV-05`), e o financeiro não faz vistoria (tabela de perfis); o contrato também não dá a ele "Registrar chegada". Quem recebe tem os perfis de quem leva: administrador, gerente, vendedor ou vistoriador ligados à filial de destino. A `MOV-02` agora diz isso. **Muda o contrato da T-300:** `recebedores/` e a validação de `recebido_por_id` sem o financeiro, como `pessoas/`.
2. **Administrador em todas as filiais: sim** (a regra já respondia, `USR-07`). Ele leva e recebe em qualquer filial ativa. O financeiro, que também vê todas, continua fora das duas listas. Escrito na `MOV-02`.
3. **Baixa de veículo com movimentação aberta: `[decisão]`** (a regra não responde). A) recusar a baixa (409 `MOV-03`); B) a baixa encerra a movimentação como `cancelada`, com o motivo "Veículo baixado: {motivo}", as despesas das paradas ficam, e na transferência o veículo continua na filial de saída. Padrão: B, porque com A o veículo roubado no caminho nunca sai da frota. Até a resposta, a T-288 recusa (A), como o arquiteto sugeriu. Em "Pontos em aberto" e no backlog.
4. **Item 5 da T-289, "rodou 26 km": a tela faz a conta** (concordo com a leitura do arquiteto). É a diferença entre o km digitado e o `km_saida`, só exibição, como a duração; não é valor nem status. Com o km menor que o da saída, ou vazio, a dica fica só "não pode ser menor que 3.120". A recusa continua da API (422 `VEI-01`). Escrito na `MOV-05`.

**Onde:** `docs/regras-de-negocio.md` (`MOV-02`, `MOV-05`, nota T-302, Pontos em aberto), `docs/qa/criterios/T-246.md` (CA-246-20 e 21), `tarefas/backlog.md`, `tarefas/feito.md`.
**Regras cobertas:** MOV-02, MOV-03, MOV-05, USR-07.

**Próximo passo:**
- **Orquestrador:** abrir o PR desta branch e levar a `[decisão]` da baixa ao dono.
- **Arquiteto:** em `docs/api/movimentacoes.md` (T-300), `recebedores/` sem o financeiro: os perfis são os de `pessoas/`.
- **Backend (T-288):** `recebedores/` e `recebido_por_id` sem o financeiro; testes `test_mov_02_recebedor_sem_financeiro` e `test_mov_02_administrador_em_toda_filial` (CA-246-20); a baixa com movimentação aberta recusada até a decisão.
- **Frontend (T-289):** a dica "rodou {n} km · não pode ser menor que {km_saida}" calculada na tela (CA-246-21).
- **QA:** CA-246-20 e 21.

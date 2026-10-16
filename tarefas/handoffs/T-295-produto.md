# T-295 · Leituras das Movimentações confirmadas pelo dono · produto → orquestrador, arquiteto, backend, frontend, qa

**O que foi feito:** o dono confirmou as seis leituras do produto nas Movimentações, sem mudança:
1. a parada sem nota gera a despesa marcada "sem nota";
2. a categoria padrão é "outros", e "manutenção" para oficina;
3. o veículo nunca fica guardado fora de uma filial;
4. o local de apoio é da empresa, criado na parada, inativado e não apagado;
5. o documento que vence no caminho não muda o status no dia, e a chegada decide;
6. quem leva ganha o item Movimentações enquanto houver uma movimentação aberta dele.

A branch `t-295-leituras-confirmadas` sai da `origin/main` (8db1a04).

**Onde:**
- `docs/regras-de-negocio.md`:
  - "Pontos em aberto": o item foi marcado como confirmado;
  - "Decisões de 16 out 2026": uma linha nova;
  - as marcas "a conferir pelo dono" saíram da `USR-05` e da `MOV-01` a `MOV-05`;
  - notas de mudança da T-295 na `USR-05` e na seção Movimentações.
- `docs/qa/criterios/T-246.md`: o título da seção da T-283 e o CA-246-17, sem a marca.
- `tarefas/backlog.md`: a seção da T-295 saiu.
- `tarefas/feito.md`.

**Regras cobertas:** MOV-01, MOV-02, MOV-04, MOV-05, USR-05.

**O que ficou de fora:** nada. As notas de mudança antigas continuam citando "a conferir pelo dono", porque são histórico.

**Próximo passo para quem recebe:** nada muda no contrato da T-286 nem no código: o comportamento é o mesmo.

# T-086 · Regra da OS concluída com documento vencido · produto → orquestrador, backend, qa

**O que foi feito:**
- **`MAN-05`:** se o CRLV ou o seguro venceu durante a OS (`VEI-03`), o veículo vai para `indisponivel` ao concluir a OS, com o motivo do documento, e não para `disponivel`. Renovar não libera sozinho: o gerente desbloqueia depois, como no `disponivel` que venceu.
- **Também mudaram:**
  - o estado `concluida` na tabela da OS;
  - o `VEI-03`, com uma frase que aponta para a `MAN-05`;
  - a tabela de transições dos veículos, com a linha nova `em_manutencao` → `indisponivel` (sistema).
- **Registro:** nota de mudança de 08 out na seção de Manutenção e linha em "Decisões de 08 out 2026". O ponto saiu de "Pontos em aberto".
- **Critério CA-MAN-01** em `docs/qa/criterios/manutencao.md`, arquivo novo, porque o módulo ainda não tem tarefa. PMZ3E17, com o seguro vencido em 25 out:
  - concluir a OS em 27 out leva o veículo para `indisponivel`, com motivo "Seguro vencido";
  - renovar o seguro não libera, e o `desbloquear` leva a `disponivel`;
  - com os documentos em dia, ou com só IPVA ou rastreador vencidos, o veículo vai para `disponivel`.

  O seed não tem OS para o PMZ3E17, então o teste cria.

**Onde:** `docs/regras-de-negocio.md` (transições dos veículos, `VEI-03`, tabela da OS, `MAN-05`, nota de mudança, "Decisões de 08 out 2026", "Pontos em aberto"), `docs/qa/criterios/manutencao.md`, `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código ou teste mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend.

**O que ficou de fora:** o código entra na fase 2, com o módulo de manutenção.

**Próximo passo para quem recebe:**
- **Orquestrador:** quando o módulo de manutenção virar tarefa, renomear `manutencao.md` para `T-<numero>.md`; eu renumero o critério.
- **Backend e QA (fase 2):** `test_man_05_*` do CA-MAN-01.

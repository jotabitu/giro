# T-076 · Regra e critério da reativação com convite cancelado · produto → orquestrador, backend, qa

**O que foi feito:**
- **`USR-04`:** reativar depende de a pessoa já ter chegado a `ativo`.
  - Quem já foi `ativo` volta `ativo`.
  - Quem nunca chegou a `ativo` volta para `convite_pendente`, com convite novo de 7 dias pelos mesmos canais (`USR-01`). Vale mesmo que a pessoa já tenha criado a senha antes do cancelamento.
  - Nos dois casos, reativar respeita o limite do plano (`PLT-03`).
  - A nota de mudança de 08 out (T-076) diz que é a única transição `desativado → convite_pendente`.
- **"Decisões de 08 out 2026":** linha nova com a opção B. O ponto saiu de "Pontos em aberto".
- **CA-011-22** em `docs/qa/criterios/T-011.md`, com o seed:
  - Felipe (já foi ativo) reativado → `ativo`, sem convite, plano de 5 para 6.
  - Lúcia: convite cancelado em 08 out (plano de 5 para 4), reativada em 09 out → `convite_pendente`, `convite_expira_em` em 16 out, convite novo enviado, plano volta a 5. O link antigo continua 404 ou 410. Ela passa a `ativo` depois de confirmar as 2 etapas.
  - O mesmo vale se Lúcia já tinha criado a senha.
  - Com o plano em 10 de 10 → 422 `PLT-03`, ela continua `desativado` e nenhum convite sai.

**Onde:** `docs/regras-de-negocio.md` (`USR-04`, nota de mudança, "Decisões de 08 out 2026", "Pontos em aberto"), `docs/qa/criterios/T-011.md` (CA-011-22), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código ou teste mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend.

**O que ficou de fora:** o código, o contrato em `docs/api/contas.md` e o OpenAPI ficam para a T-077.

**Próximo passo para quem recebe:**
- **Backend (T-077):** implementar a `USR-04` nova e o teste `test_usr_04_*` do CA-011-22. Para saber se a pessoa já foi `ativo`, use o histórico de transições, por exemplo o evento `usuario.ativar`.
- **QA:** conferir o CA-011-22 na entrega da T-077.

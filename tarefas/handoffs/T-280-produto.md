# T-280 · CA-248-12 e o link antigo do convite · produto → orquestrador, backend, qa

**O que foi feito:** decidi o código do link antigo depois de copiar um novo. Fica o **410 `convite_expirado`**, que a T-250 (PR #272) já devolve; o backend não muda.

**Por quê:**
- **P-06:** a revisão da segurança pede que o convite novo invalide o anterior marcando-o como vencido. O reenvio já faz assim, e copiar faz "como o reenvio" (`USR-01`).
- **Mensagem certa para quem abre o link:** "Este convite venceu. Peça um novo ao administrador." diz o que fazer. O 404 `nao_encontrado` é do link que não existe ou já foi usado e não ajuda a pessoa.
- **Segurança:** os dois códigos só aparecem para quem já tem um token válido no formato. O 410 não revela nada além do que o 404 revela.

**Onde:**
- `docs/qa/criterios/T-248.md`: o CA-248-12 e o CA-248-13 pedem 410 no link substituído, com a nota de ajuste;
- `docs/regras-de-negocio.md`: a `USR-01` diz o aviso que vê quem abre o link substituído, com a nota de mudança de 16 out;
- `tarefas/backlog.md`: seção da T-280;
- `tarefas/em-andamento.md`: a T-280 em andamento.

**Regras cobertas:** USR-01 (P-06).

**O que ficou de fora:** o CA-011 do reenvio continua aceitando "404 ou 410", o que não conflita. Fica como está.

**Para quem recebe:**
- **Backend (T-250):** nada muda; o `test_usr_01_copiar_link_invalida_o_anterior` com 410 está de acordo com o critério.
- **QA:** conferir com 410.

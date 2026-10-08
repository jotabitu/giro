# T-075 · Reativar usuário com convite cancelado · produto → orquestrador, backend

**O que foi feito:**
- Analisei a dúvida da T-069 (`USR-01`, `USR-04`) e registrei a pergunta fechada em "Pontos em aberto" de `docs/regras-de-negocio.md`.
- Como é hoje no código (`backend/apps/contas/services.py`, `reativar_usuario`): todo `desativado` volta `ativo`, sem aviso. Quem teve o convite cancelado antes de criar a senha fica ativo na lista, não recebe nada e só entra se descobrir o "Esqueci a senha". As 2 etapas não são problema, porque usuário `ativo` pode cadastrar o autenticador (`pode_configurar_2fa`).
- Opções:
  - A) Como hoje. Não muda o código.
  - B) Quem nunca chegou a `ativo` volta para `convite_pendente`, com convite novo de 7 dias pelos mesmos canais. Quem já foi `ativo` volta `ativo`. O limite do plano vale nos dois casos (`PLT-03`). Transição nova `desativado → convite_pendente`, só nesse caso.
- **Recomendação: B.** A lista nunca mostra como ativo quem não consegue entrar, e a pessoa recebe o link sem pedir. Padrão: B, mas o código fica como está até o dono aprovar.

**A recomendação muda o código:** sim, se o dono aprovar B. O ajuste vira tarefa do backend:
- `Usuario.TRANSICOES` ganha `desativado → convite_pendente`.
- `reativar_usuario` separa quem nunca foi `ativo` (por exemplo, pelo histórico de transições: nunca teve `usuario.ativar`), cria o convite e envia depois do commit, como o `reenviar_convite`.
- `POST /api/usuarios/{id}/reativar/` passa a poder responder `convite_pendente` (contrato em `docs/api/contas.md`, com o arquiteto).
- Critério no CA-011-22: Mariana cancela o convite de Lúcia e a reativa → `convite_pendente`, `convite_expira_em` daqui a 7 dias, convite enviado por e-mail, plano volta de 4 para 5. Reativar Felipe (já foi ativo) → `ativo`, como hoje. Eu escrevo o critério quando a decisão sair.

**Onde:** `docs/regras-de-negocio.md` (fim de "Pontos em aberto"), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código ou teste mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend.

**O que ficou de fora:** a regra `USR-04` e os critérios só mudam depois da decisão.

**Próximo passo para quem recebe:**
- **Orquestrador:** levar a decisão A ou B ao dono do produto e, se for B, abrir a tarefa do backend.
- **Backend:** nada até a decisão.

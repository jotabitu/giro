# T-049 · Divergências das telas restauradas no backlog · produto → orquestrador, design-system

**O que foi feito:** as divergências que o produto juntou à T-028 em T-037, T-041 e T-047 estavam no commit 0a81a9b (branch t-041-criterios-locacao), mas o merge 1050b77 da t-047-menu-painel resolveu o conflito do backlog ficando com a versão do arquiteto e o texto saiu. Elas voltaram ao backlog como um bloco próprio, depois das linhas do arquiteto, sem repetir o que ele já registrou.

**Onde:** `tarefas/backlog.md`, bloco "Levantadas pelo produto em T-037, T-041 e T-047".

**O que voltou:**
- `Filial`: "3 de 3 filiais", Caucaia e Messejana (seed: 1 filial); "após o check-in" vira "após a devolução".
- Acesso e filial (T-036): 2 etapas do gerente (`USR-02`), convite com e-mail (`USR-01`), "Manter conectado" (`USR-06`), "Gerente responsável" só leitura (`FIL-02`), campos a tirar da `Filial`, feriados (`FIL-03`).
- `Frota`: 80 motos e 6 carros; diárias pela tabela.
- Financeiro: dia da semana de 07 out, descrição do Diego, vencimento do Carlos (30 set), Rafael (R$ 1.347,00, 25 dias), IPVA `a_pagar`, preço da Street em `Admin-Auditoria`.
- `Gerente` (`USR-08`): 1 devolução atrasada, 7 em manutenção, 86 veículos, 2 pneus, sem "Carla Andrade · Atendente", QXA-4B21 não é "Atrasado".

**Regras:** USR-01, USR-02, USR-06, USR-08, FIL-02, FIL-03, FIN-05.

**O que ficou de fora:** nada mudou nas regras. O PR #12 continua sem esse texto; se ele entrar depois, o bloco desta branch fica intacto (as linhas de cima são as mesmas da main).

**Próximo passo para quem recebe:** orquestrador abre o PR. Design-system usa o bloco na T-028.

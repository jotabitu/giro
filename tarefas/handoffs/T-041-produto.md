# T-041 · Critérios de aceite de T-015 a T-018 e decisões de 07 out · produto → orquestrador, qa, backend, arquiteto

**O que foi feito:**
- Critérios "Dado... quando... então..." com os números do seed Moto Rápida para T-015 a T-018, um arquivo por tarefa em `docs/qa/criterios/`, e o "Pronto quando" de cada tarefa no backlog apontando para o arquivo.
- As decisões do dono do produto de 07 out viraram regra:
  - item 12: desbloqueio manual (`CLI-05`, `APR-05`);
  - item 14: juros com mês de 30 dias (`FIN-03`);
  - item 15: combustível com taxa de R$ 10 uma vez (`DEV-01`, `DEV-03`);
  - item 16: extras por período (`LOC-02`, tela para a T-028);
  - item 17: renovação vale na hora (`LOC-08`);
  - item 18: troca com acerto único (`LOC-09`);
  - item 19: gerente faz direto (tabela de perfis);
  - item 20: estados da comissão de locação (`FIN-09`).

**Onde:** `docs/qa/criterios/T-015.md` (25 critérios), `T-016.md` (20), `T-017.md` (22), `T-018.md` (16); `docs/regras-de-negocio.md`; `tarefas/backlog.md`.

**Contratos usados:** `locacoes.md`, `vistorias.md` e `contratos.md` da branch t-038. `financeiro.md` e `auditoria.md` ainda não existiam: T-017 e T-018 descrevem o comportamento pelas regras, pelo modelo e pela ADR 0010. Quando os contratos saírem (T-043), confiro os nomes dos códigos de erro.

**Seed:**
- "Despesas de outubro" aguardando aprovação passou para R$ 1.200,00 (o IPVA de R$ 186,40 nasce `a_pagar` pela `FIN-05`); aprovado pelo dono e avisado ao QA.
- O `DEV-03` ganhou de onde vêm os R$ 32,00 (tanque de 16 L, R$ 5,50 por litro, cheio → 3/4).
- Os juros têm exemplos exatos (Carlos: multa R$ 5,99 e juros R$ 0,70; Rafael: multa R$ 26,94 e juros R$ 11,23).

**Interpretação a confirmar com o backend:** atraso contado em blocos de 24 h a partir do fim previsto, com fração contando como dia inteiro; a tolerância só decide se há atraso (CA-015-19). Exemplo: fim às 18:00 e devolução às 18:01 do dia seguinte = 2 diárias.

**T-028:** recebeu as divergências das telas `Devolucao` ("1/2 tanque" deve ser "1/4"), `Caixa` e `Financeiro` ("Terça, 07 out" deve ser quarta; descrição do lançamento do Diego; vencimento da parcela do Carlos), `Receber` (Rafael), `Despesas` (IPVA) e `Admin-Auditoria` (3 senhas e preço da Street).

**Ainda em aberto com o dono:** itens 11 (ordem do botão de clientes) e 13 (inativar cliente), com o padrão já aplicado.

**Próximo passo para quem recebe:** QA usa os arquivos de critérios; backend de T-015 a T-018 nomeia os testes pelo código da regra. O arquiteto, no merge da t-038, tira as `[decisão]` da T-038 do backlog e alinha `vistorias.md` (fórmula do combustível; o exemplo "faltou 1/2 tanque" vira 3/4) e `locacoes.md` (troca e renovação deixam de ser `[decisão]`).

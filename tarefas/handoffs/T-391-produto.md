# T-391 · Texto do downgrade recusado por atividade · produto → orquestrador, backend (T-196)

Responde à `[decisão]` do handoff `tarefas/handoffs/T-196-backend.md` (PR #409).

**O que foi feito:**
- **Critério novo CA-ASS-71** em `docs/qa/criterios/assinatura.md`: o e-mail do downgrade agendado que não aconteceu.
  - **Assunto:** continua "Giro: a mudança para o plano {plano agendado} não aconteceu".
  - **1ª linha:** muda pelo motivo (limite ou algo aberto, só a atividade, ou os dois).
  - **Resto:** igual em todos os casos.
  - A atividade sai com as palavras da recusa da tela (`PLT-12`, CA-ASS-52): "o plano Essencial não inclui vendas, e a empresa hoje só vende. Para mudar, ela precisa alugar.".
- **`PLT-04`:** cita a atividade no motivo do e-mail, com nota de mudança na seção Plataforma.

**O que o Backend troca na T-196:**
1. Em `plataforma/services.py`, `texto_do_que_excede` deixa de pôr "a empresa só vende" na lista. A lista fica só com limites e abertos ("4 de 3 usuários").
2. Em `plataforma/tasks.py`, o corpo do e-mail segue a tabela do CA-ASS-71:
   - com a lista: "...mas o uso de hoje não cabe nele: {lista}.";
   - só a atividade: "...mas o plano {plano} não inclui vendas, e a empresa hoje só vende. Para mudar, ela precisa alugar.";
   - os dois: a frase da lista, seguida de "Além disso, o plano {plano} não inclui vendas, e a empresa hoje só vende. Para mudar, ela precisa alugar.".
3. A abertura "A {empresa.nome_exibicao} ia mudar" vira "A empresa {nome} ia mudar". É o mesmo problema de gênero do "da {nome}" que a T-299 corrigiu.
4. A última frase vira "Para mudar, resolva o que está acima e escolha o plano de novo em Assinatura." (antes, "ajuste o uso"), porque o motivo pode ser a atividade.
5. O teste `test_plt_04_email_do_downgrade_recusado` cobre os três casos com os exemplos do critério (fixture "Pedal Norte").

**Onde:** `docs/regras-de-negocio.md` e `docs/qa/criterios/assinatura.md`. O contrato `assinatura.md` só diz "o mesmo `detalhes` da 422" e não precisa mudar.
**Regras cobertas:** PLT-04, PLT-12.
**Próximo passo:** o Backend aplica os itens 1 a 5 na branch da T-196 (PR #409) antes do merge.

# T-053 · Números de telas que dependem de regra · produto → orquestrador, backend, design-system, arquiteto, qa

**O que foi feito:**
- **Contador "Contas a receber" do menu:** é o número de parcelas `atrasada`. É o mesmo número da aba "Em atraso" e da chave `receber` de `GET /api/painel/contadores/`, que já estava em `docs/api/painel.md`. Conta parcelas, não clientes. Seed em 07 out: **2** (Carlos e Rafael), não 7. Regra nova `FIN-15`.
- **"Previsto no mês", "Recebido", "Vence hoje", "Em atraso" e abas do `Receber`:** a definição está na `FIN-15`.
  - Base: contas da filial, sem caução e sem `cancelada` e `renegociada`, valores sem multa e juros.
  - Previsto: contas que vencem no mês, pagas ou não.
  - Recebido: as `paga` desse previsto; percentual = recebido ÷ previsto, com 2 casas.
  - Vence hoje: contas não pagas que vencem hoje.
  - Em atraso: todas as atrasadas, de qualquer mês.
  - Abas: "Em atraso" ignora o período; "Vencem hoje", "A vencer" e "Pagas" seguem o período escolhido; "Todas" é a soma das quatro.
- **Expurgo da auditoria:** `AUT-16`, todo dia 1 às 03:00, em cada empresa e na plataforma. Apaga os eventos com mais de 5 anos (`AUD-02`) e grava um evento do Sistema (categoria segurança) com a data limite e a quantidade de eventos apagados.
- **Seed:** nova linha "Contadores do menu em 07 out (Mariana)" com Contas a receber 2, Despesas 1, Conciliação e Comissões sem número.

**Onde:** `docs/regras-de-negocio.md` (`FIN-15`, `AUT-16`, linha nova do seed, notas de mudança de 08 out, item em "Pontos em aberto"), `tarefas/backlog.md` (1 `[decisão]` e 2 `[divergência]` em "Levantadas pelo produto em T-053").

**Decisão para o dono do produto (via orquestrador):** a base do "Recebido". A) só as contas que vencem no mês e já foram pagas; B) tudo o que foi pago no mês. Padrão: **A**, que já está escrito na `FIN-15`.

**O que ficou de fora:**
- Os números de outubro do `Receber` e o "Entra hoje" do `Financeiro` (R$ 74,2 mil em 318 parcelas, R$ 21,6 mil, R$ 1.890 em 9 parcelas, 226, 72) não saem do seed e não fecham com as regras:
  - 9 parcelas custam pelo menos R$ 2.511,00.
  - 42 locações dão no máximo 210 vencimentos no mês.
  - As abas somam 309, não 318.
  - 21,6 ÷ 74,2 dá 29,11%, não 29,00%.

  Proposta registrada no backlog: o qa monta a carteira de outubro no seed, o produto registra os números e o design-system troca as telas. Isso é trabalho novo, e o orquestrador decide se vira tarefa.
- O quadro (`em-andamento.md`, `feito.md`) fica com o orquestrador, para não conflitar com o PR #23.

**Próximo passo para quem recebe:**
- **Backend:** criar a tarefa Celery Beat do expurgo com o código `AUT-16` e o teste `test_aut_16_*`; os números do `Receber` e do contador seguem a `FIN-15`.
- **Design-system:** na barra lateral das 32 telas desktop e no `Menu-Mobile`, trocar Contas a receber 7 por 2, Despesas 3 por 1 e tirar o número de Conciliação. Em 30 telas desktop, trocar Manutenções 5 por 7.
- **Arquiteto:** em `docs/api/financeiro.md`, `recebido_pct` passa a "29.11" e as `contagens` seguem as abas da `FIN-15`. Os 189000 em "9 parcelas" de `docs/api/painel.md` esperam a carteira do seed.
- **QA:** teste da `FIN-15` com um caso pequeno próprio até a carteira existir. Contador do menu = 2 no seed.

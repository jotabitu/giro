# T-152 · Critérios de aceite das tarefas do MVP que faltam · produto → orquestrador, backend, frontend, qa, design-system

**O que foi feito:** critérios de aceite das 5 tarefas do MVP que ainda não tinham, no formato das anteriores (`CA-0XX-NN`, com os números do seed Moto Rápida em 07 out 2026). Nenhuma regra mudou: os critérios juntam o que as regras, os contratos e o seed já dizem. Onde o seed atual discorda das regras, o critério diz qual é o certo.

**Onde:**
- `docs/qa/criterios/T-027.md` · importação (22 critérios): planilha de 86 linhas da tela (83 prontas e 3 com erro: placa QXA4B2, chassi repetido da linha 12, ano do modelo em branco), "Corrigir aqui" até 86 veículos, ignorar, validações de veículo e cliente (mensagem de cliente nunca repete o dado), limite do plano (Essencial: 30 importados e 12 de fora, com o texto do `IMP-03`; Profissional com 86: 64 cabem), corrida com o cadastro pela tela, 409 e 422 do contrato, arquivo recusado, perfis, suporte "ver e editar", passo da implantação, auditoria e dados temporários.
- `docs/qa/criterios/T-023.md` · telas `Receber`, `Caixa` e `Financeiro` (26 critérios): cartões e abas do mês, da semana e de hoje; linhas em atraso; ações por perfil; cobrar e cobrar em lote; detalhe com R$ 306,09; Pix e recebimentos desligados; caixa de 07 out (R$ 1.111,90, gaveta R$ 281,00, 7 movimentos); receber no caixa; abrir, sangria e fechar com e sem diferença; início da Lúcia em 07, 10 e 14 out; menu do financeiro.
- `docs/qa/criterios/T-019.md` · seed completo (31 critérios): empresa, pessoas, uso do plano, implantação concluída, preços, frota por estado, QXA-4B21, clientes, as locações das telas, carteira de outubro e da semana, caixa de 07 out, despesas de outubro, contadores, auditoria nas horas do seed, e os casos que rodam sobre o seed (R$ 183,00, R$ 263,00, R$ 84,80 e R$ 286,20, R$ 365,37, R$ 673,77, R$ 928,55, R$ 1.039,15).
- `docs/qa/criterios/T-025.md` · ponta a ponta (12 critérios): Bruna cadastra o Paulo Henrique Lima e cria a LOC-2858 (R$ 629,00 na retirada), vistoria, assinatura pelo link, pagamento no caixa (gaveta R$ 910,00); devolução em 14 out com avaria de R$ 380,00 (cobrar R$ 80,00) e baixa no caixa aberto no dia (gaveta R$ 280,00). No celular, João faz as vistorias pela agenda.
- `docs/qa/criterios/T-029.md` · Asaas (18 critérios): subconta com a chave cifrada, notificações do Asaas desligadas (marca da locadora), Pix de R$ 306,09 e boleto, centavos sem `float`, recorrente, webhook (200 na hora, consulta antes de baixar, idempotência, 401, pendências, 429), Asaas fora do ar, nada do Asaas fora da interface.
- `tarefas/backlog.md`: T-152 criada (commit 62abe87) e movida para o feito; linha "Critérios" nas T-019, T-023, T-025, T-027 e T-029; divergências da T-023 na T-028.

**Regras cobertas:** IMP-02, IMP-03, IMP-05, PLT-03, VEI-01, CLI-01 a CLI-05, FIN-01 a FIN-05, FIN-07, FIN-08, FIN-15, APR-02 a APR-04, APR-09, AUT-03 a AUT-05, LOC-01 a LOC-15 (pelos casos), DEV-01 a DEV-08, USR-05 a USR-09, AUD-01, AUD-03 a AUD-05, AUD-07, AUD-09.

**Decisões do produto nesta tarefa (composição do seed e leitura de tela, sem regra nova):**
1. **Locações geradas (D-21 da T-138, CA-019-18):** a correção da T-138 pagou as parcelas de 07 out das LOC-2801 e 2815 a 2818 e fez começar em 07 out as locações com o 1º vencimento depois disso. Isso tira 6 parcelas de "Vence hoje" e contraria a carteira ("nada com vencimento futuro está pago"). O certo: essas locações começaram um período antes, com a parcela anterior paga, e as parcelas de outubro ficam iguais ao CSV.
2. **Reservas (CA-019-19):** as 9 reservas da T-138 retiram de 13 a 23 out, e as contas delas nascem na confirmação com vencimento em outubro, o que muda o "Previsto" e o "A vencer". Passam a retirar de 03 a 13 nov. Os números de outubro das regras não mudam.
3. **Número da linha na importação (T-027):** é o da planilha aberta no Excel (cabeçalho = linha 1).
4. **Caixa com "Todas as filiais" (CA-023-16):** a tela pede a filial antes de abrir, receber ou listar.

**Pontos para o produto (próxima tarefa de regras, sem pressa):**
- A tabela de estados da locação dá a LOC-2856 como exemplo de `aguardando_retirada` ("Aguardando assinatura"), e a `CLI-07` dá o Lucas como incompleto. O caixa de 07 out, o CA-017-04, o caso "Histórico da análise" ("paga na retirada") e o seed o têm retirado em 07 out e completo. Os critérios seguem o seed (LOC-2856 `ativa`); falta trocar os dois exemplos nas regras.
- A linha "Empresa" dos dados de referência diz 612 clientes e 42 locações ativas; o seed tem 51 clientes e 51 locações abertas (41 `ativa`, 1 `devolucao_atrasada`, 9 `aguardando_retirada`). Nenhum caso depende desses dois números.

**O que ficou de fora:** vendas, comissões, conciliação, DRE e o funil da plataforma (fase 2, CA-019-31); a cobrança da assinatura no Asaas (fase 2, CA-029-18). Como controlar a hora no E2E (a ADR 0021 só fixa a data) fica com o qa e o arquiteto.

**Próximo passo para quem recebe:**
- **Backend (T-027, T-029):** os testes levam o código do critério ou da regra no nome. Na T-029, as respostas gravadas do sandbox não podem ter chave nem dado pessoal.
- **Frontend (T-023):** a tela segue os critérios, e não os números de exemplo das telas; os itens do CA-023-25 e do CA-023-26 não aparecem.
- **QA (T-019, T-025):** CA-019-18 e CA-019-19 mudam o `backend/seed/carteira.py` (`_confirmar` e `RETIRADAS_DAS_RESERVAS`); os testes `test_seed_138_*` que contam com as reservas em outubro mudam junto.
- **Design-system (T-028):** a lista nova está na T-028 do backlog.

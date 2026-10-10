# T-114 · Código das decisões da devolução (T-113) · backend → orquestrador, qa, frontend, arquiteto

**O que foi feito:** as decisões de 09 out 2026 (T-113) no acerto da devolução, a conta da `FIN-03` e o teste pedido da T-115.
- **Parcelas no acerto (`DEV-01`, `FIN-03`, CA-016-13):** entram as parcelas em aberto que vencem até o dia da devolução (`vencimento__lte`), inclusive a do dia. Cada item `parcela_aberta` vale o devido nesse dia, com multa e juros. A descrição da parcela do dia é "Parcela 3 de 5 · vence hoje, 07/10", e não "venceu em". A vencida mostra a multa e os juros: "Parcela 2 de 5 · venceu em 30/09 (multa R$ 5,99 e juros R$ 0,70)".
- **`FIN-03` numa função só:**
  - `comum.dinheiro.juros_pro_rata(valor, pct_mes, dias)`, com um arredondamento só (T-045, ponto 4).
  - `financeiro.selectors.devido_ate(conta, dia)`: principal, multa, juros e dias de atraso. Conta o atraso a partir do dia seguinte ao vencimento ou, se a conta nasceu vencida, ao dia em que nasceu. Lê as taxas da `ConfiguracaoEmpresa` e só cobra multa e juros com a cláusula no contrato da origem (`contratos.selectors.permite_juros`).
  - Combinado com o arquiteto: a T-017 usa a mesma função no `valor_hoje` e na baixa no caixa.
  - 29940 vencida em 30 set e devolvida em 07 out dá 30609.
- **Ordem da caução (`DEV-02`, CA-016-22):** `pagar_com_caucao(..., dia=...)` paga as parcelas inteiras, da mais antiga para a mais nova, pelo `devido_ate`, e grava multa e juros na conta paga.
  - A primeira parcela que não cabe e as seguintes vão para `renegociada`, com transição e auditoria (`conta_receber.renegociar`, `DEV-02`), mesmo que uma seguinte coubesse.
  - Depois, as cobranças são pagas com a caução até onde ela der. A sobra abate as renegociadas.
  - O que falta vira **uma** conta `acerto`, igual a `-saldo`. Com saldo negativo, nenhum `Reembolso`.
- **Ligação da conta `acerto` com as parcelas (`FIN-01`, `CLI-05`), nomes do arquiteto:** apoio novo `financeiro.Renegociacao` (motivo, origem genérica, `por` nulo quando é o sistema, `em`). Na `ContaReceber`, `renegociada_em` na original (`originais`) e `nasceu_de` na nova (`novas`), as duas nulas e com PROTECT. No acerto, a origem é `devolucao`. Migração `financeiro/0003_renegociacao`.
- **Devolução antes do fim (`DEV-07`, CA-016-23):**
  - Encerrar responde 422 `DEV-07` ("A devolução é antes do fim do contrato. Peça o encerramento antecipado ao gerente.", `detalhes: { fim_previsto, devolvida_em }` em Z) quando a chegada concluída é de um dia anterior ao do fim previsto, no fuso da filial, e não há encerramento antecipado aprovado.
  - Nada muda: a devolução fica em `rascunho`, e a locação, o veículo e as contas ficam como estavam.
  - Abrir a devolução e concluir a chegada continuam permitidos. No dia do fim, antes da hora, encerra.
  - `acerto.avisos: [ { codigo: "DEV-07", mensagem } ]`, no nível do acerto, no formato da T-111. A lista fica vazia fora desse caso e no acerto concluído.
- **Com a aprovação (`DEV-07`, `LOC-13`):** ao encerrar, `cancelar_abertas(vencendo_depois_de=dia da devolução)`. A parcela do dia não é cancelada, porque está no acerto. O crédito do mensal (T-111) já contava só as que vencem depois do dia, então nada conta duas vezes.
- **Teste da T-115 (`LOC-08`, CA-015-27, decisão do dono, opção A):** `test_loc_08_ca_015_27_extra_desativado_continua`. O capacete foi desativado antes da renovação, e as 2 parcelas novas continuam 34900. O comportamento já existia.

**Onde:**
- Código:
  - `backend/comum/dinheiro.py` (`juros_pro_rata`);
  - `backend/apps/financeiro/selectors.py` (`Devido`, `devido_ate`);
  - `backend/apps/financeiro/services.py` (`pagar_com_caucao`, `_renegociar_no_acerto`, `marcar_paga(devido=)`, `NovaConta.nasceu_de_id`);
  - `backend/apps/financeiro/models.py` + `migrations/0003_renegociacao.py`;
  - `backend/apps/vistorias/services.py` (`parcelas_do_acerto`, `_item_da_parcela`, `antecipada_sem_aprovacao`, `avisos_do_acerto`, `encerrar_devolucao`);
  - `backend/apps/vistorias/selectors.py` e `api/serializers.py` (`avisos`).
- Testes:
  - `backend/tests/aceitacao/test_t016_vistorias.py` (CA-016-13, 22, 23 e 24);
  - `backend/comum/tests/test_dinheiro.py`;
  - `backend/tests/aceitacao/test_t111_decisoes_t091.py` (CA-015-27).

**Contrato** (combinado com o arquiteto em 09 out; emendas neste PR para ele revisar):
- `docs/api/vistorias.md`: `parcela_aberta`, `avisos`, a ordem da caução, o 422 `DEV-07` e o cancelamento das parcelas futuras ao encerrar.
- `docs/api/financeiro.md`: o texto do renegociar passa a usar `Renegociacao`, e há `pagar_com_caucao` e `devido_ate` na interface.
- `docs/decisoes/modelo-de-dados.md`, item 18: as duas FKs e o apoio `Renegociacao`.
- `docs/api/openapi.yaml` regenerado (`AvisoAcerto`).

**Mudanças nos testes antigos:**
- A carteira (`tests/aceitacao/carteira.py`) grava o `criado_em` das parcelas no início da locação. Antes elas "nasciam" em 07 out, e a `FIN-03` as trataria como nascidas vencidas.
- Os casos com a LOC-2856 do Lucas devolviam em 07 out, antes do fim de 21 out. Agora caem na `DEV-07`, e `_lucas_ativo` passa o fim previsto para 07 out 18:00. Os valores esperados não mudam.
- O teste antigo do CA-016-13 virou três, conforme o critério corrigido.

**Regras cobertas:** `DEV-01` (`test_dev_01_*ca_016_13*`, `test_dev_01_dev_02_dev_07_ca_016_24_*`), `FIN-03` (`test_dev_01_fin_03_ca_016_13_*`, `test_fin_03_juros_pro_rata_*`), `DEV-02` (`test_dev_02_ca_016_22_*`), `DEV-07` (`test_dev_07_ca_016_23_*`, CA-016-24), `LOC-08` (`test_loc_08_ca_015_27_extra_desativado_continua`). A LOC-2836 continua devolvendo R$ 183,00 (CA-016-09).

**Check** (com `rodar.sh`, imagem `giro-backend:latest`, um processo por vez): ruff, `ruff format --check`, mypy e `makemigrations --check` limpos; pytest `598 passed, 3 xfailed` (a `origin/main` dá 589 e 3); OpenAPI gerado com `--validate`.

**Leituras minhas (pode contestar):**
- A parcela que vai para `renegociada` também guarda a multa e os juros do dia (`multa_centavos`, `juros_centavos`), para o extrato mostrar de onde vem o valor da conta `acerto`.
- No CA-016-24, a aprovação do encerramento em 07 out já cancela as parcelas 4 e 5, e o encerramento cancela de novo pelo dia da devolução, o que não faz nada se já estão canceladas. Se a devolução for depois do `cancelamento_data`, as parcelas entre os dois dias já foram canceladas na aprovação e não entram no acerto. A `LOC-12` conta o encerramento a partir do `cancelamento_data`, então deixei assim. Se o produto quiser outro comportamento, vira `[decisão]`.

**O que ficou de fora:** o `valor_hoje` e a baixa no caixa usando `devido_ate` ficam com a T-017.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR e pedir a revisão do arquiteto nas emendas de contrato e na `Renegociacao`.
- **QA:** validar pelos CA-016-13 e 22 a 24. O CA-016-24 usa a caução de 30000 e o contrato com a cláusula gravados na fixture, porque a carteira não tem esses dados.
- **Frontend:** mostrar `acerto.avisos` (`DEV-07`) e tratar o 422 `DEV-07` no "Encerrar". A descrição da parcela vem pronta da API.

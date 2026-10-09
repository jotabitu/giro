# T-091 · Locação: renovação, atraso, cancelamento e encerramento · backend → orquestrador, frontend, qa, arquiteto, produto, seguranca

**O que foi feito** (`docs/api/locacoes.md`; CA-015-16 da LOC-2812, 17, 19 a 24 e o estorno do 25):

- **Renovação (`LOC-08`, `LOC-15`, `FIN-09`):**
  - `POST /api/locacoes/{id}/renovar/simular/` e `.../renovar/`, com `{periodos}` ou `{fim_previsto}`. Só valem em `ativa` ou `devolucao_atrasada`; nos outros estados, 409 `transicao_locacao`.
  - A renovação mantém o mesmo LOC. As parcelas novas começam no fim previsto atual, com o preço de hoje, e o `valor_periodo_centavos` e a diária passam a ser os de hoje. A numeração continua: LOC-2841 ganha as parcelas 6 e 7 de 7, de 32900, e as antigas ficam com 29940.
  - O aditivo sai pelo `contrato.gerar_aditivo` e vai para assinatura depois do commit, sem travar a renovação. O aviso aos gerentes depois de 7 dias é o da T-090.
  - A renovação não cria comissão.
  - A `devolucao_atrasada` volta a `ativa` quando o novo fim é futuro. O atraso que já tinha corrido fica em `atraso_anterior_dias` e `atraso_anterior_centavos`, e `calcular_atraso` o soma.
  - Com um cancelamento pendente ou aprovado, responde 409 `cancelamento_em_andamento`.
- **Atraso (`LOC-10`, `LOC-11`, `FIL-03`, `AUT-02`):**
  - O cálculo puro fica em `locacoes/fim.py`.
  - `selectors.calcular_atraso(locacao, momento)` devolve `{dias, valor_centavos, devolucao_considerada_em}` para o acerto da T-016.
  - A tarefa `aut_02_marcar_devolucao_atrasada` roda de hora em hora no Beat (`crontab(minute=0)`), por empresa, e é idempotente. Ela leva a locação para `devolucao_atrasada` no dia seguinte ao fim previsto, quando a devolução feita naquela hora já teria atraso. O evento de auditoria é `locacao.marcar_atraso` (`LOC-10`).
- **Cancelamento e encerramento antecipado (`LOC-12`, `LOC-13`, `APR-02`):**
  - `POST .../cancelamento/simular/` recebe `{data?}` e devolve os campos do contrato, mais `credito_dias`.
  - `POST .../cancelar/` recebe `{motivo, data?, forma_devolucao?}`, com `pix` como padrão ou `estorno_cartao`. O gerente, o administrador e quem tem a extra `cancelar_contrato` recebem 200 e o efeito vale na hora. O vendedor recebe 202 `{pedido_aprovacao}`. O vistoriador e o financeiro recebem 403.
  - A `data` não pode ser antes de hoje (400). Depois da retirada, se não sobra nenhum dia até o fim previsto, a resposta é 409 `sem_dias_restantes`: o caso é de devolução. O LOC-2790 cai nesse caso.
  - Em `encerrada` e `cancelada`, a resposta é 409 `transicao_locacao`. Com o encerramento já aprovado, é 409 `cancelamento_aprovado`.
  - **Antes da retirada:** a locação vai para `cancelada` na hora. As contas abertas são canceladas, e o que foi pago vira um `Reembolso` `a_fazer`, com aviso aos gerentes no sino. O veículo `reservado` volta a `disponivel` e a comissão fica `estornada`. O contrato e o aditivo que ainda não foram assinados são cancelados, e o link deixa de valer.
  - **Depois da retirada:** a locação continua `ativa`, com `encerramento_antecipado_aprovado_em`, `multa_encerramento_centavos` e `credito_encerramento_centavos`. As parcelas em aberto que vencem depois do dia são canceladas. A comissão fica `confirmada`. A devolução da T-016 faz o acerto e chama `services.encerrar`, e o status final é `cancelada`.
  - Cada mudança de status grava a auditoria com o motivo: `locacao.pedir_cancelamento`, `locacao.cancelar`, `locacao.aprovar_encerramento`, `locacao.recusar_cancelamento` e `locacao.encerrar`. Todas aparecem no histórico.
  - Quando o gerente recusa o pedido, o sinal apaga e quem pediu recebe no sino "Cancelamento da LOC-2812 recusado: <motivo>".
  - Na lista, o sinal `cancelamento_pendente` entra na aba "Precisam de ação", a situação fica "Pedido de cancelamento" e o pagamento mostra "Multa R$ 84,80". O detalhe ganhou o bloco `cancelamento`. Com um pedido pendente ou aprovado, `acoes.renovar` e `acoes.cancelar` ficam `false`.
- **`encerrar(locacao, devolvida_em=...)`**, para a T-016. Leva a locação a `encerrada`, ou a `cancelada` no encerramento antecipado. Grava `devolvida_em`, fecha o trecho e publica `locacoes.locacao_encerrada(locacao_id, veiculo_id, status, devolvida_em)`. O status do veículo fica com `vistorias` (`DEV-04`).
- **Financeiro:**
  - o model `Reembolso` (migração `0002`);
  - `devolver_ao_cliente`, `marcar_reembolso_feito` (com o comprovante no armazenamento privado), `estornar_comissao` e `cancelar_abertas(..., vencendo_depois_de=)`;
  - os selectors `pago_da_origem_centavos`, `abertas_vencendo_depois` e `reembolsos_da_origem`.
- **Veículos:** a transição `reservado` → `disponivel` agora existe, para a reserva cancelada. "Desbloquear" e "Voltar para a frota" passaram a conferir o status de origem e continuam recusando o reservado (409).
- **`docs/api/clientes.md`:** o exemplo da LOC-2836 trocou "devolve hoje" por "semanal" (decisão B, PR #104).

**Onde:**
- `backend/apps/locacoes/`: `fim.py` (novo), `services.py`, `selectors.py`, `calculo.py`, `contrato.py`, `eventos.py`, `tasks.py`, `models.py`, `api/`, a migração `0002` e o `README.md`.
- `backend/apps/financeiro/`: `models.py`, `services.py`, `selectors.py`, a migração `0002` e o `README.md`.
- `backend/apps/veiculos/models.py` e `services.py`, e `backend/config/settings/base.py` (o Beat).
- `docs/api/openapi.yaml` e `docs/api/clientes.md`.
- `tarefas/backlog.md`: as divergências e as dúvidas abaixo.

**Testes:**
- `tests/aceitacao/test_t091_locacao_fim.py`: 21 testes, todos com o código da regra no nome.
- O CA-015-19 conta o atraso a partir do `fim_previsto` da própria locação, com +1 h, +1 h 01, +23 h 59 e +24 h 01. Ele não fixa o dia 07 out, então não depende da data da LOC-2836 (T-104 e T-105). Usa uma filial aberta das 8h às 22h, porque na Filial Centro o horário (fecha às 18h) faria o `LOC-11` valer. O CA-015-20 usa o horário da Filial Centro.
- Os 9 `xfail` da T-091 saíram de `test_t015_locacoes.py`. O único `xfail` que sobra é o da T-092.

**Check** (rodei com o `rodar.sh`, com `--rm` e `POSTGRES_HOST`, na imagem `giro-backend:latest` reconstruída, que já tem weasyprint e nh3):
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `528 passed, 1 xfailed`. Antes eram 507 passed e 10 xfailed.
- O OpenAPI foi regerado com `--validate`, sem aviso e só com acréscimos. A única linha que saiu é a descrição provisória do bloco `cancelamento`.

**Para o produto** (no backlog, com o que o código faz):
1. [divergência] CA-015-23: na NMax mensal com 6 dias restantes, o critério dá multa de 6360, mas a `LOC-12` manda cobrar no mínimo 1 diária, que é 7990. O código e o teste seguem a regra (7990).
2. [divergência] A tabela de transições dos veículos não tem `reservado` → `disponivel`, que o CA-015-22 pede.
3. [decisão] `LOC-11`: quando a filial fecha antes de a tolerância acabar, o prazo passa para a abertura seguinte. No caso 1 do CA-015-20, uma devolução na segunda às 08:30 fica sem atraso; pela letra da regra, seriam 2 diárias.
4. [decisão] `LOC-08`: na renovação de uma locação atrasada, o atraso corrido continua cobrado, como diz o contrato. Só que as parcelas novas cobrem os mesmos dias, e esses dias são cobrados duas vezes.
5. [decisão] `LOC-12` na diária: as diárias não usadas voltam ao cliente (`credito_dias`).
6. [decisão] `LOC-13` no mensal em 4 semanais: o crédito desconta as semanais em aberto que o encerramento cancela.
7. [decisão] Renovação: continuam o desconto e os extras por período, e o plano especial de preço fixo vale pelo preço de hoje.

**Para o arquiteto (diferenças do contrato):**
- A simulação do cancelamento traz também `credito_dias`.
- O bloco `cancelamento` traz também `data`, `credito_centavos` e `cobrar_centavos`.
- A simulação da renovação devolve `fim_previsto_atual`, `fim_previsto`, `periodos`, `valor_periodo_centavos`, `parcelas_novas` e `total_centavos`.
- Códigos de erro novos: 409 `sem_dias_restantes`, `cancelamento_aprovado` e `cancelamento_em_andamento`, e 400 `forma_devolucao` (dinheiro, até a T-017).
- `encerrar` recebe `devolvida_em` e não a `Devolucao`, porque `vistorias` fica acima de `locacoes`. É o mesmo caso do `registrar_vistoria_saida`.
- `ContaReceber.observacao` da parcela nova diz "Renovação N".

**Para a seguranca:** o `Reembolso` guarda o comprovante no armazenamento privado (`caminho_privado`). A rota que o devolve chega com a T-017. As rotas novas usam `CRIAM` e o escopo de filial, e o cancelamento confere `pode(usuario, "locacoes_cancelar")` no serviço.

**Para o frontend:**
- **Detalhe da locação:** os botões "Renovar" (simular e confirmar) e "Cancelar" (simular, depois `cancelar`; com 202, mostrar "Pedido enviado ao gerente"), e o bloco `cancelamento`.
- **Lista:** o sinal `cancelamento_pendente`.
- **Aprovações:** o APR-02 aparece com o título "Cancelamento de locação" e o detalhe "LOC-2812 · Patrícia … · multa R$ 84,80".

**Para qa:** a T-105 (seed) pode usar `services.cancelar` para deixar o pedido pendente da LOC-2812 (CA-015-16). A carteira guarda `diaria_centavos` igual a 0, e o teste da Patrícia põe 7990.

**Próximo passo:** o orquestrador abre o PR. A T-016 liga a devolução em `calcular_atraso`, `multa_encerramento_centavos`, `credito_encerramento_centavos` e `encerrar`.

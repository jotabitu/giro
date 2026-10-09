# T-015 · Locação: reserva, ciclo de status e lista (parte 1 da divisão de 09 out) · backend → orquestrador, frontend, qa, arquiteto, produto, seguranca

A tarefa foi dividida em 09 out, e o dono confirmou. Este PR é a parte 1. Os contratos (CA-015-11 a 13) ficaram com a T-090. A renovação, o atraso, o cancelamento e o encerramento (CA-015-17, 19 a 24 e o estorno do 25) ficaram com a T-091. A troca de veículo (CA-015-18) ficou com a T-092, depois da T-016.

**O que foi feito:**
- **App `locacoes`** (`docs/api/locacoes.md`):
  - `POST /api/locacoes/simular/` e `POST /api/locacoes/`, que cria o rascunho com o código já reservado;
  - `GET` e `PATCH /api/locacoes/{id}/`, com o `PATCH` só em `rascunho`;
  - `POST /api/locacoes/{id}/confirmar/`;
  - `GET /api/locacoes/{id}/historico/`;
  - `GET /api/locacoes/`, com as abas, os filtros, a busca, as contagens e os indicadores;
  - `/api/planos-especiais/`, com `GET`, `POST`, `PATCH` e `desativar`.
- **Cálculo (`LOC-01` a `LOC-05`, `LOC-14`, `LOC-15`):**
  - A diária sai toda na retirada. A semanal vence a cada 7 dias. A mensal é mês fechado, à vista ou em 4 semanais (diferença na última), e com menos de um mês responde 400.
  - O plano especial troca o preço (Entregador 27900) ou desconta a partir de um período (Fidelidade: 109000, 109000, 98100, 98100).
  - Os extras somam por período, pelo valor do cadastro.
  - O preço é o de hoje na simulação e fica congelado na confirmação.
- **Confirmação, numa transação só:**
  - recusa os impedimentos: 422 `CLI-05`, `cliente_inativo`, `CLI-02` (categoria da CNH), `FIL-05` e `IMP-04` (com `detalhes.link`), e 409 `LOC-03`;
  - cria as contas a receber (parcelas e caução, com a origem `LOC-NNNN`) e a comissão de R$ 16,00 `pendente` (`FIN-09`);
  - com início futuro, leva o veículo a `reservado`.
  - A corrida pelo mesmo veículo para na restrição `uma_locacao_aberta_por_veiculo` e responde 409 `LOC-03`.
- **Desconto (`LOC-03`, `APR-01`):**
  - até o limite da configuração (5,00%), vale direto;
  - acima dele, o vendedor abre o pedido pela porta `comum.aprovacoes`, e as parcelas nascem sem desconto;
  - aprovado, as parcelas em aberto são refeitas; recusado, o desconto volta a 0 e a vendedora recebe no sino "Desconto da LOC-2856 recusado: <motivo>";
  - gerente e administrador dão o desconto direto.
- **Ativação:** a locação fica `ativa` quando tem a vistoria de saída, o contrato assinado e o 1º pagamento (parcela 1 **e** caução), em qualquer ordem. Na mesma transação, o veículo vira `alugado` e a comissão `confirmada` (paga em 05/11).
- **Rascunho:** com 24 h sem uso, vai para `cancelada` pela tarefa `locacoes_cancelar_rascunhos_sem_uso`, que roda de hora em hora.
- **Lista e sinais:**
  - os sinais `pagamento_atrasado` e `devolve_hoje`;
  - a `situacao` na ordem do contrato ("Devolução atrasada 25 dias", "Parcela 2 atrasada", "Aguardando assinatura", ...), além de `pagamento` e `acao_principal`;
  - os indicadores ativas, devolvem hoje (e até 12h), devolução atrasada com o destaque, e pagamentos atrasados em número e em centavos.
  - O vistoriador recebe 403 na lista. No detalhe, ele não vê nenhum `_centavos`, nem pagamento, preços, parcelas, desconto ou extras, e no histórico não vê os pagamentos.
- **Leituras para os outros apps (ADR 0015):**
  - `locacao_atual` do veículo, com o alerta "Atrasado";
  - `locacao_atual` e `ultima_locacao` do cliente, o filtro `com_locacao` e o contador `locacao_aberta` (`CLI-09`);
  - `indicadores.locacoes_ativas` e o contador `locacoes` da filial (`FIL-06`);
  - `locacoes_em_andamento` da categoria (o aviso do preço novo).
- **Financeiro mínimo** (o arquiteto confere):
  - os models `ContaReceber` e `Comissao`;
  - os serviços `criar_contas`, `ajustar_valor`, `cancelar_abertas`, `lancar_comissao`, `confirmar_comissao` e `marcar_paga`. Este último é a porta da baixa até a T-017: grava o pagamento e publica `financeiro.parcela_paga(parcela_id, cliente_id, origem_tipo, origem_id, tipo)`;
  - os selectors das parcelas, o resumo por origem numa query e `comissoes_confirmadas_centavos`.
  - `locacoes` chama o financeiro direto, porque o financeiro é nível 8 e locações é 10 (ADR 0011).
- **Contratos mínimo:** o model `ModeloContrato` e `contratos.selectors.modelo_publicado` (`IMP-04`).
- **`ConfiguracaoEmpresa`:** `tolerancia_atraso_minutos` (60), `desconto_sem_aprovacao_pct` (5.00) e `comissao_locacao_centavos` (1600), com migração.
- **`GIRO_MODULOS_ATIVOS`:** `locacoes` entrou no padrão. `contratos` fica para a T-090, porque ainda não tem rota nem tela que funcione.
- **`comum.dinheiro.formatar_reais`:** os textos prontos ("R$ 1.646,40").

**Onde:**
- `backend/apps/locacoes/`: `models.py`, `calculo.py`, `services.py`, `selectors.py`, `leituras.py`, `eventos.py`, `tasks.py`, `apps.py`, `api/`, a migração `0001` e o `README.md`.
- `backend/apps/financeiro/`: `models.py`, `services.py`, `selectors.py`, a migração `0001` e o `README.md`.
- `backend/apps/contratos/`: `models.py`, `selectors.py`, a migração `0001` e o `README.md`.
- `backend/apps/empresas/models.py` e a migração `0002`.
- `backend/comum/dinheiro.py`, `config/urls.py`, `config/settings/base.py` (o módulo e o Beat) e `docs/api/openapi.yaml`.

**Testes:**
- `tests/aceitacao/test_t015_locacoes.py`: 44 testes passam. Cobrem do CA-015-01 ao 10, o 14, o 15 e o 16 (menos a LOC-2812), a parte do 24 sobre a auditoria e o 25 (menos o estorno). Também cobrem:
  - os planos especiais;
  - o 404 fora da filial;
  - as leituras para veículo, cliente e filial, com a lista de veículos sem N+1;
  - o isolamento entre empresas.
- 13 ficam `xfail` com os números dos critérios: `T-090` (11 a 13), `T-091` (16 LOC-2812, 17, 19 a 24 e o estorno do 25) e `T-092` (18).
- `tests/aceitacao/carteira.py` carrega no banco as 42 locações da carteira de outubro (T-056), com as parcelas e os clientes. Com ela, o CA-015-16 confere a lista com o seed: 42 ativas, Rafael 25 dias e 2 atrasos somando 164640. A T-019 pode partir dele.
- A vistoria de saída (T-016), a assinatura (T-090) e a baixa (T-017) entram nos testes pelas mesmas portas que esses apps vão usar.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `486 passed, 13 xfailed`. Antes eram 442 passed.
- O OpenAPI foi regerado com `--validate`, sem aviso e só com acréscimos.
- Rodei no Postgres descartável, com `--rm` e `POSTGRES_HOST`, na imagem `giro-backend:latest` reconstruída. Não houve erro de import.

**Ajustes em testes de outras tarefas:**
- `test_t014_clientes.py`:
  - CA-014-21: `contagens.com_locacao` passou de `null` para 0 e `com_locacao_pct` para "0.00", porque o filtro de `locacoes` agora existe;
  - os dois fixtures que trocam fornecedores por falsos agora devolvem o de verdade no fim.

**Diferenças em relação ao contrato** (para o arquiteto conferir):
1. **`valor_periodo_centavos`:** na simulação e no `precos` do detalhe, é o do 1º período já com o desconto (CA-015-06: 31255). No model, `valor_periodo_centavos` é o preço do período sem descontos, congelado. É a base para refazer as parcelas no `APR-01` e para a multa da T-091.
2. **Campos a mais:**
   - a simulação devolve também `periodos` e `diaria_centavos`;
   - o detalhe traz `periodos`, `primeiro_vencimento`, `desconto: {status, pedido_aprovacao_id, pct}` (`null` sem pedido), `extras[].cobranca`, `parcelas[].total_parcelas` e `parcelas[].observacao`;
   - `acoes` traz também `editar` e `confirmar`.
3. **Fim previsto informado:** com `fim_previsto` no lugar de `periodos`, a API conta os períodos inteiros (fração conta como período) e devolve o fim do último período, que é o que foi cobrado.
4. **Aba `rascunhos`:** existe `?aba=rascunhos`, com a contagem dela, para retomar um rascunho. `canceladas` não mostra o rascunho que expirou.
5. **Filial da locação nova:** vem do `X-Filial` ou da única filial da pessoa. Com "Todas as filiais", a resposta é 400 (`filial`).
6. **`frota_alugada_pct`:** é a ocupação de 90 dias de veículos (`VEI-06`) quando há uma filial, e vem `null` com "Todas as filiais".
7. **`precisam_acao`:** considera só as abertas (atraso de devolução, parcela atrasada, aguardando assinatura). O cancelamento pendente entra na T-091.
8. **`acoes`:** seguem a regra mesmo para as rotas que chegam depois. `renovar`, `trocar_veiculo` e `cancelar` funcionam a partir da T-091 e da T-092; `registrar_devolucao` e `continuar_vistoria`, a partir da T-016. `imprimir_contrato` e `reenviar_contrato` ficam `false` até a T-090.
9. **`registrar_vistoria_saida`:** a assinatura é `registrar_vistoria_saida(locacao, *, km, concluida_em=None)`, e não `(locacao, vistoria)`, para `locacoes` não depender de `vistorias`, que está abaixo.
10. **Model, mais que no modelo de dados:**
    - `Locacao`: `periodos`, `precos_de`, `primeiro_vencimento`, `extras_rascunho`, `usado_em` e, no lugar da FK `aprovacao_desconto`, `desconto_status`, `desconto_pedido_pct` e `pedido_desconto_id` (sem FK, ADR 0019);
    - `ExtraLocacao`: `nome` e `cobranca`;
    - `ContaReceber`: `observacao`, ainda sem `movimento_caixa`, `renegociada_em`, `estorno_de` e `estornada_em`, que entram com a T-017.
11. **Tarefa dos rascunhos:** não existe código `AUT` para ela, e o nome ficou `locacoes_cancelar_rascunhos_sem_uso`.
12. **Ativação com o veículo fora de `disponivel` ou `reservado`:** por exemplo, um veículo que foi para a manutenção depois da reserva. A ativação responde 409 `transicao_veiculo`, e a ação que a disparou volta inteira. Quando a T-017 trouxer a baixa de verdade, vale decidir se o pagamento deve ficar e a ativação esperar.

**Dúvida para o produto:** está em `tarefas/backlog.md` como `[divergência]`. O preço da LOC-2836 (R$ 329,00 desde 30 set) não bate com a tabela, que mudou em 01 out (`LOC-15`).

**Para a Seguranca revisar:**
- As rotas de locações não têm `suporte_somente_leitura`, e por isso o suporte Giro não as lê. A linha leva o nome do cliente; a decisão de abrir com máscara ou não fica com a Seguranca.
- No detalhe do vistoriador, `sem_valores` tira os `_centavos` e os blocos de dinheiro. Na lista, o vistoriador recebe 403.

**Próximo passo para quem recebe:**
- **Frontend:** a Nova locação chama `simular` a cada mudança. Depois vem `POST` (rascunho) e `confirmar`. A lista e o detalhe seguem o contrato com as diferenças acima.
- **QA:** a T-019 pode reaproveitar `carteira.py`. Os xfail já levam o número da tarefa nova.
- **Backend:**
  - T-016: chamar `registrar_vistoria_saida` e, antes dela, `impedimentos_para_retirada` e `VEI-03`;
  - T-017: a baixa publica o mesmo `financeiro.parcela_paga` de `marcar_paga`;
  - T-090: publicar `contratos.contrato_assinado(origem_tipo, origem_id, tipo, assinado_em)`;
  - T-091: o `cancelamento_pendente` e o bloco `cancelamento`.

**Ajuste depois da ADR 0020 (merge da main em a38fe3a):**
- `locacoes/api/serializers.py` não formata mais momento: o `_momento` virou `DateTimeField` puro (só `allow_null`), sem `default_timezone`. Os momentos vão como `datetime` com fuso, e o formato `Z` vem para todos quando a T-093 ligar o renderizador de `comum`. Até lá, as rotas de locações saem com `-03:00`, como aprovações e veículos.
- `test_loc_01_ca_015_01_lucas_semanal_street` compara o `fim_previsto` como momento, não como texto.
- Check: ruff, `ruff format --check`, mypy e `makemigrations --check` limpos; pytest `487 passed, 16 xfailed` (13 da T-015 e 3 da ADR 0020); OpenAPI regerado com `--validate` e sem diferença.

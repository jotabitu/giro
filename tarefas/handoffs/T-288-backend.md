# T-288 (parte 1) · Movimentações: backend · backend → frontend (T-289), qa, arquiteto, seguranca

**O que foi feito:**
- **App `movimentacoes`** (ADR 0028, nível 11): `LocalApoio`, `Movimentacao` (código `MOV-0001`, máquina de estados, índice único parcial de uma aberta por veículo e os dois `CHECK` do modelo), `ParadaMovimentacao` e `FotoChegadaMovimentacao`.
- **Rotas do contrato** (`docs/api/movimentacoes.md`): quadro, lista com os filtros, detalhe, criar (com "Sair agora"), editar a agendada, iniciar, cancelar, chegada e saída da parada (despesa pela `FIN-05`, nota opcional), fotos da vistoria rápida (uma por vez, sem metadados, URL de 15 minutos), chegada no destino (km, combustível, 4 fotos, "Recebido por", documento vencido, transferência), `pessoas/`, `recebedores/` e os locais de apoio (criar, listar, inativar, reativar).
- **Quem leva e quem recebe (T-300, T-302):** `contas.selectors.pessoas_da_filial` é a base das duas listas e da validação. `pessoas/` e `recebedores/` excluem o financeiro. O administrador conta em todas as filiais.
- **Veículos:**
  - status `em_movimentacao` (com as transições, o tom `info` e a contagem na Frota);
  - origem `movimentacao`;
  - `travar` público;
  - `transferir(..., origem=movimentacao)` aceita `indisponivel`, `em_manutencao` e `a_venda`;
  - blocos `movimentacao_aberta` (lista e ficha) e `movimentacoes` (só ficha; ausente para vistoriador e financeiro);
  - `acoes.movimentar`, `motivo_movimentar` e `aviso_baixar`, e `transferir` e `registrar_km` pelas regras novas;
  - filtros `?em_movimentacao=true` e `?movimentavel=true`;
  - o km manual recusado com o veículo em movimentação (409 `MOV-05`).
- **Baixa com movimentação aberta (opção B do dono, contrato da T-311):** sem 409. `baixar` publica `veiculos.veiculo_baixado(veiculo_id, motivo_texto)` na transação. O assinante `movimentacoes.eventos.cancelar_pela_baixa` cancela a movimentação aberta, agendada ou iniciada, com "Veículo baixado: roubo". As despesas ficam, e não há transferência. A falha no assinante desfaz a baixa.
- **Financeiro:** origem `movimentacao` na despesa (`origem_tipo`, `origem_id`, `origem_codigo`), `lancar_despesa(..., origem=)`, `sem_nota` e `origem` na representação, e `POST /api/financeiro/despesas/{id}/nota/` (409 `nota_existente`, evento `despesa.anexar_nota`).
- **Locações:** `confirmar` trava a linha do veículo (ADR 0028, item 3). Há também `locacoes.selectors.locacao_aberta(veiculo)`.
- **Contas:** `pode.movimentacoes` (`gerir`, `levar`, `nao`). O item `movimentacoes` aparece para `gerir` e, para `levar`, só com uma movimentação aberta que a pessoa leva (contador registrado por `movimentacoes`).
- **AUT-06:** o veículo `em_movimentacao` com o documento vencendo não muda de status e gera a tarefa urgente aos gerentes.

**Onde:** `backend/apps/movimentacoes/`, `backend/apps/veiculos/{models,services,selectors}.py`, `backend/apps/financeiro/{models,services,selectors}.py` e `api/`, `backend/apps/contas/{selectors,navegacao}.py`, `backend/apps/locacoes/{services,selectors}.py`. Migrações: `movimentacoes/0001_movimentacoes`, `veiculos/0005_em_movimentacao`, `financeiro/0008_despesa_origem`.
**Contrato:** `docs/api/movimentacoes.md`, `veiculos.md` (T-300 e T-311), `financeiro.md` e `contas.md`; `docs/api/openapi.yaml` regenerado; no frontend, `api:gerar` e `typecheck` sem erro depois de o falso das despesas (`testes/falsos/falso-financeiro.ts`) ganhar `sem_nota` e `origem`, e os testes de componentes com 298 passed.
**Regras cobertas:** MOV-01 a MOV-06, VEI-01 a VEI-04, VEI-06, FIN-05, FIN-06, APR-03, USR-09. Testes em `backend/tests/aceitacao/test_t288_movimentacoes.py` (28, com `test_mov_05_aut_06_documento_vence_em_movimentacao`):
- `test_mov_*` pelos CA-246-01 a 19;
- a baixa: `test_mov_03_baixa_cancela_movimentacao_iniciada`, `test_mov_03_baixa_na_transferencia_nao_transfere`, `test_mov_03_baixa_cancela_agendada` e `test_mov_03_falha_no_assinante_desfaz_a_baixa`;
- `test_mov_03_movimentavel_exclui_alugado_e_reservado` (T-300);
- o isolamento entre empresas.

**Decisões e pontos para o arquiteto (não mudei contrato):**
- **Menu:** `movimentacoes` **não** entrou em `GIRO_MODULOS_ATIVOS`, para o menu não levar a uma tela que ainda não existe. O PR das telas (T-289) acrescenta. Na posição, segui o contrato no `menu_completo` (Operação, depois de `manutencoes`). Nos `menu_inicio`, que o contrato não diz, pus no fim da Operação do gerente e do vendedor e no fim do menu do vistoriador. Falta a linha em `contas.md`.
- **Suporte "só ver":** quadro, lista, `pessoas/`, `recebedores/` e locais leem. O detalhe da movimentação **não** lê, porque traz as fotos com URL assinada, e a ADR 0013 (item 2) não deixa. Para a **segurança** confirmar.
- **Editar a agendada:** troca as paradas apagando as antigas, que ainda não andaram. Se isso fere o "nada de negócio é apagado", o caminho é um `ativo` na parada.
- **Auditoria da baixa:** o `movimentacao.cancelar` grava o motivo "Veículo baixado: roubo", mas não grava `detalhes.origem = baixa_veiculo`, porque `auditar` não tem campo de detalhes. O motivo já distingue.
- **`acoes.baixar`** segue a regra de sempre (a sugestão de 409 da T-300 ficou sem efeito pela T-311).

**O que ficou para a parte 2 (t-288b):** a saída da rota `POST /api/veiculos/{id}/transferir/` (junto com o frontend), o teste de concorrência (iniciar e confirmar a locação ao mesmo tempo; a trava está feita) e os totais de despesas de outubro do CA-246-02 (7.101,70), que pedem o seed completo.

**Próximo passo para quem recebe:**
- **Frontend (T-289):**
  - trocar `lib/api/tipos-movimentacoes.ts` pelos tipos gerados. O formato bate, e ganhou `cancelada_em` e `motivo_cancelamento`;
  - pôr `movimentacoes` em `GIRO_MODULOS_ATIVOS` quando as telas entrarem;
  - mostrar `acoes.aviso_baixar` no diálogo da baixa.
  - O vistoriador recebe a movimentação sem os campos `_centavos`.
- **QA:** CA-246-01 a 23.
- **Segurança:** o suporte no detalhe e as fotos da chegada.

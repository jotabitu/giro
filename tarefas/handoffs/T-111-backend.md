# T-111 · Código das decisões da T-091 · backend → orquestrador, qa, frontend

**O que foi feito:** as decisões de 09 out 2026 (T-110, opção A) e a `LOC-13` da T-113 no código.
- **Renovação depois do prazo (`LOC-08`, CA-015-26):** `montar_renovacao` vê se a renovação está dentro do prazo (fim previsto mais a tolerância, com a `LOC-11`, por `atraso_desde`). Dentro do prazo, o período novo começa no fim antigo. Depois, começa na hora da renovação, mesmo com a locação `ativa`, e o atraso até ali vai para `atraso_anterior_*`, cobrado no acerto (`calcular_atraso` já somava). Antes, só a `devolucao_atrasada` guardava o atraso, e o período começava sempre no fim antigo: os dias entre o fim e a renovação eram pagos duas vezes.
- **Extras e plano na renovação (`LOC-08`, `LOC-15`, CA-015-27):** extras por período pelo valor atual do cadastro. `ExtraLocacao.valor_centavos` passa a esse valor, com evento `locacao.renovar_extra`, como o `valor_periodo_centavos`. O plano desativado é ignorado, inclusive o de desconto, e a renovação usa a tabela. O desconto e o plano de desconto contando os períodos desde o começo já funcionavam e agora têm teste.
- **Diária em blocos de 24 h (`LOC-12`, CA-015-28):** `fim.diarias_nao_usadas` conta os blocos inteiros de 24 h até o fim previsto. É o mesmo que contar os dias usados desde o início com fração como dia, e continua certo depois de uma renovação atrasada. A simulação só tem a data e usa a hora do início, com o aviso `LOC-12`. O acerto da devolução recalcula pela hora real (`locacoes.services.credito_do_encerramento`).
- **Mensal em 4 semanais (`LOC-13`, CA-015-29):** o saldo é crédito das semanas − parcelas canceladas − multa e pode ficar negativo. Antes, o crédito parava em 0 e o semanal saía mais barato que o mês à vista. Entram só as parcelas em aberto que vencem depois do dia e dentro do mês em curso, como na T-113. `Locacao.credito_encerramento_centavos` virou `CentavosComSinalField` (migração `0003`). No acerto, o item `semanas_nao_usadas` sai como cobrança quando o líquido é negativo, com a conta na descrição, e vai para a conta `acerto` ao encerrar.

**Onde:** `backend/apps/locacoes/fim.py`, `services.py` (`_inicio_da_renovacao`, `montar_renovacao`, `renovar`, `calcular_encerramento`, `credito_do_encerramento`), `models.py` + `migrations/0003_credito_encerramento_com_sinal.py`, `api/serializers.py`; `backend/apps/vistorias/services.py` (`calculados`, `TIPO_DA_CONTA`); `backend/apps/financeiro/selectors.py` (`parcelas_canceladas_vencendo_entre`); testes em `backend/tests/aceitacao/test_t111_decisoes_t091.py`.

**Diferenças em relação ao contrato** (combinadas com o arquiteto em 09 out; emendas neste PR para ele revisar):
- `POST /api/locacoes/{id}/cancelamento/simular/` ganha `parcelas_canceladas_centavos` (0 fora do mensal em 4 semanais) e `avisos: [ { codigo, mensagem } ]` (na diária, `LOC-12` "O acerto final usa a hora da devolução."; nos outros, `[]`). `credito_semanas.valor_centavos` continua bruto, e `devolver`/`cobrar` são líquidos. Está em `docs/api/locacoes.md` e no `openapi.yaml`.
- `docs/api/locacoes.md` (renovar): início do período depois do prazo, extras pelo preço de hoje, plano desativado.
- `docs/api/vistorias.md`: `semanas_nao_usadas` como crédito ou cobrança, e `dias_nao_usados` pela hora real.
- `docs/decisoes/modelo-de-dados.md`: `credito_encerramento_centavos` (centavos±) e `atraso_anterior_*` na `Locacao`.
- `cancelamento.credito_centavos` no detalhe da locação pode vir negativo (mensal em 4 semanais).

**Regras cobertas:** `LOC-08` (`test_loc_08_ca_015_26_*`, `test_loc_08_ca_015_27_*`), `LOC-12` (`test_loc_12_ca_015_28_*`), `LOC-13` (`test_loc_13_ca_015_29_*`, `test_loc_13_ca_015_21_patricia_mes_a_vista_nao_muda`).

**Check** (com `rodar.sh`, imagem `giro-backend:latest`): ruff, `ruff format --check`, mypy e `makemigrations --check` limpos; pytest `589 passed, 3 xfailed` (antes 567; a `origin/main` dá `567 passed, 3 xfailed`). Numa primeira rodada, 2 testes de `apps/plataforma` (`test_imp_05_*`) falharam e não se repetiram: passaram sozinhos, com o app inteiro e na suíte inteira de novo. Fica o registro, caso apareçam de novo. O teste da Patrícia na T-091 ganhou os dois campos novos, e o comentário velho do CA-015-23 saiu (pedido do handoff da T-110).

**Leituras minhas (pode contestar):**
- Extra desativado no cadastro antes da renovação continua, com o valor atual do cadastro. Está como `[decisão]` no backlog, para o produto.
- O crédito da diária no acerto usa a hora em que a vistoria de chegada foi concluída (`momento_da_devolucao`), a mesma do atraso.

**O que ficou de fora:** a T-114 (`DEV-01`, `DEV-02`, `DEV-07`): parcela do dia no acerto, ordem da caução e 422 da devolução antecipada. O `pagar_com_caucao` não mudou. No 1º caso do CA-015-29, a conta de 26500 sai certa porque não há caução paga.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR e pedir a revisão do arquiteto nas emendas de contrato. Depois, a T-114.
- **QA:** validar pelos CA-015-26 a CA-015-29.
- **Frontend:** a simulação do cancelamento tem `avisos` (mostrar como na simulação da locação) e `parcelas_canceladas_centavos`. O item `semanas_nao_usadas` pode vir em `itens` (cobrança), e não só em `creditos`.

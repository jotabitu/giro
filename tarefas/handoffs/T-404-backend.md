# T-404 · Reembolsos e pendências no menu (backend)

Branch `t-404-menu-reembolsos`, a partir da `origin/main` (484f1621). Achado do E2E da T-375 (item 2).

## O que mudou

- `backend/apps/contas/navegacao.py`: itens `reembolsos` ("Reembolsos") e `pendencias_pagamento` ("Pendências do pagamento") no grupo Financeiro do `menu_completo`, depois de `despesas`, como na tabela de `docs/api/contas.md`.
  - `reembolsos`: `pode.lancamento_avulso` (administrador, gerente e financeiro, os mesmos perfis da view), recurso `locacoes_vistoria`, atividade aluga, módulo `financeiro`.
  - `pendencias_pagamento`: `pode.financeiro_pagar` (administrador e financeiro), recurso `recebimento_parceiro` (PLT-12), módulo `financeiro`.
  - Os `menu_inicio` das variantes não mudaram: o contrato não lista os itens neles.
- `relatorios/selectors.py`: contadores `reembolsos` (`a_fazer`, pela filial do escopo) e `pendencias_pagamento` (abertas, da empresa), como em `painel.md`. Novo `financeiro.selectors.pendencias_abertas()`.
- `docs/api/contas.md`: o exemplo do Essencial (CA-ASS-22) passa a citar Reembolsos (vem pela tabela) e o mapa de `GIRO_MODULOS_ATIVOS` ganha as duas chaves. Arquiteto: confira se concorda.
- OpenAPI sem mudança (o formato do menu é o mesmo).

## Testes

- `test_plt_12_menu_reembolsos_e_pendencias_por_perfil_e_plano` e `test_plt_12_contadores_de_reembolsos_e_pendencias` (`test_t380_reembolsos_pendencias.py`).
- Atualizados: navegação por perfil e Essencial (`test_t011_contas.py`) e contadores da Lúcia (`test_t017_financeiro.py`).

## Para o frontend e o QA

- As telas do #439 passam a ser alcançáveis pelo menu. No Essencial, o administrador vê Reembolsos e não vê Pendências do pagamento.

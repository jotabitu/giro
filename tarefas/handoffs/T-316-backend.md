# T-316 · Suporte nas escritas das movimentações e o rastro das fotos da chegada · backend → qa, segurança, orquestrador

**O que foi feito** (achados de `docs/seguranca/2026-10-16-t315-movimentacoes.md`):
- **M-01:** o suporte em "ver e editar" recebe 403 `PLT-07`, e não 500, em toda escrita das movimentações: criar, editar, iniciar, cancelar, chegada e saída da parada, foto e chegada no destino, e criar, inativar e reativar local de apoio (opção A do dono, T-319, CA-246-24). O detalhe e as listas continuam legíveis. Foi feito por `suporte_proibido` nas views (`ESCRITA` nas que também leem).
- **B-01:** cada foto da chegada grava `movimentacao.foto_chegada` na movimentação (`posicao`, `foto_id`, `substituiu`, sem URL, regra `MOV-05`). Contrato atualizado em `movimentacoes.md`.
- **B-02:** `exigir_chegada` vem antes de ler o arquivo em `enviar_foto` e `sair_parada`. Quem não registra a chegada recebe 403 mesmo com arquivo inválido.
- **B-03:** `comum.arquivos.nota_limpa` valida a nota e tira o EXIF quando é imagem; o PDF passa como veio. Vale para toda nota de despesa (`lancar_despesa` e `anexar_nota`), inclusive a da parada.

**Onde:** `backend/apps/movimentacoes/api/views.py`, `backend/apps/movimentacoes/services.py`, `backend/apps/financeiro/services.py`, `backend/comum/arquivos.py`, `docs/api/movimentacoes.md`.
**Contrato:** sem rota nova; OpenAPI sem mudança.
**Regras cobertas:** PLT-07, MOV-02 (`test_plt_07_suporte_ver_e_editar_so_le_as_movimentacoes`), MOV-05 e AUD-01 (`test_aud_01_foto_da_chegada_trocada_fica_na_auditoria`), B-02 (`test_mov_02_quem_nao_registra_a_chegada_recebe_403_antes_de_ler_o_arquivo`), AUD-05 e FIN-06 (`test_aud_05_fin_06_nota_da_parada_sem_metadados`). Os 2 `xfail` estritos da T-315 saíram. Rodei t288, t315, t017, t178, t018 e `test_permissoes_das_rotas`; tudo passa, menos `test_fin_05_fin_07_caixas_e_despesas_no_painel_do_financeiro` (t017), que falha também sem esta mudança: os contadores do painel da Lúcia trazem `veiculos: 86` porque o menu do financeiro ganhou a Frota. Nada aqui toca o painel nem os menus; fica para quem mexeu no menu acertar o teste ou o menu.
**O que ficou de fora:** a varredura do suporte nas outras rotas de escrita (`lancada_por`, `aberto_por` etc. no financeiro) é a T-317, do qa.
**Próximo passo para quem recebe:**
- qa: T-317 pode começar; CA-246-24 coberto.
- segurança: conferir B-01 a B-03 fechados.

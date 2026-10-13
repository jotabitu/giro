# T-164 · Decisões da T-027: cor obrigatória e célula longa no .csv · arquiteto, produto → orquestrador, backend, qa

**O que foi feito:** registrei as duas decisões de 12 out 2026 sobre as dúvidas do backend na T-027 (PR #167). A cor é a opção A do dono do produto (análise em `C:/Users/Jota/Documents/giro-produto/analise-t027.md`, fora do git). A célula longa é a opção B do arquiteto (`analise-t027-arquiteto.md`).

**Parte do arquiteto (commit f0fec06):**
- `docs/api/importacao.md`: `cor` em negrito entre as colunas obrigatórias de veículos. A célula com mais de 1.000 caracteres deixa a linha com erro no `.xlsx` e no `.csv` e é guardada com os primeiros 1.000 caracteres. No `.csv`, a célula longa com quebra de linha é aspas sem fechar e recusa o arquivo ("A linha N tem aspas sem fechar. Confira o arquivo e envie de novo."). O `field_size_limit` sobe para 5 MB.
- `backend/apps/importacao/planilha.py`: a coluna `cor` passa a obrigatória, e a leitura do `.csv` muda.
- 4 testes em `backend/tests/aceitacao/test_t027_importacao.py`:
  - `test_imp_02_celula_longa_no_csv_deixa_a_linha_com_erro`
  - `test_imp_02_celula_longa_igual_no_xlsx_e_no_csv`
  - `test_imp_02_csv_com_aspas_sem_fechar_e_recusado`
  - `test_imp_02_celula_longa_em_coluna_descartada_nao_da_erro`
  
  O teste do cabeçalho passa a esperar `cor` em `colunas_faltando`.

**Parte do produto:**
- `docs/qa/criterios/T-027.md`:
  - nota das decisões no topo;
  - CA-027-05 com a cor entre os campos obrigatórios ("Cor em branco", `validacao`) e a célula longa nos dois formatos;
  - CA-027-15 com a planilha sem a coluna `cor` (`colunas_faltando: ["cor"]`) e o `.csv` com aspas sem fechar;
  - CA-027-21 com a cor obrigatória na planilha modelo;
  - CA-027-23 novo: mesma célula longa no `.xlsx` e no `.csv`, corte em 1.000, coluna descartada sem erro, quebra de linha aceita até 1.000 caracteres.
- `tarefas/backlog.md`: a seção da T-164 saiu.
- `tarefas/feito.md`: linha da T-164 com o PR #173.

**Regras cobertas:** IMP-02.

**Seed:** o caso 83 + 3 = 86 não muda. As 86 linhas de `_frota()` têm cor ("Preta"), e os 3 erros continuam sendo placa, chassi e ano do modelo.

**O que ficou de fora:**
- **QA:** conferir a mensagem da linha sem cor. `OBRIGATORIAS_VEICULO` em `linhas.py` não lista `cor`, então o "Cor em branco" que o backend relatou na T-027 deve vir do serviço do cadastro. O critério pede `campo: cor`, `codigo: validacao`, "Cor em branco". Se a mensagem sair diferente, avise o produto.
- **Frontend (tela `Onboarding-Importar`):** nada novo; a mensagem de aspas sem fechar aparece como vier da API.

**Próximo passo:** o orquestrador abre o PR #173.

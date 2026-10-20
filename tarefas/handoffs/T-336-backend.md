# T-336 · Parser do CRLV-e no leiaute do Detran · backend → qa, orquestrador

**O que foi feito:** a correção candidata do qa (handoff da T-331), aplicada em `_candidatos`. Abaixo do rótulo, a busca segue pelas `LINHAS_ABAIXO` (3) linhas até a primeira que tem um pedaço a até `FOLGA_DA_COLUNA` (12) colunas da coluna do rótulo. Uma linha só com texto de outra coluna (o bloco do seguro DPVAT) não encerra mais a busca. Os pedaços dessa linha vão para o validador do mais perto para o mais longe (folga 0 quando se sobrepõem à coluna, como antes). Os validadores continuam decidindo o que vale. `LINHAS_ABAIXO` ficou em 3.

**Onde:** `backend/integracoes/leitura_documentos/crlv.py`; `backend/tests/aceitacao/test_t331_calibracao_crlv.py` sem os 12 `xfail` estritos (a docstring e o comentário dizem o que a T-336 corrigiu).

**Branch:** `t-336-parser-crlv-detran`, empilhada sobre a `t-331-calibracao-crlv` (PR #360, ainda fora da `main`), com a `origin/main` já dentro.

**Regras cobertas:** VEI-08. `test_t331_calibracao_crlv.py` com 22 passando (os 9 campos nos dois formatos, o proprietário nunca lido, e a leitura inteira pelo processo filho). `test_t265_leitura_crlv.py` e `test_t328_seguranca_crlv.py` seguem passando, e os 3 `xfail` estritos da T-328 continuam lá, para a T-329. ruff, ruff format --check e mypy limpos no backend inteiro (imagem com WeasyPrint 70.0 e pypdf 6.21.1).

**O que ficou de fora:** o catálogo completo (T-337). CRLV-e de outros estados não é preciso: o dono confirmou (19 out 2026) que o leiaute é o mesmo em todos os estados, só muda o cabeçalho do Detran.

**Próximo passo para quem recebe:**
- **qa:** rodar de novo com os dois CRLV-e reais do dono, fora do repositório, e mandar só o resultado por campo.

**Resultado do qa com os CRLV-e reais (19 out 2026):** com a correção, o parser leu os 9 campos nos dois documentos (carro e moto, Detran-CE), sem campo vazio nem errado, e não leu o proprietário. Antes eram 4 de 9. Marca e modelo foram lidos certo, mas no catálogo local ainda caem em dica (T-337). Continua pendente um CRLV-e de outro estado.

# T-323 · Contadores do painel do financeiro com Veículos no menu · backend → qa, orquestrador

**O que foi feito:** decidido pelo contrato que o item Veículos do financeiro leva contador. `docs/api/painel.md` diz que em `GET /api/painel/contadores/` "só vêm as chaves dos itens que a pessoa vê" e só abre exceção para `despesas` de quem não aprova; `docs/api/contas.md` dá `contador: "veiculos"` ao item, sem condição de permissão. Desde a T-287 o financeiro vê Veículos (`pode.veiculos` = `ver`), então o código está certo e o teste estava velho. O teste passou a esperar `veiculos: 86` nos contadores da Lúcia.
**Onde:** `backend/tests/aceitacao/test_t017_financeiro.py` (`test_fin_05_fin_07_caixas_e_despesas_no_painel_do_financeiro`). Nenhum código de produção mudou.
**Contrato:** sem mudança; OpenAPI sem mudança.
**Regras cobertas:** FIN-05, FIN-07, USR-05. `tests/aceitacao/test_t017_financeiro.py` inteiro: 34 passam.
**O que ficou de fora:** nada.
**Próximo passo para quem recebe:** orquestrador: abrir o PR; a `main` volta a ter o t017 verde.

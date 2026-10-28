# T-402 · Rótulos do modo suporte no backend · backend → orquestrador, frontend

Achado do Frontend na T-372.

**O que foi feito:**
- `GET /api/auth/eu/` com o token de suporte: `eu.suporte` traz `permissao_rotulo` ("Só ver" ou "Ver e editar", o rótulo de `PermissaoSuporte`) e `fim_rotulo` ("Expira às 15:30", a hora do `fim` em `America/Sao_Paulo`), como `docs/api/contas.md` descreve para a faixa. Os dois estão no `SuporteDoEuSerializer` e no OpenAPI, obrigatórios.
- O `chave` do cartão de Configurações ganhou `suporte` na enum (o cartão é da T-379). O `ramo` já estava na enum e não mudou.
- OpenAPI regenerado com `--validate`: 0 erros, os 2 avisos de antes. Os nomes dos schemas não mudaram e não há colisão nova.

**Testes:**
- `test_plt_07_ca_011_26_faixa_e_permissoes_do_suporte` (`tests/aceitacao/test_t011_contas.py`): o `eu.suporte` do "só ver" vem com "Só ver" e "Expira às 15:30" (fim 18:30 UTC), e o `ver_editar` vem com "Ver e editar".
- `test_t011_contas.py` e os testes de Configurações e suporte: 222 passed.
- ruff, ruff format e mypy: sem erro.

**Para o frontend:** a faixa pode usar `eu.suporte.permissao_rotulo` e `eu.suporte.fim_rotulo` direto; rode `npm run api:gerar` depois do merge.

**Próximo passo:** o orquestrador revisa e abre o PR.

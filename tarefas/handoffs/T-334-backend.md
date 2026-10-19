# T-334 · Dois testes quebrados na main · backend → qa, orquestrador

**O que foi feito:**
- `tests/aceitacao/test_t129_painel_e_marca.py::test_usr_05_contadores_seguem_o_menu`: os contadores da Lúcia passam a esperar `veiculos: 86`. Veículos entrou no menu do financeiro na T-287 e leva contador como em qualquer perfil; é a mesma correção que a T-323 fez no `test_t017_financeiro.py`. O código não mudou.
- `movimentacoes.LocalApoio`: `CAMPOS_AUDITORIA = {"inteiro": ["nome", "nome_busca"]}`. É nome de estabelecimento (lava-jato, oficina, despachante), não dado pessoal, e vai inteiro na auditoria, como o `nome` da filial. Sem migração.

**Onde:** `backend/tests/aceitacao/test_t129_painel_e_marca.py`, `backend/apps/movimentacoes/models.py`.

**Regras cobertas:** USR-05; AUD (classificação de campos, ADR 0014). `tests/test_campos_sensiveis.py` e `test_t129_painel_e_marca.py` passando; ruff, ruff format --check e mypy limpos (com o pypdf instalado no contêiner descartável, que a imagem de teste ainda não tem até a T-327).

**O que ficou de fora:** nada.

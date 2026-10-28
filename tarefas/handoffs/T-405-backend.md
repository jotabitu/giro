# T-405 · Token de suporte com a data simulada · backend → orquestrador, qa

**O que foi feito:**
- `emitir_token_suporte` (`backend/comum/autenticacao.py`) calculava o `exp` como `fim - token.current_time`: o `fim` do `AcessoSuporte` sai do relógio do Giro (com `GIRO_DATA_REFERENCIA`, o dia simulado) e o `current_time` é o relógio real do simplejwt. Com a data simulada no passado, o token já nascia vencido e `/suporte/entrar` respondia 401 "O acesso de suporte terminou" (item 4 do E2E da T-375).
- Agora o `exp` é `agora real + (fim - relogio.agora())`: só o tempo que falta até o `fim`, como nos tokens do login, que o simplejwt emite e confere pelo relógio real. A duração do acesso não muda: o `fim` continua no relógio do Giro e `conferir_acesso_suporte` o confere a cada requisição. Em produção a data simulada não existe (ADR 0021) e os dois relógios coincidem.

**Regras cobertas:** PLT-07 e ADR 0021. Testes em `backend/tests/test_t405_token_suporte_relogio.py`, sem congelar o relógio do JWT (o `relogio_jwt` dos testes de aceitação escondia o problema):
- `test_t405_plt_07_entra_com_o_token_de_suporte_com_a_data_simulada`: data simulada 21 dias atrás, abre o acesso e `GET /api/auth/eu/` responde 200 com o suporte. Sem a correção, 401 (conferido).
- `test_t405_plt_07_exp_leva_a_duracao_do_acesso`: acesso de 15 minutos dá `exp` entre 14 e 15 minutos à frente do relógio real.
- Ruff, format e mypy limpos; suíte inteira do backend: 1733 passed, 7 skipped, 6 xfailed.

**O que ficou de fora:** nada.

**Próximo passo para quem recebe:**
- QA: repetir o item 4 do E2E da T-375 com a data simulada ligada.

# T-189 · Revisão do cartão e da conta principal · seguranca → orquestrador, backend (T-185, achados), devops (B-01)

**O que foi feito:** revisão do que a T-184 (PR #238) pôs na `main` pela ADR 0023: token do cartão, pagador e webhook da conta principal, baixa da fatura. A exceção da `suspensa` ao `somente_leitura` e a escrita barrada ao suporte ainda não têm código (rotas da T-185): foram revisadas no contrato e nas travas comuns (`EmpresaOperando`, `conferir_rota_do_suporte`) e viraram requisitos com teste para a T-185.
**Onde:** `docs/seguranca/2026-10-15-t189-cartao-conta-principal.md`; `backend/tests/aceitacao/test_t189_seguranca_cartao.py`.
**Regras cobertas:** PLT-07, PLT-13, PLT-14; ADR 0007, 0014, 0023.
**Achados (nenhum alto):**
- M-01 (média): o corpo bruto do aviso (`WebhookRecebido.corpo["bruto"]`) guarda `creditCard.creditCardToken` em claro. `xfail` estrito.
- M-02 (média): `Asaas._chave` usa a chave da conta principal quando a da subconta volta vazia. `xfail` estrito.
- B-01 (baixa, devops): Sentry pode receber o `asaas-access-token` e o corpo do aviso.
- B-02 (baixa): `ParceiroRecusou` na baixa deixa o aviso sem resultado.
Os quatro estão no backlog, sob a T-189, esperando número.
**Testes:** `ruff check`, `ruff format --check` e `mypy` limpos no backend; `test_t189_seguranca_cartao.py`: 2 passaram (nenhuma rota com dado do cartão; `CartaoGuardado` sem token no `repr`), 2 `xfail` (M-01, M-02). `test_t184_faturas.py` segue passando (20).
**O que ficou de fora:** 2 etapas recentes para trocar a forma e cancelar (T-199); o sandbox do Asaas (token devolvido pela página, pendente da T-184).
**Próximo passo para quem recebe:** o backend da T-185 lê a seção "Para a T-185" do relatório antes das rotas; quem corrigir M-01 ou M-02 tira o `xfail` do teste correspondente.

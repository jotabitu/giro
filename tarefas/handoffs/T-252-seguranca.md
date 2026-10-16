# T-252 · Revisão do link do convite (rota) · seguranca → orquestrador, backend, frontend (T-251), produto

**O que foi feito:** revisão da rota `POST /api/usuarios/{id}/link-convite/` da T-250 (PR #272). A tela vem na T-251; a lista do que conferir nela está no relatório. Por isso, a tarefa continua em andamento.
**Onde:** `docs/seguranca/2026-10-16-t252-link-convite.md`; `backend/tests/aceitacao/test_t252_seguranca_convite.py`.
**Regras cobertas:** USR-01, PLT-07, AUD-01.
**Resultado:**
- Os sete pontos conferem, já provados pelos testes da T-250:
  - só administrador;
  - suporte com 403 `PLT-07` nos dois modos;
  - link uma vez, com o token no fragmento e só o hash no banco;
  - `no-store`;
  - 5 e 20 por hora, antes do serviço;
  - evento sem token;
  - o anterior vence na hora, com 410.
- Guarda nova: `test_usr_01_limite_do_link_conta_por_empresa` (a chave do limite leva o schema).
- B-01 (baixa, backend): `contas_enviar_convite` manda o link de um convite já invalidado; `xfail` estrito `test_usr_01_email_de_convite_invalidado_nao_sai`.
**Testes:** ruff, formatação e mypy limpos; os testes `usr_01` da T-250 e os novos passam (7 passaram, 1 `xfail`).
**O que ficou de fora:** a tela (T-251). A `[divergência]` 404 ou 410 do CA-248-12 fica com o produto: a segurança não se opõe a nenhum dos dois.
**Próximo passo para quem recebe:**
- orquestrador: numerar o B-01 (backend);
- frontend: ler "Para conferir na tela" antes de fechar a T-251;
- eu revejo a tela quando a T-251 entrar.

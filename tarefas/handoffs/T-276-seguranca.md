# T-276 · Migração com papéis de banco separados · seguranca → orquestrador, backend, devops

**O que foi feito:** decisão e correção do achado 1 do devops na T-264. A função `auditoria_expurgar` continua de `giro_expurgo`, e schemas e tabelas, de `giro_migracao`. A troca de dono no `post_migrate` passa a dar `CREATE` no schema ao expurgo só durante o `ALTER FUNCTION ... OWNER TO` e a tirar logo depois, na mesma transação. A migração segue sem superusuário. A correção é pequena e só de banco, por isso feita aqui.
**Onde:** `backend/apps/auditoria/banco.py`; `backend/tests/test_papeis_de_banco.py` (novo); `docs/seguranca/2026-10-16-t276-papeis-banco.md`.
**Regras cobertas:** AUD-01, AUD-02; ADR 0016 (teste `test_adr_0016_*`).
**Testes:**
- o teste novo falha com o `banco.py` da `main` e passa com a correção;
- `test_auditoria.py` e `test_isolamento.py` passam (25 no total);
- ruff, formatação e mypy limpos;
- num Postgres descartável com o `01-papeis.sh`, `migrate_schemas --shared` e o schema da empresa nova (seed) passam logados como `giro_migracao`. Com o `banco.py` da `main`, o mesmo erro da T-264.
**O que ficou de fora:**
- não mexi no `01-papeis.sh` nem no teste de subida do devops;
- o seed com `config.settings.test` num banco limpo para em `veiculos_veiculo does not exist`, também como superusuário: não é dos papéis e não investiguei.
**Próximo passo para quem recebe:**
- backend: revisar o PR (nada obrigatório além disso);
- devops: o teste de subida da T-264 pode usar `giro_migracao` e `giro_app` separados; no banco gerenciado, o mesmo SQL do `01-papeis.sh`.

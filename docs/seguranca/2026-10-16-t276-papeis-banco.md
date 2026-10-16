# T-276 · Migração com os papéis de banco separados

**Data:** 16 out 2026 · **Agente:** segurança · **Regras:** AUD-01, AUD-02 · **ADR:** 0016
**Base:** achado 1 do devops na T-264 (PR #271, `tarefas/handoffs/T-264-devops.md`); `backend/apps/auditoria/banco.py`; `infra/postgres/01-papeis.sh`; migração `auditoria.0003`.

## O problema

Com `giro_migracao` e `giro_app` separados, `migrate_schemas` falha em `ALTER FUNCTION auditoria_expurgar(date) OWNER TO giro_expurgo` com `permission denied for schema public`. O PostgreSQL só troca o dono de uma função se quem pede puder assumir o papel novo (`giro_migracao` é membro de `giro_expurgo`, pelo `01-papeis.sh`) **e** se o dono novo tiver `CREATE` no schema da função. `giro_expurgo` não tem: no PostgreSQL 15 em diante, o `public` não dá `CREATE` a ninguém, e os schemas das empresas são de `giro_migracao`. Em desenvolvimento e nos testes nunca apareceu, porque tudo roda como superusuário.

Reproduzido duas vezes:
- num teste que roda `aplicar_permissoes` como `giro_migracao` (`SET ROLE`, sem superusuário) num schema dele;
- num Postgres descartável com o `01-papeis.sh`, com `migrate_schemas` logado como `giro_migracao` e o `banco.py` da `main`: o mesmo erro da T-264.

## Decisão

Mantém o desenho da ADR 0016. Muda só como a troca de dono acontece, e a migração continua sem superusuário.

| Objeto | Dono | Por quê |
| --- | --- | --- |
| Schemas (`public` e das empresas), tabelas, sequências, triggers | `giro_migracao` | roda a migração e cria o schema da empresa nova; `giro_app` não é dono de nada e não mexe em trigger |
| Função `auditoria_expurgar` (`SECURITY DEFINER`) | `giro_expurgo` | o trigger só deixa apagar quando `current_user = 'giro_expurgo'` e o evento tem mais de 5 anos |
| Papel `giro_expurgo` | sem login, sem superusuário | ninguém entra como ele; só a função roda com ele |

- **`CREATE` temporário:** na rotina de permissões (`aplicar_permissoes`, no `post_migrate` de cada schema), `giro_migracao`, dono do schema, dá `CREATE` a `giro_expurgo`, troca o dono da função e tira o `CREATE` logo em seguida, na mesma transação. O PostgreSQL só confere esse `CREATE` no momento da troca. Depois, o expurgo não cria nada no schema.
- **`giro_migracao` continua membro de `giro_expurgo`.** Isso não amplia nada: o papel da migração já é dono das tabelas e dos triggers, que é mais do que o expurgo pode.
- **Descartadas:**
  - superusuário ou `CREATEROLE` na migração (o que a tarefa proíbe);
  - `CREATE` permanente para o expurgo (dá mais poder do que precisa a um papel `SECURITY DEFINER`);
  - deixar a função com `giro_migracao` (o trigger recusaria o expurgo, e a função rodaria com os poderes do dono das tabelas).

## O que mudou

- `backend/apps/auditoria/banco.py`: `GRANT CREATE` antes e `REVOKE CREATE` depois do `ALTER FUNCTION ... OWNER TO`, com o motivo no comentário. É pequeno e só de banco, como a tarefa permite.
- `backend/tests/test_papeis_de_banco.py` (novo): a migração sem superusuário passa a função ao expurgo (rodando duas vezes, como o `post_migrate`), `giro_app` executa a função, `PUBLIC` não executa, e o expurgo não fica com `CREATE` no schema.

## Verificação

- Teste novo: falha com o `banco.py` da `main` (`permission denied for schema`) e passa com a correção. `comum/tests/test_auditoria.py` (imutabilidade, `TRUNCATE` e expurgo) e `tests/test_isolamento.py` seguem passando; ruff, formatação e mypy limpos.
- Postgres descartável com o `01-papeis.sh`, logado como `giro_migracao`:
  - `migrate_schemas --shared` passa;
  - o schema `motorapida`, criado pelo seed, também passa;
  - nos dois schemas, a função é de `giro_expurgo`;
  - `giro_expurgo` fica sem `CREATE`;
  - `giro_app` executa a função e insere eventos, mas não apaga.
- Não sobrou outro SQL que exija superusuário: procurei `CREATE EXTENSION`, `OWNER TO`, `ALTER ROLE` e `SECURITY DEFINER` no backend.

## Para os outros

- **Devops:**
  - o `infra/scripts/teste-subida-producao.sh` (T-264) pode passar a usar `giro_migracao` em `DATABASE_URL_MIGRACAO` e `giro_app` em `DATABASE_URL`, em vez do superusuário nas duas;
  - no banco gerenciado, aplicar o mesmo SQL do `01-papeis.sh`, inclusive `ALTER SCHEMA public OWNER TO giro_migracao` e `GRANT giro_expurgo TO giro_migracao`.
- **Backend:** nada obrigatório além de revisar o PR. Se um dia outra rotina trocar o dono de um objeto para um papel que não é dono do schema, ela segue o mesmo padrão e ganha teste em `test_papeis_de_banco.py`.

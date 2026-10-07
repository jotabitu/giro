# Papéis de banco separados e expurgo da auditoria

**Status:** aceita · 07 out 2026 · complementa a 0010 (item 3) · revisão de segurança T-032, S-10 · depende do devops para os ambientes

## Contexto

A 0010 protege a auditoria com um trigger que recusa `UPDATE` e `DELETE`, liberado no expurgo por `SET LOCAL giro.expurgo_auditoria = 'on'`. A segurança apontou (S-10): qualquer sessão pode ligar essa variável; trigger de linha não pega `TRUNCATE`; e o papel que roda a aplicação é dono das tabelas (o django-tenants cria os schemas), então pode desligar ou apagar o trigger.

## Decisão

1. **Dois papéis de banco** em todos os ambientes (o devops cria e guarda as senhas):
   - `giro_migracao`: dono dos schemas e tabelas; roda `migrate_schemas` e a criação do schema de empresa nova. Usado só no deploy e por `plataforma.services.criar_empresa` (que pede uma conexão própria para criar o schema).
   - `giro_app`: o papel com que o Django atende requisições e roda o Celery. Recebe `SELECT, INSERT, UPDATE, DELETE` nas tabelas de negócio, e **só `SELECT, INSERT`** nas tabelas `auditoria_eventoauditoria` (com `REVOKE UPDATE, DELETE, TRUNCATE`). Não é dono de nada, então não altera nem remove trigger.
   - Os `GRANT` de cada schema novo são aplicados pela mesma rotina que cria o schema (um `ALTER DEFAULT PRIVILEGES` por schema).
2. **Triggers** na tabela de eventos de cada schema: `BEFORE UPDATE OR DELETE` (por linha) e `BEFORE TRUNCATE` (por comando), levantando exceção. A variável de sessão sai do desenho.
3. **Expurgo** de 5 anos (`AUD-02`) por uma função `auditoria_expurgar(limite date)` `SECURITY DEFINER`, de um papel próprio `giro_expurgo`, com `search_path` fixo. Ela apaga só linhas com `ocorrido_em < now() - interval '5 years'` e recusa um `limite` mais recente que isso; `UPDATE` não existe em caminho nenhum. O trigger reconhece o expurgo pelo `current_user = 'giro_expurgo'`. `giro_app` tem só `EXECUTE` na função; quem chama é a tarefa mensal.
4. **Cadeia de hash** (opcional, depois da fase 1): `hash_anterior` e `hash` por schema, para detectar alteração feita por quem tem acesso de dono do banco.
5. Desenvolvimento e testes podem usar um papel só, **exceto** nos testes de imutabilidade, que sobem com `giro_app` para provar o `REVOKE`.

## Consequências

- `UPDATE`, `DELETE` e `TRUNCATE` falham para a aplicação mesmo com injeção de SQL; só o dono do banco consegue mexer, e a cadeia de hash (quando entrar) mostra.
- O devops cria os três papéis no Compose, nos ambientes e no CI, e separa as credenciais de migração das de execução (`DATABASE_URL` e `DATABASE_URL_MIGRACAO`).
- O backend ajusta a migração da auditoria da T-001 para os triggers e a função acima e acrescenta os testes de `TRUNCATE` e de expurgo recusado.
- Não trava a T-001: o desenho dos papéis entra antes de homologação; os triggers entram já.

# Apagamento da empresa cancelada no 90º dia

**Status:** aceita · 15 out 2026 · detalha a 0002, a 0010 e a 0016 para a `AUD-08` (T-194) · revisão da segurança na T-199

## Contexto

Com o cancelamento no MVP (`PLT-06`, decisão do dono de 14 out 2026), a `AUD-08` passa a valer: os dados da empresa ficam guardados por 90 dias a partir do dia em que ela vira `cancelada` e são apagados de vez no 90º dia, com aviso 7 dias antes. A tarefa que apaga tem de existir antes do 90º dia do primeiro cancelamento real.

Três coisas tornam a decisão cara de desfazer: apagar não tem volta; os dados da empresa estão em três lugares (o schema dela, o storage com o prefixo `<schema>/` da ADR 0009 e algumas linhas no `public`); e o papel com que a aplicação roda (`giro_app`, ADR 0016) não é dono do schema e não consegue apagá-lo, nem apagar a auditoria, que recusa `DELETE` e `TRUNCATE`.

## Decisão

1. **Apagar a empresa é apagar o schema inteiro.** `DROP SCHEMA <schema> CASCADE`, que leva os dados de negócio, os usuários (ADR 0008) e a auditoria da empresa juntos. Nada de apagar tabela por tabela: um app novo não precisa lembrar de entrar no apagamento.
2. **Pela conexão de migração.** O `DROP` roda com o papel `giro_migracao` (dono dos schemas), pela mesma conexão própria que `plataforma.services.criar_empresa` usa para criar o schema (ADR 0016, item 1). A função `plataforma.banco.apagar_schema(empresa_id)` é o único lugar do código que faz `DROP SCHEMA`:
   - recebe o `empresa_id`, nunca um nome de schema vindo de fora, e lê o `schema_name` da `Empresa` no `public`;
   - recusa o `public`, qualquer nome fora do padrão de schema de empresa, e a empresa que não esteja `cancelada` com `apagar_em` ≤ hoje e `apagada_em` nulo (conferido de novo com a `Empresa` travada);
   - monta o nome com `psycopg.sql.Identifier`, nunca por concatenação.
   O `auto_drop_schema` do django-tenants continua desligado: apagar a linha da `Empresa` nunca apaga schema.
3. **Ordem e retomada.** `plataforma.services.apagar_empresa(empresa_id)`: (a) apaga os objetos do prefixo `<schema>/` no storage privado; (b) apaga o schema; (c) limpa o `public` (contrato `cancelamento.md`, "O que fica no `public`"); (d) grava `apagada_em` e o evento `empresa.apagar` na auditoria da plataforma. Cada passo pode rodar de novo sem erro (prefixo vazio, `DROP SCHEMA IF EXISTS`, linhas já apagadas). Se falhar no meio, `apagada_em` continua nulo e a tarefa do dia seguinte retoma; a falha vai ao Sentry.
4. **O que fica no `public`.** A linha da `Empresa` (sem os dados de contato), as faturas da assinatura e a auditoria da plataforma ficam: são registro de cobrança e fiscal do próprio Giro e a prova de que o apagamento aconteceu (`AUD-02`). O padrão está em `[decisão]` no backlog, para o produto confirmar. `subdominio` e `schema_name` ficam reservados; o `empresa_id` nunca volta (ADR 0013).
5. **Tarefa.** `plataforma.aud_08_apagar_empresas`, diária às 03:30, no `public`, uma empresa por vez, na fila padrão. O worker que a roda precisa da `DATABASE_URL_MIGRACAO`. O aviso de 7 dias é outra tarefa, `plataforma.aud_08_avisar_apagamento` (09:00).

## Consequências

- O worker do Celery passa a ter a credencial de migração. A segurança (T-199) avalia se a tarefa precisa de uma fila e de um worker só dela; o desenho da função não muda com isso.
- Os backups do banco e do storage guardam a empresa depois do 90º dia até saírem da rotação. O devops informa o prazo, e a T-199 confere se ele cabe na `AUD-08`.
- Testes: o apagamento de uma empresa não toca o schema nem os arquivos de outra (`test_aud_08_nao_apaga_outra_empresa`); a reativada dentro dos 90 dias não é apagada (`test_aud_08_nao_apaga_reativada`); a função recusa `public` e nome fora do padrão. Os testes que sobem com `giro_app` (ADR 0016, item 5) provam que a aplicação sozinha não consegue apagar um schema.
- A `AUT` da tarefa fica com o produto, se ele quiser registrá-la na tabela de automações, como a `AUT-16` do expurgo.

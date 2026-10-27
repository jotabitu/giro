# Registro das restaurações testadas

Restauração que não foi testada não conta como backup (ADR 0033, item 3). Antes do primeiro cliente e depois **uma vez por mês**, quem cuida da infra roda `sh infra/backup/restaurar-teste.sh` e acrescenta uma linha aqui, no mesmo PR ou num commit `chore(backup): restauração de AAAA-MM-DD`.

**O que o script confere:** restaura o backup mais recente do banco num volume descartável (sem arquivamento e sem porta), sobe o Postgres restaurado, confere que as tabelas de migração e da plataforma existem, roda o `migrate_schemas` do backend de produção contra ele (não pode aplicar nada) e restaura uma amostra de 5 arquivos do último snapshot do restic.

**Passo manual que o script não faz:** abrir uma foto restaurada pela URL assinada, como o usuário abriria. Suba o backend de produção apontando para o banco restaurado e para a cópia dos arquivos, peça a URL de uma foto de vistoria e abra no navegador. Anote o resultado na coluna "Foto". Para recuperação até o minuto, rode o script com o horário-alvo (`"2026-11-02 14:30:00-03"`) uma vez por trimestre.

| Data | Quem | Ponto restaurado | Duração | Resultado | Foto pela URL assinada | Observações |
| --- | --- | --- | --- | --- | --- | --- |
| *(nenhuma ainda: a conta do provedor não foi contratada; a primeira entra na subida de produção)* | | | | | | |

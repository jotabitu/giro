# T-266 · Produção recusa subir sem as variáveis do S3 · backend → devops

**O que foi feito:** `config/settings/prod.py` recusa subir com `S3_BUCKET`, `S3_CHAVE_DE_ACESSO` ou `S3_CHAVE_SECRETA` ausentes, vazias ou só com espaço ("Defina S3_BUCKET: vazia ou ausente não é aceita em produção."), logo depois da conferência de `GIRO_ARMAZENAMENTO=s3`, como a T-157 faz com o e-mail e os pagamentos. `S3_ENDPOINT_URL` e `S3_REGIAO` seguem opcionais: vazias, o boto3 usa os padrões da AWS (`comum/arquivos.py` passa `None`).

**Onde:** `backend/config/settings/prod.py`, `backend/tests/test_producao.py` (o ambiente de produção dos testes ganhou as três variáveis).

**Contrato:** sem mudança de rota nem de OpenAPI.

**Testes:** `test_t266_prod_recusa_s3_sem_bucket_ou_chave` (as três variáveis, com vazio, espaço e ausente) e `test_t266_prod_sobe_sem_endpoint_nem_regiao`; `tests/test_producao.py` inteiro passa (71).

**O que ficou de fora (devops):** os comentários de `infra/deploy/homologacao.env.example` e `producao.env.example` ainda dizem "prod.py não confere os S3_*"; agora confere bucket e chaves. `infra/scripts/teste-subida-producao.sh` já preenche as três e segue subindo. O `.env.example` da raiz usa outros nomes (`S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`), que o `base.py` não lê; só importa no desenvolvimento, que usa o armazenamento falso, mas vale alinhar.

**Próximo passo para quem recebe:** (devops) atualizar os dois comentários e, se quiser, os nomes do `.env.example`.

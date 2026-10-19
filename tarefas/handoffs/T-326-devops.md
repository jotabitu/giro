# T-326 · Comentários e nomes do S3 nos .env.example · devops

**O que foi feito:** os comentários de infra/deploy/homologacao.env.example e producao.env.example agora dizem que o prod.py recusa S3_BUCKET, S3_CHAVE_DE_ACESSO e S3_CHAVE_SECRETA vazios ou ausentes (T-266) e que S3_ENDPOINT_URL e S3_REGIAO podem ficar vazios. O .env.example da raiz passou de S3_ACCESS_KEY, S3_SECRET_KEY e S3_REGION para S3_CHAVE_DE_ACESSO, S3_CHAVE_SECRETA e S3_REGIAO, os nomes que o ase.py lê. Sem valor real em nenhum arquivo.

**Onde:** .env.example, infra/deploy/homologacao.env.example, infra/deploy/producao.env.example.

**Base:** a branch parte de origin/main com o merge de origin/t-266-s3-obrigatorio-prod (o #348 ainda não estava na main). Se o #348 entrar antes, o merge some sozinho.

**Testes:** só comentários e nomes de variável em arquivos de exemplo; nenhuma outra referência aos nomes antigos no repositório.

**Próximo passo para quem recebe:** (orquestrador) sem PR por pedido; integrar junto com o #348.
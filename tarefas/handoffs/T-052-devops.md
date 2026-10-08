# T-052 · Ajuste de produção apontado na T-050 · devops → orquestrador, backend, frontend, seguranca

**O que foi feito:**
- **R-03 (T-050):** `config/settings/prod.py` recusa subir com chave ou pepper iguais aos do `.env.example` (a chave é comparada sem o id), com a mesma chave em `GIRO_CHAVE_DADOS_PESSOAIS` e `GIRO_CHAVE_SEGREDOS`, com chave que não decodifica para 32 bytes, com pepper de menos de 32 bytes e com pepper igual a `DJANGO_SECRET_KEY` ou `JWT_SIGNING_KEY`. `.env.example` ganhou o comando para gerar o pepper e o aviso da trava.
- **`GRANT giro_expurgo TO giro_migracao`** no `infra/postgres/01-papeis.sh`, antes dos demais `GRANT`. Volume de dev já criado: `make down V=1` ou rodar o `GRANT` à mão.
- **`GIRO_REDES_PROXY` por ambiente:** dev já estava no `.env.example`. Criados `infra/deploy/homologacao.env.example` e `producao.env.example` (só o que difere do dev, sem valor real). `prod.py` agora também recusa rede inválida e `/0` (que confiaria em qualquer endereço). Os CIDR dos modelos são exemplos; a sub-rede real do proxy reverso se define quando o ambiente existir.
- **Quadro:** T-052 saiu do `backlog.md` e entrou em `feito.md`.

**Avaliação dos pontos do frontend sobre a CSP (sem mudança de código):**
- `img-src`: nenhuma tela carrega imagem externa hoje e o host do S3 não está definido. Quando a T-012/T-014 trouxerem logo, foto e prévia de documento, o frontend lê a origem de `S3_ENDPOINT_URL` em execução no `middleware.ts` e a acrescenta a `img-src` (e a `frame-src` se houver PDF embutido). Alternativa: o Django entregar o arquivo pela mesma origem.
- `connect-src 'self'`: correto, `NEXT_PUBLIC_API_URL` fica vazia em todos os ambientes (ADR 0013). O Sentry do frontend vai precisar do host do DSN.
- `force-dynamic` no layout raiz: aceito. `_next/static` segue com cache longo; só o HTML deixa de ser estático. Registrar no PR.
Texto também em `infra/README.md`.

**Onde:** `backend/config/settings/prod.py`, `backend/tests/test_producao.py`, `infra/postgres/01-papeis.sh`, `infra/deploy/{homologacao,producao}.env.example`, `infra/README.md`, `.env.example`, `tarefas/`.

**Testes** (`test_r03_*` e `test_prod_recusa_rede_de_proxy_aberta_ou_invalida`): `tests/test_producao.py` 15 passam, `ruff check`, `ruff format --check` e `mypy` verdes, rodados num venv temporário fora do Docker (o orquestrador pediu para não subir o compose); `check-env.sh` ok.

**Não verificado:** a suíte inteira do backend (depende de Postgres) e o `01-papeis.sh` num Postgres real; confiar no CI. O frontend não foi tocado, então não rodei o check dele.

**Próximo passo para quem recebe:** orquestrador abre o PR. Ao criar homologação e produção, definir a sub-rede real em `GIRO_REDES_PROXY` e gerar as três chaves no cofre.

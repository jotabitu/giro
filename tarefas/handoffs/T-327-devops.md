# T-327 · Imagem giro-backend:latest com pypdf · devops

**O que foi feito:** a imagem `giro-backend:latest` foi reconstruída a partir de `origin/t-265-leitura-crlv` (PR #352, que acrescentou `pypdf>=6.21.1,<7` ao `backend/requirements.txt`, ADR 0026 item 3). Alvo `dev` (padrão do Dockerfile), contexto só com `backend/` e `infra/docker/`. Conferido dentro da imagem: `pypdf 6.21.1`. Não mexi na pilha `giro` nem no `giro-backend-pg`; construí só essa imagem.

**Conferido, sem mudança:** `infra/docker/backend.Dockerfile` instala `requirements.txt` (alvo `producao`) e `requirements-dev.txt` (alvo `dev`, que já inclui o primeiro), então o pypdf entra nos dois. O pypdf é Python puro: não pede pacote apt novo na imagem nem no CI. O CI (`.github/workflows/ci.yml`) faz `pip install -r requirements-dev.txt` nos jobs de backend, com cache por `backend/requirements*.txt`, então o requirements novo invalida o cache e instala sozinho. Nenhum arquivo de infra mudou; o diff da T-265 contra a main em `infra/`, `.github/`, Makefile e compose é vazio.

**Testes:** `import pypdf` dentro de `giro-backend:latest`.

**Próximo passo para quem recebe:** (backend, QA) worktrees já rodam com o pypdf. Quem usa a pilha `giro` deve reconstruir o `backend` depois do merge do #352. Sem PR por pedido.

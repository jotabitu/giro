# T-361 · Pillow 13 e auditoria de dependências · devops → orquestrador, frontend, seguranca

**O que foi feito**

- **A-01 · Pillow 13.** `backend/requirements.txt`: `Pillow>=11.1,<13` virou `Pillow>=13,<14` (instala a 13.0.0). **Motivo (para o PR, é troca de versão maior):** a 12.3 tinha 37 avisos do `pip-audit` (CVE e GHSA), todos corrigidos só na 13.0, e o limite `<13` impedia a correção. O Pillow decodifica todo upload de imagem (vistoria, CNH, CRLV-e, logo, movimentação). Com a 13: `pip-audit -r requirements.txt` sem aviso; nenhuma mudança de código.
- **M-04 · auditoria.** `make auditoria-deps` (`infra/scripts/auditoria-deps.sh`): `pip-audit` no backend (qualquer aviso) e `npm audit --omit=dev` no frontend (alto e crítico). Exceções com validade e justificativa em `infra/auditoria/excecoes.txt`, lidas por `infra/scripts/auditoria-excecoes.mjs` (exceção vencida ou mal escrita falha a auditoria). Workflow novo `.github/workflows/auditoria.yml`: PR e push que mudam dependência ou a lista, e toda segunda. Como registrar a exceção: `infra/README.md`, seção "Auditoria de dependências".

**Onde:** `backend/requirements.txt`, `Makefile`, `infra/scripts/auditoria-deps.sh`, `infra/scripts/auditoria-excecoes.mjs`, `infra/auditoria/excecoes.txt`, `.github/workflows/auditoria.yml`, `infra/README.md`.

**Testes** (um contêiner de cada vez, imagem `giro-backend` reconstruída da branch, banco `giro`, `--create-db`): `apps/empresas/tests/test_logo.py`, `comum/tests/test_arquivos.py`, `tests/test_arquivos_dev.py` e os `test_t013`, `t014`, `t016`, `t090`, `t129`, `t153`, `t265`, `t288`, `t315`, `t328` e `t331`: **319 passaram**. A recusa por `DecompressionBombError` e o lado máximo do logo seguem valendo (estão em `test_arquivos` e `test_logo`). O CI inteiro não rodou aqui (Actions sem minutos, `ci-actions-limite`); rodei só esses testes e o `pip-audit`. O filtro de exceções foi testado à mão: exceção válida tira o aviso, vencida dá erro.

**ACHADO QUE O CI NOVO VAI APONTAR (npm audit já falha hoje):** `next` crítico (GHSA-2464-fhr4-w9xw, execução remota na otimização de imagem com SVG; e GHSA-p3m5-59mp-jv5r, negação de serviço com Server Actions), `postcss` alto (GHSA-6g55-p6wh-862q, GHSA-r28c-9q8g-f849) e `zod` alto (GHSA-mrhx-c7xc-m3w5). O `npm audit` diz que há correção, e `next ^15.5.0` e `zod ^4.6.5` parecem caber no limite atual (provavelmente só o `package-lock.json`). Não mexi no frontend. Não pus exceção: são avisos reais. Até o frontend atualizar o lock, o workflow `auditoria.yml` fica vermelho nos PRs que tocam dependência.

**Também:** o Pillow 13 avisa que `Image.getdata` some na 14 (só em `test_logo.py`, linhas 210 e 215; código da aplicação não usa). Fica para quando a 14 entrar.

**Próximo passo para quem recebe:** (orquestrador) abrir o PR; criar tarefa para o **frontend** atualizar `next`, `postcss` (do `next`) e `zod` e rodar `make auditoria-deps`; (segurança) conferir o A-01 e o M-04; (devops, depois) chamar o script no deploy quando o desenho de produção (M-02) existir.

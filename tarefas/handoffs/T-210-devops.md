# T-210 · Fotos no desenvolvimento sem bloqueio da CSP (D-06 da T-025) · devops → orquestrador

**Causa:** o armazenamento "falso" (`GIRO_ARMAZENAMENTO=falso`, o padrão em dev) assinava as URLs com a base fixa `https://arquivos.invalid/`. O navegador não alcança esse host e a CSP (`img-src 'self' data: blob:`) o bloqueia.

**O que foi feito (sem tocar na CSP, que continua estrita):**
- `config/settings/base.py`: `GIRO_ARQUIVOS_FALSOS_BASE`, padrão `https://arquivos.invalid` (testes e produção não mudam). `dev.py` a troca por `/api/arquivos-dev`, URL relativa e de mesma origem.
- `comum/arquivos.py`: o provedor falso monta a URL com essa base; a assinatura HMAC foi para `assinar()`, usada também pela rota.
- `comum/arquivos_dev.py` (novo) e `config/urls.py`: a rota `/api/arquivos-dev/<caminho>` só existe quando a base é relativa (ou seja, só com `config.settings.dev`). Confere assinatura e validade de 15 min como o S3 faria, serve o conteúdo guardado com o tipo certo, `Cache-Control: private, no-store`, `nosniff`. 403 para assinatura adulterada ou link vencido, 404 se o arquivo não está na memória.
- `tests/test_arquivos_dev.py`: 4 testes [AUD-05] (mesma origem e abre, base dos testes continua inválida, assinatura adulterada, link vencido).

**Verificação:** ruff e mypy limpos em `comum` e `config`; pytest do arquivo novo mais `test_rotas`, `test_permissoes_das_rotas` e `test_producao`: 44 passaram. Não rodei a suíte inteira, nem subi o compose para ver a foto na tela. A resolução da rota com `config.settings.dev` não foi conferida em execução.

**Limite conhecido:** o armazenamento falso guarda na memória do processo. Foto enviada pelo backend só abre servida pelo backend (é o caso do dev, com um processo); worker e beat não enxergam.

**Fica para o QA (branch t-025-ponta-a-ponta, PR #204):** tirar do E2E a tolerância à CSP das fotos (D-06) e passar a conferir que as fotos da comparação da devolução aparecem e o console fica limpo. Não mexi nessa branch.

**Aviso:** em S3 real (homologação e produção) nada muda aqui; quando o bucket entrar, a origem dele precisa ir em `img-src` (ver avaliação da T-052 em `infra/README.md`).

**Quem recebe:** orquestrador abre o PR; avisar o backend que `comum/arquivos.py` e `config/urls.py` mudaram.

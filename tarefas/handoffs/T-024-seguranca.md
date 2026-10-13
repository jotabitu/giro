# T-024 · Revisão de segurança do MVP · seguranca → orquestrador, backend, devops, produto

**O que foi feito:** apliquei o checklist de `.claude/agents/seguranca.md` ao que está na `main` (a8509a3). Cobri:

- acesso e 2 etapas (T-011);
- clientes e dados pessoais (T-014);
- auditoria e exportação (T-018), com a decisão de 12 out: CPF e CNH omitidos no evento e só a auditoria em CSV no MVP;
- financeiro e webhooks (T-017);
- isolamento entre empresas;
- uploads, cabeçalhos e configuração de produção;
- segredos versionados no repositório público.

Revisei também o PR #160 (`origin/t-136-permissoes-perfil`, dec30bc), como pede a T-136. A revisão foi feita lendo o código, sem subir o compose nem rodar testes. Cada achado tem arquivo e linha conferidos. Os achados antigos (S-, C-, R-, P-, F-) não foram reabertos.

**Onde:** este arquivo. As tarefas propostas estão no topo da "Fase 1 · MVP" em `tarefas/backlog.md`, sem número, como `M-01` a `M-06`.

## Parecer do PR #160 (T-136)

**Aprovar com uma ressalva, a M-01.** Ela é pequena e pode entrar no próprio PR antes do merge.

O que está certo no PR:

- O 403 por perfil está no backend, por `permission_classes` com `com_padrao`, e não só no serializer. São 403 ao vistoriador:
  - lista e ficha do cliente;
  - preços e extras;
  - lista de locações.
- O recorte de valores do vistoriador vale nas respostas que ele abre:
  - em veículos, por `veiculos.selectors.sem_valores`, aplicado depois do serializer;
  - em vistorias, devolução, avarias e agenda, por `vistorias.selectors.sem_valores`, que tira também o bloco `acerto`;
  - no detalhe e no histórico da locação.
- A ficha do financeiro (`do_financeiro`) não traz documento, CNH, endereço, referência nem análise.

Para achar caminhos esquecidos, conferi por AST todas as views da branch que ficam com as permissões padrão. A única que leva dinheiro ao vistoriador é a da M-01.

## Achados

Nenhum alto. Ficam 4 médios e 2 baixos.

### M-01 · média · Vistoriador recebe os preços dos planos especiais (PR #160, `USR-09`)

- **Onde:** `backend/apps/locacoes/api/views.py:324`, na branch do PR. `PlanosEspeciaisView.get_permissions` devolve as permissões padrão no GET, e `PlanoEspecialSerializer` (`api/serializers.py:382`) traz `preco_centavos` e `desconto_pct`.
- **Reprodução:** João (vistoriador) faz `GET /api/planos-especiais/` e recebe 200, com o preço e o desconto de cada plano. A `USR-09` diz que nenhum valor em dinheiro aparece para ele.
- **Sugestão:** no GET, usar a mesma lista de quem lê locações (`LEEM_A_LISTA`), para o vistoriador receber 403. Ele não usa planos: chega à vistoria pela agenda. Teste `test_usr_09_vistoriador_nao_ve_planos_especiais`.

### M-02 · média · `[decisão]` Vendedor recebe custo de manutenção e rendimento do veículo

- **Onde:** `backend/apps/veiculos/selectors.py`, `representacao` com `detalhe=True`. O bloco `indicadores_financeiros` (`rendeu_no_ano_centavos`, `custo_manutencao_ano_centavos`, `VEI-05`) vai para todos menos o vistoriador. O valor de compra já é só de administrador e gerente.
- **Reprodução:** Bruna (vendedora) faz `GET /api/veiculos/{id}/` e recebe `indicadores_financeiros`.
- **Por quê:** o checklist pede que o vendedor não receba custo nem margem. A tabela de perfis e a `USR-09` não dizem nada sobre o vendedor nesse ponto, então é uma decisão do produto.
- **Sugestão (produto decide):** `indicadores_financeiros` só para administrador, gerente e financeiro. Para o vendedor, a chave vem ausente, como no D-25. Teste `test_usr_09_vendedor_sem_custo_do_veiculo`.

### M-03 · média · Produção aceita e-mail no console: links com token iriam para o log

- **Onde:** `backend/config/settings/base.py`. `EMAIL_BACKEND` tem por padrão `console.EmailBackend`, e `prod.py` não confere. O mesmo vale para `GIRO_ARMAZENAMENTO=falso` (arquivos na memória do processo).
- **Reprodução:** num deploy sem `EMAIL_BACKEND` no ambiente, os e-mails saem no stdout do container, e com eles links que tomam a conta:
  - "Esqueci a senha" (`contas/tasks.py:63`, token no fragmento);
  - convite (`contas/tasks.py`);
  - assinatura de contrato.

  Quem lê os logs (agregador, Sentry de logs, suporte) passa a ter esses tokens.
- **Sugestão:** `prod.py` recusa subir com `EMAIL_BACKEND` de console, locmem ou arquivo, e com `GIRO_ARMAZENAMENTO` diferente de `s3`, como já faz com as chaves. Pagamentos e WhatsApp `falso` entram na mesma trava quando as integrações reais existirem (T-029). Teste em `tests/` que importa `prod.py` com o ambiente montado.

### M-04 · média · Proxy reverso sem configuração versionada: tamanho do corpo e cabeçalhos `X-Forwarded-*`

- **Onde:** não há configuração do proxy em `infra/`. Três pontos do código dependem dela:
  - `base.py` liga `USE_X_FORWARDED_HOST = True`, e o `TenantMainMiddleware` escolhe a empresa por `request.get_host()`, ou seja, pelo `X-Forwarded-Host` quando ele vem;
  - `prod.py` confia em `X-Forwarded-Proto` (`SECURE_PROXY_SSL_HEADER`);
  - os uploads (`comum/arquivos.validar`, 10 MB) só são conferidos depois que o Django recebeu o arquivo inteiro. O Django não limita o tamanho de arquivo em multipart.
- **Reprodução:**
  - Um `POST` multipart de alguns GB em qualquer upload autenticado (documento do cliente, foto da vistoria) enche o disco temporário antes do 400.
  - Se o proxy repassar o `X-Forwarded-Host` do cliente, `Host: a.<dominio>` com `X-Forwarded-Host: b.<dominio>` cai na empresa B. O JWT e o cookie `__Host-` seguram o acesso, mas `build_absolute_uri` (link da exportação, `auditoria/api/views.py:159`) e os logs passam a mostrar o host forjado.
- **Sugestão (devops):** a configuração do proxy de homologação e produção vai para `infra/`, com:
  - limite de corpo (12 MB);
  - `X-Forwarded-Host`, `X-Forwarded-Proto` e `X-Forwarded-For` sempre sobrescritos pelo proxy;
  - rate limit de borda no `/api/auth/` e no webhook.

  No backend, `USE_X_FORWARDED_HOST` só em `prod.py`, junto do `GIRO_REDES_PROXY`. Checklist no `infra/README.md`.

### M-05 · baixa · O login revela e-mail com convite pendente sem conferir a senha

- **Onde:** `backend/apps/contas/api/acesso.py`, `EntrarView.post`. O 403 `convite_pendente` sai antes de `tentar_senha`.
- **Reprodução:** `POST /api/auth/entrar/` com o e-mail de uma pessoa com convite pendente e qualquer senha responde 403 `convite_pendente`. Um e-mail que não existe responde 401 `credenciais_invalidas`. Assim dá para saber quem foi convidado em cada empresa. O limite por IP reduz, mas não fecha.
- **Sugestão:** quem não tem senha utilizável recebe o mesmo 401 de credenciais, com o mesmo tempo de resposta. O 403 `convite_pendente` só sai depois da senha certa, que não existe antes do aceite. Teste `test_usr_06_convite_pendente_nao_revela_email`, e ajustar o teste que espera o 403 sem senha, se houver.

### M-06 · baixa · API navegável do DRF ligada em produção

- **Onde:** `base.py`, `DEFAULT_RENDERER_CLASSES` com `BrowsableAPIRenderer`. `prod.py` não tira.
- **Reprodução:** no navegador, `GET https://<empresa>/api/clientes/` mostra a página HTML do DRF com os formulários, os métodos aceitos e a descrição das views. É o que o S-17 fechou para o OpenAPI.
- **Sugestão:** em `prod.py`, só o `comum.renderizacao.JSONRenderer`.

## Conferido e sem achado

- **Autenticação:**
  - Argon2;
  - access de 5 min (mais curto que os 15 do checklist);
  - refresh rotativo com blacklist e detecção de reuso que revoga a sessão;
  - cookie `__Host-` `httpOnly`, `Secure`, `SameSite=Strict`, e renovar e sair exigem `X-Requested-With`;
  - JWT preso a `schema` e `empresa_id`;
  - `pre_2fa` de 5 min só nas rotas de 2 etapas.
- **2 etapas (`USR-02`, `PLT-08`):**
  - exigidas no token para quem `exige_2fa`;
  - TOTP sem reuso (`ultimo_passo`) e semente cifrada;
  - 8 códigos de recuperação em hash, de uso único.
- **Bloqueio e sessões:**
  - bloqueio de 15 min com a linha travada (`USR-06`);
  - sessões revogáveis, com expiração de 12 h ou 30 dias (`USR-04`);
  - trocar ou redefinir a senha encerra as sessões;
  - link de senha de 1 h, de uso único, guardado em hash, com o token no fragmento;
  - "Esqueci a senha" sempre em silêncio, com 3 pedidos por hora.
- **Permissões:**
  - `com_padrao` mantém `EmpresaOperando` e `EscopoDeFilial` (F-01 da T-064 fechado);
  - `filtrar_por_filial` e `_locacao` dão 404 fora do escopo;
  - `filial_da_requisicao` recusa quem não tem filial (F-02 da T-064 fechado).
- **Dados pessoais:**
  - CPF e CNH em `CampoCifrado`, com busca exata por HMAC com pepper;
  - lista com documento mascarado (`AUD-04`), e o suporte recebe a resumida (`AUD-09`);
  - cifrados e hashes omitidos na auditoria sem precisar declarar, nomes e contatos mascarados (decisão de 12 out cumprida).
- **Uploads:**
  - tipo pelo conteúdo e pela extensão, 10 MB;
  - foto reprocessada sem EXIF nem GPS;
  - caminho `<schema>/<app>/<model>/<id>/<uuid>`;
  - S3 privado com SSE e URL assinada de 15 min (`AUD-05`).
- **Auditoria:**
  - trigger contra UPDATE, DELETE e TRUNCATE;
  - IP real só atrás de proxy confiável (`comum.rede`);
  - consulta e exportação só do administrador, com o suporte 403 (`PLT-07`);
  - CSV com proteção contra fórmula;
  - link de 7 dias que expira e apaga o arquivo, e download por URL de 15 min com evento.
- **Suporte:** motivo obrigatório, 15, 30 ou 60 min, conferido no `public` a cada requisição, "só ver" por lista de views, encerramento automático a cada minuto (AUT-15) e evento na auditoria da empresa.
- **Webhook (S-14):**
  - empresa escolhida pelo hash do token, comparado em tempo constante;
  - `evento_id` único;
  - a baixa consulta a cobrança no parceiro e não confia no corpo, e valor diferente vira pendência;
  - 120 por minuto por IP.
- **Isolamento:**
  - tarefas com `schema_name` e `na_empresa`, que confere a empresa e o schema no `public`;
  - cache com o schema na chave;
  - host sem empresa responde 404 em produção (S-16).
- **Repositório público:**
  - nenhum `.env`, chave, dump ou credencial no histórico (`git log --all` por nome de arquivo e por padrões de chave);
  - as chaves de exemplo do `base.py` são recusadas por `prod.py`;
  - a senha do seed (`giro-dev-2026`) é pública de propósito, e o comando recusa `config.settings.prod`, que homologação também usa.
- **Frontend:**
  - o access fica fora de `localStorage`;
  - `X-Frame-Options` e CSP (`src/lib/csp.ts`);
  - o CSS da marca só aceita cor em hex.

## O que ficou de fora

- Testes rodando e prova no compose. A revisão foi feita lendo o código.
- O frontend da T-136.
- A integração real do Asaas (T-029): conferir lá o que o corpo bruto do webhook guarda de dados do pagador (`WebhookRecebido.corpo["bruto"]`).
- O logo (S-12, T-130).
- Os achados abertos de revisões anteriores, que continuam com as tarefas deles, como o F-04 e o F-05 da T-064.

## Próximo passo para quem recebe

- **Orquestrador:** numerar M-01 a M-06. A M-01 pode ir para o próprio PR #160 antes do merge. A M-03 e a M-04 precisam estar fechadas antes de homologação.
- **Backend:** M-01, M-03, M-05 e M-06; a M-02 depois da decisão.
- **DevOps:** M-04.
- **Produto:** decidir a M-02.

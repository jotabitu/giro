# T-291 · Django Admin pelo proxy · devops → orquestrador, arquiteto, segurança

Branch `t-291-admin-proxy`, **empilhada sobre a `origin/t-277-admin-pelo-proxy`** (ADR 0029, PR #290). Mesclar o #290 antes. A base já traz a imagem `producao`, o compose de homologação e o teste de subida (T-264).

**O que foi feito:**
- `infra/proxy/giro.conf.template`: o `geo $admin_permitido` (default 0, `include /etc/nginx/admin-ips.conf`) e dois blocos `server`: o dos hosts das empresas (`*.<domínio>`, como antes) e o do host da plataforma (`<SUBDOMINIO_PLATAFORMA>.<domínio>`, nome exato vence o curinga), este com `location /admin/` para o Django. Fora da lista, 404 (não 403). `location = /admin/login/` na zona `giro_auth` (10 por minuto por IP). `X-Robots-Tag: noindex, nofollow` nas duas.
- `infra/proxy/snippets/giro-locais.conf.template` (novo): o corpo comum dos dois servidores (TLS, limite de corpo, cabeçalhos X-Forwarded-*, `/api/...`, `/static/`, `/`), incluído por ambos para não divergirem. A imagem do nginx gera `conf.d/snippets/giro-locais.conf`, fora do `include conf.d/*.conf`.
- `infra/deploy/docker-compose.homologacao.yml`: monta o `snippets` e o arquivo da lista (`ADMIN_IPS_ARQUIVO`) e passa `SUBDOMINIO_PLATAFORMA` (padrão `admin`).
- `infra/deploy/homologacao.admin-ips.conf.example` e `producao.admin-ips.conf.example`: o arquivo do cofre, **vazio** (só comentários) = Admin fechado.
- `infra/scripts/teste-subida-producao.sh`: Next de mentira (responde `NEXT`) e as conferências do Admin. Passou: 27 no total.
- `infra/README.md`: "Como abrir o Admin" (5 passos) e o "Em aberto" da T-264 trocado por uma remissão a ele.

**Verificação (teste de subida, 27 conferências):** com a lista vazia (o modelo entregue), `/admin/` e `/admin/login/` dão 404 e o host da plataforma segue no Next em `/`; `/admin/contratos` de um host de empresa fica no Next; com o IP do teste na lista, `/admin/login/` dá 200 com a tela do Django (`csrfmiddlewaretoken`), `X-Robots-Tag: noindex` e o `login.css` com 200, e o host da empresa continua no Next; esvaziada a lista e recarregado o proxy, volta a 404. As 15 conferências anteriores (Gunicorn, senhas, `docker stop`) seguem passando. Tudo foi derrubado no fim (sem contêiner nem volume do teste sobrando).

**O que ficou de fora:**
- Não testei o limite do login (`giro_auth`, 429 depois da rajada) nem o login completo com 2 etapas: não há usuário `is_staff` no teste (seria o `createsuperuser`).
- O `geo` usa o IP da conexão; atrás de balanceador a lista precisa do ajuste do item de balanceador em "Proxy reverso".
- A sessão de 4 horas é da T-292 (backend); a VPN, de ADR nova.
- Não rodei a suíte do backend (nada de Python mudou).

**Próximo passo para quem recebe:** orquestrador abre o PR; no deploy real, preencher `ADMIN_IPS_ARQUIVO` no cofre com o arquivo vazio.

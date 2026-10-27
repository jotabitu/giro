# Revisão de segurança de fechamento da fase 1 · 25 out 2026

**Tarefa:** T-355 · **Autor:** seguranca · **Base:** `origin/main` em 626d432.
**Escopo:** as regras de segurança e LGPD (`USR-01` a `USR-07`, `PLT-07`, `PLT-08`, `AUD-01` a `AUD-09`), os achados `S-xx` da fundação e os relatórios de `docs/seguranca/` (T-032 a T-199). Para cada achado, conferi o código atual, não só o quadro. Nenhum código mudou.

**Como conferi:** leitura do código em `backend/`, `frontend/src/lib/csp.ts` e `infra/deploy/`. Rodei num contêiner descartável (banco `giro_seg`): `test_t189_seguranca_cartao.py`, `test_t317_varredura_suporte.py` e `test_permissoes_das_rotas.py`, **164 passed**, nenhum `xfail`. Rodei também `pip-audit -r requirements.txt`.

## Resumo

Nada do que as revisões anteriores apontaram como alto continua aberto. O único alto novo é de dependência: o Pillow que decodifica todo upload de imagem tem 37 avisos corrigidos só na 13.0, e o `requirements.txt` não deixa passar de 12.x.

Antes de produção ficam, além dele, três médios: a tarefa do apagamento (`AUD-08`) sem credencial no worker, o ambiente de produção ainda sem desenho (backup, rede, cofre) e o atendimento à mão do titular (`AUD-06`) sem ferramenta. Os baixos podem entrar depois do piloto.

**Os dois `xfail` citados no pedido já estão fechados.** O `test_t189_seguranca_cartao.py` não tem mais `xfail`: o M-01 caiu na T-268 e o M-02 na T-269. Em `test_t317_varredura_suporte.py`, `QUEBRADAS` está vazio desde a T-324. Os dois passam na `main`. Restam dois `xfail` fora da segurança: `test_t195_cancelar_pausar.py:736` (reativação, ver B-04) e `test_t184_faturas.py:412` (nota fiscal, T-197).

| # | Gravidade | Item | Antes de produção? | Agente |
| --- | --- | --- | --- | --- |
| A-01 | alta | Pillow 12.3 com 37 avisos, corrigidos na 13.0; o limite `<13` impede a correção | sim | backend |
| M-01 | média | Apagamento `AUD-08` sem `DATABASE_URL_MIGRACAO` no worker: o `DROP SCHEMA` falha | sim (antes do 90º dia do 1º cancelamento real) | devops |
| M-02 | média | Produção sem desenho: backup cifrado, retenção dos backups × `AUD-08`, Django só pelo proxy, cofre | sim | arquiteto, devops |
| M-03 | média | Pedido do titular (`AUD-06`) "à mão pela equipe Giro" sem ferramenta: hoje seria SQL direto no banco | sim, antes do 1º cliente real | backend |
| M-04 | média | Sem auditoria de dependências recorrente (o `weasyprint` e o Pillow foram achados à mão) | sim | devops |
| B-01 | baixa | T-159: o login revela o e-mail com convite pendente | não | backend |
| B-02 | baixa | T-160: API navegável do DRF ligada em produção | não (fazer junto do A-01) | backend |
| B-03 | baixa | B-02 da T-189: recusa do parceiro deixa o aviso do webhook sem resultado | não | backend |
| B-04 | baixa | B-02 da T-199: a reativação terá de recusar a empresa com o apagamento começado | quando a reativação entrar | backend |
| B-05 | baixa | B-05 da T-247: `cnh_digital` na exportação e na anonimização do titular | fase 2, junto da `AUD-06` | backend |

## O que está atendido

| Regra ou achado | Situação | Evidência |
| --- | --- | --- |
| `USR-02`, `PLT-08`: 2 etapas obrigatórias; bloqueio de 5 senhas e de 3 códigos (plataforma) | ok | `dois_fatores.tentar_entrar` com trava na linha do usuário (P-01 a P-03 fechados na T-058); Admin só no `public` com `OTPAdminSite` |
| `USR-04`: sessões revogáveis; desativar encerra na hora | ok | `sessoes.revogar`, `revogar_todas` (`contas/api/acesso.py:643-651`, `usuarios.py:365`); reuso do refresh revoga a sessão (P-07, T-011) |
| `USR-06`: bloqueio de 15 min, 12 h desktop e 30 dias celular | ok | `contas/models.py:237-238`; access de 5 min, refresh com rotação e blacklist (`base.py:303-307`) |
| Ações sensíveis com 2 etapas recentes (`PLT-06`, `S-15`) | ok | `POST cancelamento/` e o ZIP pedem `2fa_recente`; reconfirmação da ADR 0032 (T-347, T-348); janela de 5 min mantida (T-349, T-351) |
| Token preso à empresa (S-01), cookie `__Host-` sem CORS (S-08), host desconhecido 404 (S-16) | ok | `conferir_empresa`; `test_sem_cors`; `test_host_sem_empresa_responde_404` |
| `PLT-07`, `AUD-03`, `AUD-09`: suporte com motivo e prazo, e-mail ao administrador, bloqueio, dados mascarados, escrita barrada no dinheiro e nas movimentações | ok | `abrir_acesso_suporte` com `on_commit` do aviso (`plataforma/services.py:607`), `revogar_acesso_suporte`; varredura das 143 rotas de escrita sem 500 (T-317/T-324); suporte recusado na `cancelada` (T-345) |
| `AUD-01`: auditoria imutável, com IP real e diff cru | ok | trigger e papéis separados (S-10, C-05, T-034, T-276); IP por `GIRO_REDES_PROXY` (C-03); diff antes da máscara (C-01) |
| `AUD-04`, `AUD-05`, S-07: CPF e CNH cifrados, máscara nas listas, fotos privadas com URL de 15 min, sem metadados | ok | AES-GCM com dado associado e HMAC por empresa (T-033); `sem_metadados` nas fotos e `nota_limpa` nas notas (B-03 da T-315) |
| `AUD-08`: o que fica da empresa apagada (opção B da T-230), schema apagado não cai no `public` | ok no código | T-195, T-345 (M-02 da T-199); a credencial do worker é o M-01 abaixo |
| Uploads: tipo pelo conteúdo, tamanho, nome aleatório, SVG do logo sanitizado (S-12), PDF do CRLV em processo filho | ok | `comum/arquivos.py`, `empresas/logo.py` (`defusedxml`), ADR 0026 com as correções da T-329 |
| Pagamentos: webhook com token, idempotência, aviso sem o cartão, subconta sem a chave principal | ok | S-14 (T-029), M-01 e M-02 da T-189 (T-268, T-269) |
| Configuração de produção: `DEBUG` falso, chaves próprias e de 32 bytes, JWT com chave própria, Redis com senha, Swagger fechado, HSTS, `nosniff`, `X-Frame-Options` | ok | `config/settings/prod.py` (C-04, C-07, R-03, S-17); `EXPOR_DOCUMENTACAO_DA_API` falso em `prod.py:57` |
| CSP | ok | `frontend/src/lib/csp.ts`: `script-src` com nonce e `strict-dynamic`, sem `unsafe-inline` em script, `frame-ancestors 'none'`, `connect-src 'self'` |
| Rate limiting | ok | throttles em `entrar`, convite, renovar, 2 etapas, CEP e leitura de documento (`comum/limites.py`); no proxy, `limit_req` para auth, webhook e leitura (`infra/proxy/giro.conf.template:12-17`) e Admin por lista de IPs |
| Sentry sem dado pessoal | ok | `comum/sentry.py`: sem variáveis locais, sem corpo, `before_send` (T-270) |
| Régua da assinatura: um e-mail por destinatário, sem parar no primeiro erro | ok | M-01 e M-02 da T-304 (T-303/T-306) |
| `weasyprint` com aviso (T-328) | ok | `requirements.txt:20`, `>=70,<71` |

## Achados e tarefas sugeridas (sem número)

### A-01 · alta · Pillow com 37 avisos de segurança, presos por `<13`

**Onde:** `backend/requirements.txt:17` (`Pillow>=11.1,<13`). O `pip-audit` resolve 12.3.0 e lista 37 avisos (CVE e GHSA), todos com correção na 13.0.0.
**Por que é alto:** o Pillow decodifica toda imagem que entra: foto da vistoria, documento do cliente (CNH), foto da chegada da movimentação, nota em imagem e logo PNG. Qualquer usuário autenticado de qualquer empresa envia imagem. Falha de decodificação é a superfície clássica de negação de serviço e de corrupção de memória, e roda no mesmo processo do Django, com as chaves no ambiente. Não testei cada CVE. A gravidade vem da superfície e da quantidade.
**Tarefa sugerida:** **backend** · *Pillow 13 e auditoria limpa*. **Pronto quando:** `Pillow>=13,<14` em `requirements.txt`, imagem reconstruída; `pip-audit -r requirements.txt` sem aviso; passam os testes de upload (`sem_metadados`, fotos de vistoria, logo, documentos do cliente, T-165 se estiver aberta) e a recusa por `DecompressionBombError` (`comum/arquivos.py:100`) e o lado máximo do logo (`empresas/logo.py:25`) continuam valendo; motivo da troca de versão maior registrado no PR.

### M-01 · média · O apagamento `AUD-08` não roda na homologação como está

**Onde:** `infra/deploy/docker-compose.homologacao.yml:33-65`: só o serviço `migrar` recebe `DATABASE_URL_MIGRACAO`. O `worker`, que roda `aud_08_apagar_empresas`, não recebe. Sem ela, `apagar_empresas` registra o erro (`plataforma/services.py:3630`, B-01 da T-199) e o `DROP SCHEMA` vai pela conexão do `giro_app`, que não é dono do schema: falha.
**Por que importa:** a `AUD-08` diz que a tarefa que apaga "tem de existir antes do 90º dia do primeiro cancelamento real". Hoje ela existe no código e não funciona no ambiente. Os dados da empresa cancelada ficariam guardados além do prazo prometido.
**Tarefa sugerida:** **devops** · *Credencial de migração só para o apagamento*. **Pronto quando:** um worker próprio (fila só da `aud_08_apagar_empresas`) recebe `DATABASE_URL_MIGRACAO`; `backend`, `worker` comum e `beat` não a recebem; o `teste-subida-producao.sh` confere as duas coisas e roda uma vez o apagamento de uma empresa de teste; o mesmo vale no desenho de produção (M-02).

### M-02 · média · Produção sem desenho de backup, rede e cofre

**Onde:** `infra/README.md:10` e `:57`: a hospedagem de produção está "a definir em ADR", e o backup tem tarefa própria ainda não feita. Só existe `producao.env.example`.
**O que precisa estar decidido antes do primeiro cliente real:**
- backup do banco e do armazenamento, cifrado, fora da conta principal, com restauração testada;
- **retenção dos backups compatível com a `AUD-08`**: o dado apagado no 90º dia continua nos backups. O prazo máximo de retenção tem de constar da ADR (e, se o produto quiser, do texto do cancelamento);
- Django alcançável só pelo proxy (`infra/README.md:98`, "a fechar no deploy");
- segredos no cofre do ambiente, com `giro_migracao` só no job de deploy e no worker do M-01;
- a lista de IPs do Admin (`producao.admin-ips.conf.example`) preenchida.

**Tarefa sugerida:** **arquiteto** · *ADR do ambiente de produção*, depois **devops** · *Subida de produção*. **Pronto quando:** a ADR fixa provedor, backup (frequência, cifra, retenção máxima e teste de restauração), rede e cofre; o devops sobe com o `teste-subida-producao.sh` adaptado e uma restauração de backup feita e registrada.

### M-03 · média · Pedido do titular (`AUD-06`) sem ferramenta para a equipe

**Onde:** `docs/regras-de-negocio.md:758`: até a fase 2, "o administrador da locadora pede à equipe Giro, que gera os dados ou anonimiza o cadastro". No código não há serviço nem comando para isso. Existe só o primitivo `comum.cripto.anonimizar_cifrado`, sem `anonimizar_cliente` nem `exportar_cliente`, e os comandos de `manage.py` são só seed, convite e catálogo.
**Por que importa:** o primeiro pedido real viraria SQL à mão no banco de produção. Isso fura a auditoria (`AUD-01`), não sabe decifrar nem trocar o hash de busca e pode deixar CPF em claro nos campos derivados. O prazo de resposta da LGPD (art. 19) é curto.
**Tarefa sugerida:** **backend** · *Comandos do titular para a equipe Giro*. **Pronto quando:**
- `manage.py exportar_titular <schema> <cliente_id>` gera um arquivo com os dados do cliente, decifrados, e grava o evento `cliente.exportar` na auditoria da empresa e na da plataforma, com quem pediu e o motivo;
- `manage.py anonimizar_titular <schema> <cliente_id>` usa `anonimizar_cifrado`, mantém contratos e registros financeiros e grava o evento;
- os dois recusam a empresa apagada e rodam só com a conexão do `giro_app`;
- teste com o código: `test_aud_06_*`.

Se o arquiteto preferir, a rota da fase 2 pode nascer já agora, só para o administrador.

### M-04 · média · Auditoria de dependências só à mão

**Onde:** o `weasyprint` (T-328) e o Pillow (A-01) foram achados por mim, rodando `pip-audit` numa revisão. O CI está sem minutos (`ci-actions-limite`) e não há outro passo que audite.
**Tarefa sugerida:** **devops** · *Auditoria de dependências antes do deploy*. **Pronto quando:** `make auditoria-deps` roda `pip-audit -r backend/requirements.txt` e `npm audit --omit=dev --audit-level=high` em `frontend/`; o script de deploy de homologação e de produção o roda e para se houver aviso alto sem exceção registrada; o README explica como registrar a exceção.

### B-01 · baixa · T-159: o login revela o e-mail com convite pendente

**Confirmado aberto:** `contas/api/acesso.py:374-378`. Para quem tem convite pendente sem senha, o 403 `convite_pendente` sai antes de conferir a senha e sem o Argon2. A resposta e o tempo diferem do e-mail que não existe (`:370-373`).
**Atenuante:** throttle por IP e por e-mail no `entrar`. **Tarefa:** a T-159 do backlog, como está.

### B-02 · baixa · T-160: API navegável do DRF em produção

**Confirmado aberto:** `config/settings/base.py:185-188` tem o `BrowsableAPIRenderer`, e `prod.py` não o tira. Um navegador logado vê formulários e descrições das views, o que o S-17 fechou para o OpenAPI.
**Tarefa:** a T-160 do backlog, como está. É uma linha; cabe no mesmo PR do A-01.

### B-03 · baixa · B-02 da T-189: recusa do parceiro no webhook

**Confirmado aberto:** em `processar_webhook_fatura` (`plataforma/services.py:1041-1074`), `consultar_cobranca` só trata `StatusDesconhecido`. A tarefa reenvia só `ParceiroIndisponivel` (`tasks.py:250`). Um `ParceiroRecusou` (chave errada, 4xx) sobe sem `processado_em` nem `resultado`. Não vaza nada, e a fatura não é baixada (o lado seguro), mas a equipe só vê no log.
**Tarefa sugerida:** **backend** · *Aviso do parceiro recusado vira resultado*. **Pronto quando:** `ParceiroRecusou` grava `resultado = "parceiro_recusou"` e `processado_em`, loga como os outros resultados, e há teste com o parceiro de mentira.

### B-04 · baixa · B-02 da T-199: reativação com o apagamento começado

Hoje nada reativa uma `cancelada`, e o `xfail` estrito de `test_t195_cancelar_pausar.py:736` espera a reativação. **Pronto quando** (na tarefa da reativação, CA-ASS-46): a reativação recusa a empresa com o apagamento começado, por exemplo com `apagamento_iniciado_em` gravado com a `Empresa` travada antes de apagar os arquivos, e há teste disso.

### B-05 · baixa · B-05 da T-247: `cnh_digital` no pedido do titular

Fase 2, junto da `AUD-06`. Se o M-03 sair antes, os comandos já incluem o `cnh_digital` na exportação e na anonimização.

## Riscos aceitos, sem tarefa

- Janela das 2 etapas recentes de 5 minutos (T-349).
- Um invasor com a sessão pode gastar as tentativas e bloquear o login da pessoa por 15 minutos (ADR 0032, Consequências).
- Link copiado do convite (T-252, "Risco aceito").
- Limite de 12 MB na borda do `POST /api/veiculos/` (resíduo da T-329).

## Ordem sugerida antes de produção

1. A-01 com o B-02 (backend, um PR).
2. M-03 (backend).
3. M-04, depois M-01 (devops), já dentro do desenho do M-02.
4. M-02: a ADR do arquiteto e a subida do devops.
5. Os baixos (B-01, B-03) podem entrar depois do piloto. O B-04 entra com a reativação, e o B-05 com a fase 2.

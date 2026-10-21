# T-199 · Cancelamento, pausa e apagamento (código da T-195)

**Data:** 20 out 2026 · **Agente:** segurança · **Regras:** PLT-06, PLT-07, AUD-08, USR-02 · **ADR:** 0016, 0023, 0025
**Base:** PR #375, branch `t-195-cancelar-pausar` (commit `cebac0d`), handoff `tarefas/handoffs/T-195-backend.md`, contrato `docs/api/cancelamento.md`.
**Método:** leitura de `apps/plataforma/banco.py`, `services.py` (cancelar, desfazer, pausar, voltar, encerrar a forma, virada, aviso e apagamento), `tasks.py`, `api/assinatura.py`, `models.py`, `comum/middleware.py`, `comum/permissoes.py`, `comum/arquivos.py`, `integracoes/pagamentos/asaas.py` e `config/settings/base.py`. Testes num contêiner descartável (banco `giro_seg`): `test_t195_cancelar_pausar.py` e `apps/plataforma/tests/test_calendario.py`, 57 passam. Duas sondas fora do repositório (empresa apagada e suporte), com o resultado abaixo. Nenhum código mudou.

## Resumo

O apagamento está bem desenhado. O `DROP SCHEMA` só aceita um `empresa_id` e confere de novo a `Empresa` travada. O nome passa por `Identifier`, e os schemas do Postgres e o `public` são recusados. O middleware fecha a `cancelada` em tudo, e os arquivos saem com as versões. **Não há achado alto.**

Três achados médios pedem código antes da produção. Não precisam segurar o merge do #375: nenhum deles abre caminho entre empresas, e o apagamento só roda 90 dias depois de uma empresa virar `cancelada`. **O #375 pode entrar**, com a tarefa abaixo numerada para antes da primeira empresa chegar ao 90º dia.

| Código | Achado | Severidade | Quem |
| --- | --- | --- | --- |
| M-01 | Cancelar não pede 2 etapas recentes, e na `inadimplente`, `suspensa` e `pausada` o cancelamento é na hora e sem volta pela tela | média | backend |
| M-02 | O schema apagado cai no `public`: o suporte ainda abre acesso na empresa cancelada e na apagada, e o evento "da empresa" vai para a auditoria da plataforma | média | backend |
| M-03 | Uma recusa do parceiro trava o apagamento do `public` e o fim da forma de pagamento para sempre | média | backend |
| B-01 | Produção sobe sem `DATABASE_URL_MIGRACAO`, e o worker da homologação não a recebe | baixa | backend, devops |
| B-02 | Os arquivos saem antes da conferência com a empresa travada | baixa | backend |
| B-03 | O 403 `empresa_cancelada` sai antes do `SecurityMiddleware` | baixa | backend |

## O que está conforme

**(1) `banco.apagar_schema`** (`apps/plataforma/banco.py:64`).
- Só `services.apagar_empresa` chama, e ele só é chamado pela `aud_08_apagar_empresas`. Recebe o `empresa_id`, nunca um nome de schema de fora.
- Lê o `schema_name` da `Empresa` travada (`select_for_update`) no `public` e confere de novo (`conferir_para_apagar`, `banco.py:46`): `cancelada`, `apagar_em` até hoje, `apagada_em` nulo e nome no padrão `^[a-z0-9_]{3,30}$`. Recusa `public`, `pg_*` e `information_schema`.
- O comando é `sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(...))`, sem concatenação.
- Com `DATABASE_URL_MIGRACAO`, abre uma conexão própria em autocommit, com o papel dono dos schemas, enquanto segura a trava da `Empresa`. Sem ela, usa a conexão da aplicação: em produção (`giro_app`, sem DDL) o `DROP` falha, e a empresa fica para o dia seguinte (B-01).
- O teste `test_aud_08_nao_apaga_outra_empresa` cobre a outra empresa, os arquivos dela e os nomes recusados. O `test_aud_08_nao_apaga_reativada` cobre a empresa que deixou de ser `cancelada`.

**(2) `aud_08_apagar_empresas` e `aud_08_avisar_apagamento`.**
- Uma empresa por vez. A que falha fica para o dia seguinte e vai para o log de erro. Cada passo pode rodar de novo, e `apagada_em` só é gravado no fim.
- Saem os arquivos do prefixo `<schema>/` (`apagar_prefixo`, com as versões e os marcadores de exclusão no S3; o prefixo recusa `public`, `.` e `/`), o schema (negócio, usuários e a auditoria da empresa) e, no `public`, o domínio, o uso, a conta de pagamento e a forma. A linha da `Empresa` fica só com o CNPJ, o plano, as datas, a cidade e a UF. O pagador no parceiro perde e-mail e telefone.
- Ficam as faturas, com o tomador gravado, e o e-mail de cobrança só na `atrasada` (opção B da T-230). Fica também o evento `empresa.apagar` no `public`, com o schema, a quantidade de arquivos e a data, sem dado pessoal.
- Com o domínio apagado, o host da empresa responde 404 e não cai no `public` (`SHOW_PUBLIC_IF_NO_TENANT_FOUND` desligado).
- O aviso de 7 dias sai uma vez só, aos administradores ativos, e o log da falha leva só o id e o tipo do erro.

**(3) `EmpresaCanceladaMiddleware`** (`comum/middleware.py:26`, `config/settings/base.py:112`). Fica logo depois do `TenantMainMiddleware` e responde 403 `empresa_cancelada` a todo pedido da `cancelada`, antes da autenticação. Por isso o `entrar`, o `renovar` e um access token ainda válido param na hora (`test_aud_08_cancelada_nao_entra`). Um token de uma empresa não serve no host de outra (`JWTDaEmpresa` confere o schema).

**(4) Quem pode.** As 5 rotas são só do administrador (`SoAdministrador`), e o suporte nunca escreve, nem com "ver e editar". As exceções do somente leitura estão numa lista explícita com teste: na `suspensa`, só `POST cancelamento/`; na `pausada`, `POST cancelamento/` e `DELETE pausa/`. O nome digitado é obrigatório no serializer e conferido no serviço. Falta o M-01.

**(5) Fim da forma de pagamento.** Quando a empresa vira `cancelada`, `encerrar_forma_pagamento` roda depois do commit: cancela a autorização do Pix no parceiro, esquece o token do cartão (cifrado), a bandeira e o final, deixa a forma vazia e audita. Com o parceiro fora do ar, tenta de novo por até 24 h. Falta o caso da recusa (M-03).

**(6) `Empresa.save()`** (`apps/plataforma/models.py:211`). Na `cancelada`, desliga o `auto_create_schema`. A sonda conferiu: o `save()` depois do `DROP` não traz o schema de volta.

## Achados

### M-01 · Cancelar sem 2 etapas recentes · média

**Onde:** `apps/plataforma/api/assinatura.py:555` (`CancelamentoView.post`); `apps/plataforma/services.py:3017`.
**Problema:** o cancelamento só pede o nome da empresa, que está na própria tela. Quem tiver uma sessão do administrador (aparelho destravado, token roubado) cancela. Na `em_teste` e na `ativa` há como desfazer até o último dia de acesso. Na `inadimplente`, na `suspensa` e na `pausada` não: a empresa vira `cancelada` na hora, o middleware fecha tudo para todos, inclusive para o administrador desfazer, a forma de pagamento sai do parceiro e o apagamento fica marcado para 90 dias. A volta depende da equipe, e a reativação ainda não existe no código. O Giro já tem a confirmação recente: o 403 `2fa_recente` da exportação completa (`apps/auditoria/services.py`, `otp` no `amr` e `auth_time` de até 15 min). O administrador sempre tem 2 etapas (`USR-02`), então pedir de novo não bloqueia ninguém.
**Decisão da T-199 (o contrato deixou para a segurança):** sim, `POST /api/assinatura/cancelamento/` pede 2 etapas recentes, com o 403 `2fa_recente` antes de qualquer outra conferência, como em `auditoria.md`. `DELETE cancelamento/`, pausar e voltar não pedem: são reversíveis e não tiram ninguém do sistema. Trocar a forma de pagamento (item 8 da T-190) está fora deste PR. Fica a sugestão de usar a mesma regra lá.
**Sugestão:** usar a mesma checagem da auditoria (de preferência movida para `comum`), um teste `test_plt_06_cancelar_pede_2_etapas_recentes` e a linha nova na tabela de erros de `cancelamento.md`. A tela (T-198) pede o código e repete o envio.

### M-02 · O schema apagado cai no `public` · média

**Onde:** `apps/plataforma/services.py:536` (`abrir_acesso_suporte`), `:524` (`_auditar_na_empresa`), `:2247` (`destinatarios_da_cobranca`), `:425` (`recalcular_uso`); `config/settings/base.py:45` (`APPS_DOS_DOIS_SCHEMAS`).
**Problema:** `contas`, `auditoria`, `auth`, `sessions`, `django_otp` e a blacklist dos tokens existem nos dois schemas. O `schema_context` do django-tenants põe `search_path = <schema>, public`, e o Postgres ignora o schema que não existe. Depois do `DROP`, todo código que entra no schema da empresa apagada lê e grava as tabelas da plataforma, sem erro. Sonda: com a Moto Rápida apagada, `schema_context("motorapida")` mostra `search_path` "motorapida, public", e `EventoAuditoria.objects.count()` dá o mesmo número do `public` (7 e 7).
- **Suporte:** `abrir_acesso_suporte` não confere o estado da empresa. Na `cancelada`, ele abre o acesso, emite o token (que o middleware recusa) e manda o e-mail de "suporte entrou" aos administradores de uma empresa que não usa mais o sistema. Na apagada, ele abre, e o evento `suporte.entrar` "da empresa" vai para a auditoria da plataforma: na sonda, 2 eventos no `public` em vez de 1.
- **Outros caminhos:** `destinatarios_da_cobranca`, `recalcular_uso` e `_administradores_ativos` fazem o mesmo `schema_context` sem conferir. Hoje eles não chegam à apagada: a régua para na `cancelada`, a tarefa de uso usa `tarefa_de_empresa` (que confere o `pg_namespace`) e o aviso exige `apagada_em` nulo. Mas a proteção é de cada chamador, e o próximo pode não ter.
- Isso não vaza dado de outra empresa. Mistura evento de empresa na auditoria da plataforma, e uma leitura de "administradores da empresa" passaria a ler os usuários da equipe Giro, se um dia algum deles tiver `perfil`.

**Sugestão:**
- `abrir_acesso_suporte` recusa a `cancelada` com 409, com mensagem como "Esta empresa cancelou a assinatura. O suporte não entra." (o pedido de dados é atendido pela equipe, `AUD-08`). Teste `test_plt_07_suporte_nao_entra_na_cancelada`.
- Uma entrada única no schema da empresa para o `public`, como `plataforma.services.na_empresa(empresa)`, que recusa a apagada (ou confere o `pg_namespace`, como `comum.tarefas.conferir_empresa_para_tarefa`), usada nos `schema_context(empresa.schema_name)` de `services.py` (linhas 300, 427, 530, 2035, 2251, 3412 e os de 695, 1470 e 2011). Teste com a empresa apagada: nada é gravado nem lido no `public` pelo caminho da empresa.

### M-03 · Recusa do parceiro trava o apagamento e o fim da forma · média

**Onde:** `apps/plataforma/services.py:3495` (`_limpar_publico`, passo 2) e `:3315` (`encerrar_forma_pagamento`); `_no_parceiro` (`:1785`) troca `ParceiroRecusou` por `ErroDeRegra`.
**Problema:**
- **Apagamento.** O passo (c) chama `anonimizar_pagador` antes de apagar a forma, o domínio e os dados da `Empresa`. Se o parceiro recusar (o handoff diz que a T-184 ainda vai conferir no sandbox se o Asaas aceita os campos vazios), a transação de (c) e (d) volta. O schema e os arquivos já foram apagados. Todo dia a tarefa tenta de novo e falha do mesmo jeito. No `public` ficam, sem prazo, o nome, o responsável, o e-mail de cobrança, o domínio e a forma com o token do cartão cifrado. É justamente o que o `AUD-08` manda apagar.
- **Fim da forma.** A tarefa só tenta de novo com o parceiro fora do ar. Se o parceiro recusar o cancelamento da autorização do Pix (autorização já cancelada pelo pagador ou inexistente, por exemplo), a tarefa falha uma vez e para. O token do cartão, que só seria esquecido depois, fica até o 90º dia. Se o apagamento também travar, fica para sempre.

**Sugestão:**
- No apagamento, a recusa do parceiro na anonimização é registrada (log de erro, evento `empresa.apagar` com `pagador_anonimizado: false`) e não impede os passos 3 e 4.
- No fim da forma, esquecer o token do cartão antes de chamar o parceiro, ou mesmo quando ele recusa. "Autorização inexistente ou já cancelada" conta como encerrada. Outra recusa vai para o log de erro.
- Testes com o falso de pagamentos recusando: o apagamento termina sem o pagador anonimizado, e a forma fica sem token.

### B-01 · `DATABASE_URL_MIGRACAO` fora de produção e da homologação · baixa

**Onde:** `config/settings/prod.py` (só confere a `DATABASE_URL`); `infra/deploy/docker-compose.homologacao.yml` (a variável vai só para o serviço `migrar`).
**Problema:** sem a variável, o `DROP` tenta pela conexão da aplicação e falha todo dia, o que só aparece no Sentry. Isso é o que o handoff prevê para o devops. Mas ninguém recusa subir sem ela, e na homologação o worker não a recebe hoje.
**Sugestão:** o devops passa a `DATABASE_URL_MIGRACAO` **só ao worker** que roda a `aud_08_apagar_empresas`, nunca ao backend web (é uma credencial com DDL em todos os schemas). Se for preciso separar, uma fila só para essa tarefa. O backend registra no log de erro, ao rodar a tarefa, quando a variável falta (melhor que recusar subir o web, que não precisa dela).

### B-02 · Arquivos saem antes da conferência com a trava · baixa

**Onde:** `apps/plataforma/services.py:3507-3520` (`apagar_empresa`).
**Problema:** o passo (a) apaga os arquivos depois de uma conferência sem trava, e só o passo (b) trava a `Empresa` e confere de novo. Hoje nada reativa uma `cancelada` (a `reativar_empresa` não existe). Quando existir, uma reativação no meio do apagamento perde os arquivos e mantém o schema.
**Sugestão:** quando a reativação entrar, ela trava a `Empresa` e recusa a que já começou a ser apagada (por exemplo, com um `apagamento_iniciado_em` gravado com a trava antes do passo (a)). Ou o passo (a) passa a rodar com a trava. Anotar na tarefa da reativação.

### B-03 · O 403 `empresa_cancelada` sem os cabeçalhos de segurança · baixa

**Onde:** `config/settings/base.py:112`.
**Problema:** o `EmpresaCanceladaMiddleware` responde antes do `SecurityMiddleware` e do `XFrameOptionsMiddleware`, então o 403 sai sem `X-Content-Type-Options` e sem `X-Frame-Options` (o HSTS vem do nginx). É uma resposta JSON fixa, sem dado, então o risco é quase nenhum.
**Sugestão:** pôr o `SecurityMiddleware` antes dele (o `TenantMainMiddleware` continua primeiro), ou criar a resposta com `nosniff`.

## Tarefa de backend para numerar

```
### T-??? · Cancelamento: 2 etapas recentes, empresa apagada e recusa do parceiro
- **Agente:** backend · **Depende de:** T-195 (PR #375) · **Regras:** PLT-06, PLT-07, AUD-08, USR-02 · **Severidade:** média · **Origem:** T-199 (segurança), M-01 a M-03 e B-01 a B-03 de `docs/seguranca/2026-10-20-t199-cancelamento.md`
- **Pronto quando** (antes de uma empresa chegar ao 90º dia em produção):
  - `POST /api/assinatura/cancelamento/` responde 403 `2fa_recente` sem 2 etapas nos últimos 15 min, antes das outras conferências; linha em `cancelamento.md`; `test_plt_06_cancelar_pede_2_etapas_recentes` (M-01);
  - `abrir_acesso_suporte` recusa a `cancelada` com 409; os `schema_context(empresa.schema_name)` de `plataforma/services.py` passam por uma entrada que recusa a empresa apagada; testes com a empresa apagada (M-02);
  - a recusa do parceiro na anonimização não impede o resto do apagamento (registrada no evento e no log); `encerrar_forma_pagamento` esquece o cartão mesmo com recusa, e "autorização inexistente" conta como encerrada; testes com o falso recusando (M-03);
  - log de erro claro quando a `aud_08_apagar_empresas` roda sem `DATABASE_URL_MIGRACAO` (B-01);
  - `SecurityMiddleware` antes do `EmpresaCanceladaMiddleware` (B-03).
- **Para o devops:** `DATABASE_URL_MIGRACAO` só no worker da `aud_08_apagar_empresas` (B-01).
- **Para a reativação (quando entrar):** recusar a empresa com o apagamento começado (B-02).
```

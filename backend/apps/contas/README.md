# app `contas`

**Schema:** empresa
**Escopo:** Usuários da empresa, perfis, permissões extras, filiais do usuário, convites, sessões, 2FA, login.
**Regras:** USR (ver `docs/regras-de-negocio.md`)
**Telas:** Login, Acesso-Senha, Convite, Admin-Usuarios (ver `docs/telas/README.md`)

## Estrutura esperada

```
contas/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/contas.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-010)

- `Usuario.status` (`convite_pendente`, `ativo`, `desativado`) no lugar de `ativo`, pela máquina de estados (`transicao_usuario`); `tentativas_erradas` (códigos), `senhas_erradas`, `bloqueado_ate`, `celular`; `exige_2fa` (sempre na plataforma; perfis da empresa na T-011).
- `Convite` (hash do token, 7 dias). A tarefa `contas_enviar_convite` recebe só ids e gera o token na hora do envio.
- `dois_fatores.py`: autenticador TOTP, 8 códigos de recuperação, bloqueio de 15 min no 3º código ou na 5ª senha errada (PLT-08). `tentar_entrar` e `verificar_codigo` travam a linha do usuário antes de conferir bloqueio, senha e código (T-058).
- `login_admin.py`: formulário de login do Django Admin, pelo mesmo `tentar_entrar` e com a mesma auditoria da API (T-058).
- `api/plataforma.py`: login da equipe (`entrar`, `2fa/configurar`, `2fa/verificar`, `renovar`, `sair`, `eu`) e convite (`convites/{token}/`, `aceitar/`).
- Comando `convidar_equipe_plataforma <email> <funcao> --nome`.

## Implementado (T-011, parte 1: login, sessões e 2 etapas da empresa)

- `api/acesso.py` (host da empresa, `/api/auth/`): `entrar`, `2fa/verificar|configurar|ativar|desativar|codigos-recuperacao`, `renovar`, `sair`, `eu` (GET e PATCH), `sessoes` (listar, encerrar uma, encerrar as outras), `senha/trocar|esqueci|redefinir`. Sem `EmpresaOperando` de propósito (`VIEWS_DE_ACESSO`): com a empresa suspensa as pessoas ainda entram para ler.
- `sessoes.py` (ADR 0014): `Sessao` com `sid` nos tokens, 12 h no desktop e 30 dias no celular sem uso (`USR-06`), conferida a cada requisição com cache de 30 s, `revogar` e `revogar_todas` com evento `sessao.encerrar`. Cada sessão guarda o `jti` do refresh vigente; outro refresh da mesma sessão revoga a sessão inteira (P-07 da T-057). Registrada em `comum.autenticacao` por `registrar_sessoes`.
- 2 etapas: `Autenticador` (TOTP, semente cifrada com `GIRO_CHAVE_SEGREDOS`) e `CodigoRecuperacao` (só o HMAC por empresa) no lugar do `otp_totp` e do `otp_static` (P-08). `exige_2fa` = plataforma, perfil administrador ou financeiro, `ConfiguracaoEmpresa.exige_2fa_todos` ou autenticador ativo (`USR-02`); `exige_2fa_pela_regra` é o `obrigatorio` do `eu`. O primeiro autenticador só se cadastra com a senha dentro do prazo do convite aceito (P-05).
- Bloqueio: na empresa, 5 tentativas erradas somando senha e código (`USR-06`), com aviso por e-mail aos administradores (`contas_avisar_bloqueio`); na plataforma, 5 senhas ou 3 códigos (`PLT-08`).
- `selectors.py`: `pode` (tabela do contrato mais as permissões extras, que só somam, `USR-03`), `extra_e_padrao_do_perfil`, `administradores`, `dados_do_eu`. `pode` é registrado em `comum.permissoes`.
- `navegacao.py`: a `navegacao` do `eu` (`USR-05`, `USR-08`). Monta `menu_completo`, `menu_inicio` da variante e `barra_celular` a partir do `pode`, dos recursos do plano, da atividade e de `settings.GIRO_MODULOS_ATIVOS`. A variante do administrador (e do suporte) é `implantacao` até o passo `primeira_locacao` (`IMP-01`).
- `senhas.py`: validadores com texto pronto (12 ou mais, letras e números, diferente do e-mail e do nome da empresa, fora das comuns).
- `RedefinicaoSenha`: link de 1 hora, uso único, 3 pedidos por hora; o token vai no fragmento (`/entrar/redefinir#<token>`).
- T-071: navegação do `eu`.

## Implementado (T-070: modo suporte)

- Token `suporte` (ADR 0013, item 2) em `comum.autenticacao`: sem usuário nem refresh, vence no `fim`, conferido no `public` a cada requisição. A autenticação monta um `AtorSuporte` (administrador em todas as filiais) e aplica a regra da view: `suporte_proibido` (sempre 403 `PLT-07`), `suporte_somente_leitura` (o que o "só ver" lê) e `so_suporte`.
- Rotas da conta (`Logada`: sessões, senha, 2 etapas), escrita de usuários e as públicas (entrar, renovar, sair, senha, convite) recusam o token de suporte com 403 `PLT-07`. `GET /api/auth/eu/` devolve `suporte` preenchido e, no "só ver", `pode` só com `painel`, `veiculos` e `administracao`.
- `POST /api/auth/suporte/sair/`: o acesso vai para `encerrado`.

## Implementado (T-069: usuários e convite da empresa)

- `api/usuarios.py` (host da empresa): `usuarios/` (lista com `plano` e `contagens`, filtros `situacao`, `perfil`, `filial`, `busca`), detalhe com `permissoes_extras` (`marcada`, `padrao_do_perfil`) e `entrou_em`, `PATCH` (perfil, filiais, permissões extras), `convites/`, `reenviar-convite`, `link-convite` (copiar link do convite: link novo só na resposta, `no-store`, 5 por hora por convidado e 20 por hora por administrador, evento `usuario.copiar_link_convite` sem o token; T-250), `cancelar-convite`, `desativar`, `reativar`, `redefinir-2fa`, `sessoes` e `sessoes/{sid}/encerrar`. Só o administrador. Públicas: `convites/consultar/` e `convites/aceitar/`, com o token no corpo (P-09) e 30 por minuto por IP.
- `services.py`: `convidar` (e-mail obrigatório e único sem diferenciar maiúsculas, filial obrigatória para quem não é administrador, `exigir_limite` e `atualizar_uso` na transação, envio depois do commit por e-mail e, com celular, por WhatsApp), `gerar_link_convite` (invalida os convites anteriores; base do `reenviar_convite` e do `copiar_link_convite`), `reenviar_convite`, `copiar_link_convite`, `cancelar_convite`, `alterar_usuario` (auditoria `usuario.alterar_perfil` e `usuario.alterar_permissoes`; `ultimo_administrador`), `desativar_usuario` (revoga as sessões na mesma transação; `desativar_a_si_mesmo`), `reativar_usuario` (`USR-04`: quem já foi `ativo` volta `ativo`; quem nunca chegou a `ativo` volta para `convite_pendente` com convite novo e sem a senha antiga; `PLT-03`; `ja_foi_ativo` olha a auditoria), `redefinir_2fa`. `convidar_administrador` usa o mesmo `convidar`; quando o administrador da compra fica `ativo`, marca o passo `conta` da implantação.
- P-06: um convite novo, reenviado ou aceito invalida os outros da pessoa (`expira_em = agora`; o link antigo responde 410). O link sai como `/convite#<token>`, também no convite da equipe da plataforma, que passou para `plataforma/convites/consultar/` e `aceitar/` com o token no corpo.
- `Usuario`: restrição `usuario_email_unico_sem_caixa` em `Lower(email)`.
- WhatsApp atrás de `integracoes/whatsapp` (`GIRO_PROVEDOR_WHATSAPP`, só o falso por enquanto).

## Eventos assinados

| Evento | O que faz |
| --- | --- |
| `plataforma.empresa_criada` | convida o administrador da empresa nova (`convite_pendente`, conta no plano) |

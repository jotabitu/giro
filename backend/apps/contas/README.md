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

## Eventos assinados

| Evento | O que faz |
| --- | --- |
| `plataforma.empresa_criada` | convida o administrador da empresa nova (`convite_pendente`, conta no plano) |

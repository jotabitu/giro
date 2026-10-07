---
name: seguranca
description: Segurança e LGPD do Giro. Revisa autenticação, 2FA, permissões por perfil, isolamento entre empresas, dados pessoais, auditoria, acesso de suporte e uploads. Use ao fim de módulos que tocam dados pessoais, dinheiro ou acesso, e antes de cada fase ir para produção.
---

# Segurança e LGPD

Você procura o que pode vazar, ser burlado ou violar a LGPD, e devolve achados como tarefas.

## Leia primeiro

`CLAUDE.md`, seções "Usuários, perfis e permissões", "Plataforma e assinatura" (acesso de suporte) e "Auditoria, LGPD e exportação" de `docs/regras-de-negocio.md`, requisitos não funcionais em `docs/plano.md`.

## Checklist de revisão

- **Isolamento:** nenhum endpoint, tarefa Celery, exportação ou arquivo cruza empresas. Teste com duas empresas.
- **Autenticação:** Argon2, JWT de 15 minutos com refresh rotativo em cookie httpOnly, 2FA obrigatório para administrador e financeiro (USR-02) e para toda a equipe da plataforma (PLT-08), bloqueio de 15 min após 5 tentativas e expiração de sessão (USR-06), sessões revogáveis (USR-04).
- **Permissões:** cada endpoint checa perfil e filial no backend; vistoriador não recebe valores; vendedor não recebe custo nem margem.
- **Dados pessoais:** CPF e CNH criptografados em repouso, CPF mascarado em listas (AUD-04), fotos em armazenamento privado com URL de 15 minutos (AUD-05), exportação e anonimização do titular (AUD-06).
- **Auditoria:** eventos imutáveis com antes e depois, IP e aparelho (AUD-01); entradas do suporte Giro sempre com motivo e prazo e visíveis para a empresa (PLT-07, AUD-03).
- **Uploads:** tipo e tamanho validados, sem execução, nomes aleatórios.
- **API:** rate limiting, CORS restrito aos subdomínios, cabeçalhos de segurança, OWASP Top 10.
- **Dinheiro:** valores só calculados no servidor; webhooks de pagamento com assinatura verificada e idempotência.

## Não faça

- Não corrija direto em módulos de outros agentes; abra tarefa com severidade (alta, média, baixa), reprodução e sugestão.

## Pronto quando

- O checklist foi aplicado ao módulo, achados altos viraram tarefas no topo do backlog e o relatório está em `docs/seguranca/<data>-<modulo>.md`.

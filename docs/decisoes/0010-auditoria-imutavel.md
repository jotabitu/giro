# Auditoria imutável em cada schema

**Status:** aceita · 07 out 2026

## Contexto

`AUD-01` exige que toda ação que muda dado de negócio grave um evento que ninguém edita ou apaga, nem o dono do produto. Eventos acontecem nas empresas e na plataforma, e as entradas do suporte aparecem nas duas auditorias (`PLT-07`, `AUD-03`). Guardamos por 5 anos (`AUD-02`) e apagamos tudo 90 dias após o cancelamento da assinatura (`AUD-08`).

## Decisão

1. Model `auditoria.EventoAuditoria`, no app `auditoria`, instalado nos dois schemas: no `public` guarda os eventos da plataforma; no schema da empresa, os da empresa. O backend cria o app junto com `comum` em T-001.
2. Campos: `ocorrido_em` (UTC), `ator_tipo` (`usuario`, `sistema`, `suporte`), `ator_id`, `ator_nome` (texto copiado na hora: o nome continua certo mesmo se o usuário mudar), `acesso_suporte_id` (quando suporte), `acao` (texto fechado `<objeto>.<verbo>`, ex.: `locacao.ativar`), `categoria` (`financeiro`, `operacao`, `configuracoes`, `seguranca`, `suporte`), `objeto_tipo`, `objeto_id`, `objeto_codigo` (ex.: `LOC-2856`), `filial_id` (quando houver), `antes` e `depois` (JSON só com os campos mudados), `motivo`, `ip`, `aparelho` (user agent resumido), `regra` (código, quando a ação vem de uma regra, ex.: `AUT-02`).
3. Imutável em três camadas: o model recusa `save()` de registro existente e `delete()`; o manager não expõe `update()`/`delete()`; e uma migração `RunSQL` cria um trigger PostgreSQL que levanta exceção em `UPDATE` e `DELETE` na tabela. O expurgo de eventos com mais de 5 anos é a única exceção: roda numa função SQL que liga `SET LOCAL giro.expurgo_auditoria = 'on'`, conferido pelo trigger. Apagar a empresa (`AUD-08`) é `DROP SCHEMA` e não passa pelo trigger.
4. Quem gravar: o serviço de domínio, sempre dentro da mesma transação da mudança, por `comum.auditoria.auditar(...)` ou pela `MaquinaDeEstados` (que já audita). Não usamos signals `post_save` genéricos: eles não sabem a ação nem o motivo e são contornados por `update()`.
5. Quem é o ator: um middleware preenche um contextvar com usuário, IP e aparelho a partir da requisição autenticada. Tarefas Celery entram com ator `sistema` e a `regra` da tarefa (`AUT-02`). Token de suporte (ADR 0008) entra com ator `suporte`.
6. Ações do suporte: entrada e saída gravam um evento no schema da empresa (categoria `suporte`, com o motivo) e outro no `public`. Cada escrita feita durante o acesso grava só no schema da empresa, com `acesso_suporte_id`.
7. Dados pessoais nos campos `antes`/`depois`: CPF, CNH e documentos são gravados mascarados (`***.218.330-**`), para que a auditoria não vire cópia dos dados pessoais e a anonimização (`AUD-06`) não precise reescrever eventos.

## Consequências

- O índice principal é `(ocorrido_em DESC)`, com índices em `(objeto_tipo, objeto_id)`, `(categoria, ocorrido_em)` e `(ator_id, ocorrido_em)` para a tela `Admin-Auditoria`.
- Teste obrigatório: `UPDATE` e `DELETE` direto no banco falham; toda transição de status de uma máquina grava exatamente um evento.
- A segurança revisa a lista de campos mascarados.

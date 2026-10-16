# T-252 · Link copiável do convite (rota)

**Data:** 16 out 2026 · **Agente:** segurança · **Regras:** USR-01, PLT-07, AUD-01
**Base:** branch `t-250-backend-decisoes-15-out` (PR #272): `apps/contas/services.py` (`gerar_link_convite`, `copiar_link_convite`, `_invalidar_convites`, `convite_pelo_token`), `apps/contas/api/usuarios.py` (`LinkDoConviteView`), `apps/contas/tasks.py` (`contas_enviar_convite`), `comum/limites.py`, `tests/aceitacao/test_t250_decisoes.py`; no frontend, `src/lib/fragmento.ts`.
**Método:** leitura do código e dos testes da T-250, e dois testes novos em `tests/aceitacao/test_t252_seguranca_convite.py`. A tela (T-251) ainda está com o frontend: o que conferir nela está no fim.

## Resumo

A rota está certa nos sete pontos pedidos. Não há achado alto nem médio. Um achado baixo (B-01, com `xfail` estrito) e uma guarda nova de isolamento.

| Ponto | Situação | Onde está provado |
| --- | --- | --- |
| Só administrador | `SO_ADMINISTRADOR`; os outros quatro perfis, 403 | `test_usr_01_copiar_link_so_administrador` |
| Suporte Giro sem acesso | `suporte_proibido = True`: 403 `PLT-07` nos dois modos, antes de qualquer efeito | o mesmo teste, que confere também que nenhum evento foi gravado |
| Link mostrado uma vez | sai só na resposta do `POST`; o banco guarda o hash do token (`secrets.token_urlsafe(32)`, SHA-256); a leitura do usuário não traz link | `test_usr_01_copiar_link_invalida_o_anterior` |
| Fora de log | o token vai no fragmento (`/convite#<token>`), que não chega ao servidor, ao proxy nem ao `Referer`; nenhum middleware registra corpo de resposta; a página `/convite` apaga o fragmento da barra e do histórico (`consumirFragmento`) | `test_usr_01_copiar_link_evento_sem_token` (com `caplog`) |
| `no-store` | `Cache-Control: no-store` na resposta | `test_usr_01_copiar_link_invalida_o_anterior` |
| Limites por hora | 5 por convidado e 20 por administrador; conferidos depois da permissão e antes do serviço (o 429 não gera nem invalida nada); a chave leva o schema (`make_key`), então não cruza empresas | `test_usr_01_copiar_link_limite_*`; **novo:** `test_usr_01_limite_do_link_conta_por_empresa` |
| Evento sem token | `usuario.copiar_link_convite`, categoria `seguranca`, quem copiou, de quem e só `convite_expira_em` | `test_usr_01_copiar_link_evento_sem_token` |
| Invalidação do anterior com 410 | o convite anterior vence na hora (`expira_em = agora`), sob a linha travada da pessoa; o link antigo responde 410 `convite_expirado`; aceitar exige o convite válido | `test_usr_01_copiar_link_invalida_o_anterior` |

**Sobre a `[divergência]` do CA-248-12 (404 ou 410 no link antigo):** do lado da segurança, os dois servem. O 410 só diz "este token existiu e venceu" a quem já tem o token, e isso não ajuda ninguém a adivinhar outro. Manter o 410, igual ao reenvio, evita dois caminhos de invalidação. A escolha é do produto.

## Achado

### B-01 · O e-mail de um convite já invalidado sai com o link morto · baixa

**Onde:** `apps/contas/tasks.py`, `contas_enviar_convite`: confere só `aceito_em`, renova o token e envia.
**Problema:** o e-mail (e o WhatsApp) do convite ou do reenvio vai para a fila depois do commit. Se o administrador copia o link antes de a tarefa rodar, ou se a fila repete a tarefa, o convite do e-mail já está vencido (P-06). Mesmo assim, a tarefa gera um token novo para ele e manda à pessoa um link que responde "expirado". Não abre acesso: o convite vencido não aceita senha. Mas confunde quem recebe, e um e-mail com link de acesso que não vale é o tipo de mensagem que treina a pessoa a ignorar avisos.
**Reprodução:** `test_usr_01_email_de_convite_invalidado_nao_sai` (`xfail` estrito): roda a tarefa do e-mail de um convite que o link copiado já invalidou, e o e-mail sai.
**Sugestão (backend):** a tarefa não envia quando `convite.expira_em <= agora` (ou quando já existe convite mais novo da mesma pessoa), e não renova o token desse convite.

## Risco aceito, sem tarefa

Quem copia o link pode abri-lo e criar a senha no lugar da pessoa convidada. Isso não é escalada: o administrador já escolhe o e-mail e o perfil de quem convida, e pode convidar outra conta. Fica rastreado na auditoria:
- "Copiou o link do convite", com o administrador e a pessoa;
- "Aceitou o convite", com IP e aparelho (`AUD-01`).

O mesmo vale para o reenvio.

## Para conferir na tela (quando a T-251 entrar)

1. O botão aparece só com `acoes.copiar_link_convite`, e o texto do `aviso` vem da resposta, sem texto próprio.
2. O link fica só na memória do componente e no momento de copiar:
   - nada de `localStorage`, `sessionStorage`, URL, título da página nem `console`;
   - na mutação do TanStack Query, sem `mutationKey` persistida e com o resultado descartado ao fechar (`reset()` ou `gcTime: 0`);
   - nada de colocar a resposta no cache da consulta do usuário (`setQueryData`); o detalhe é relido.
3. O link é mostrado uma vez. Ao fechar, ele some; para ver de novo, outro clique gera outro link, o anterior deixa de valer e o aviso diz isso.
4. A cópia usa `navigator.clipboard.writeText`. Se a cópia falhar, a tela mostra o link para seleção manual, sem mandá-lo para log ou Sentry.
5. O 429 e o 409 mostram a mensagem da API como vem; o 429 não tenta de novo sozinho.
6. Nenhum `fetch` ou evento de análise leva o link (o Sentry do frontend, quando existir, sem `breadcrumbs` de resposta dessa rota).

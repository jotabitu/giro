# Reconfirmar as 2 etapas sem sair: access novo na mesma sessão

**Status:** aceita · 21 out 2026 · T-346 (achado M-01 da T-199, feito na T-345) · detalha a 0013 (item 3) e a 0014 (item 1)

## Contexto

O backup completo (`S-15`, `auditoria.md`) e o cancelamento da assinatura (`PLT-06`, `cancelamento.md`, T-345) pedem 2 etapas recentes: `otp` no `amr` e `auth_time` de no máximo 15 minutos (`comum.autenticacao.dois_fatores_recente`). Sem isso, a API responde 403 `2fa_recente`.

Hoje o `auth_time` só nasce no login completo com código (`emitir_tokens` sem `sid`). A rotação do refresh (`auth/renovar/`) não o leva adiante. Na prática, ele dura só o primeiro access do login, que vive 5 minutos. Depois disso, a única saída para o 403 é sair e entrar de novo, o que abre uma sessão nova e perde o que a pessoa já tinha preenchido na tela.

## Decisão

1. **Rota própria.** `POST /api/auth/2fa/reconfirmar/` recebe o código do autenticador ou um código de recuperação e devolve **só um access novo** (`contas.md`, "Reconfirmar as 2 etapas").
2. **A mesma sessão.** O access novo leva o mesmo `sid`, `schema`, `empresa_id` e `amr` do token que chamou, mais `auth_time` = agora. Não abre sessão, não emite refresh e não grava cookie. O refresh vigente da sessão continua o mesmo. Por isso a rota não disputa com um `renovar` de outra aba, que veria o refresh trocado e revogaria a sessão por reuso (P-07).
3. **O `auth_time` nasce em dois lugares só:** no login completo com código e na reconfirmação. A rotação continua sem levá-lo, como a T-345 testou (`test_t345` e `test_t018`). A janela útil é, portanto, a menor entre 15 minutos e a vida do access (5 minutos). Isso basta, porque a tela repete o pedido logo depois de reconfirmar. Quem cancela sem passar pela tela também não precisa de mais.
4. **O mesmo bloqueio do login.** O código passa por `dois_fatores.verificar_codigo`: a mesma trava na linha do usuário e a mesma contagem do login. Na empresa vale a `USR-06` (5 tentativas erradas, somando senhas e códigos, bloqueiam por 15 minutos e avisam os administradores). No `public` valeria a `PLT-08` (3 códigos). O bloqueio vale também para o próximo login, porque a contagem é uma só. A sessão aberta continua.
5. **Auditoria `seguranca`**, sem o código: `usuario.reconfirmar_2fa` no acerto e `usuario.reconfirmar_2fa_falhou` no erro, mais o `usuario.usar_codigo_recuperacao` e o `usuario.bloqueado` que já existem.
6. **Sem autenticador, sem reconfirmação.** Quem não tem 2 etapas recebe 409 `2fa_inativo` e continua recebendo `2fa_recente` nas ações sensíveis até ativar. Hoje isso não alcança ninguém nessas ações: cancelar e o backup são só do administrador, e a `USR-02` obriga o administrador a ter 2 etapas.
7. **A tela reage ao 403.** O frontend não pergunta antes se as 2 etapas estão recentes. Ele tenta a ação; no 403 `2fa_recente`, pede o código, chama a rota e repete o mesmo pedido uma vez, sem recarregar a página.

## Alternativas descartadas

- **Sair e entrar de novo** (o que existe hoje): abre outra sessão, troca o `sid` e apaga o que a pessoa preencheu.
- **Refresh novo com `auth_time`**, como faz o `2fa/ativar/`: a troca do refresh disputa com o `renovar` de outra aba e pode derrubar a sessão por reuso. E levar o `auth_time` na rotação muda o que a T-345 decidiu e testou.
- **Cabeçalho próprio (`X-Giro-2FA`) em cada ação sensível:** cada view passaria a conferir o código, e o código viajaria junto com o corpo da ação. A rota única mantém a conferência num lugar só.
- **Pedir a senha em vez do código:** a `S-15` e o M-01 pedem o autenticador. A senha é o fator que um invasor com a sessão já pode ter.

## Consequências

- `comum.autenticacao` ganha uma função que emite o access reconfirmado a partir das claims do token atual. A docstring de `CLAIM_AUTH_TIME` passa a citar as duas origens. Não há dependência nova nem migração.
- O painel da plataforma não tem ação com `2fa_recente` hoje. Quando tiver, usa a mesma rota em `plataforma.md`, com a `PLT-08`.
- Um invasor com uma sessão roubada pode gastar as tentativas e bloquear o login da pessoa por 15 minutos. O mesmo já acontece com a senha pedida em `2fa/desativar/`. O bloqueio avisa os administradores e fica na auditoria.

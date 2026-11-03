# T-410 · Reserva na confirmação (frontend) · frontend → orquestrador

**O que foi feito (na mesma branch e no mesmo PR #457 do backend):**
- `npm run api:gerar` e dois ajustes de tipo nos falsos: `aguarda_retirada` na conta (`falso-financeiro.ts`) e `automatico` no cancelamento (`falso-locacoes.ts`); o detalhe falso ganhou `prazo_retirada`.
- Veículo: a lista e a ficha já mostravam `situacao.rotulo`; o falso agora manda "Reservado na LOC-x" e o bloco `reserva` (tipo `Veiculo.reserva`). A ficha mostra o rótulo como vem e o link "Ver LOC-x" (desktop e celular). No celular o rótulo era posto em minúsculas (`reservado na loc-2850`); com `reserva` ele agora fica como a API mandou.
- Nova locação: o seletor já lista só `disponivel`, então o reservado não aparece. O falso agora recusa o reservado (`LOC-03`) e imita o `inicio_vencido` (impedimento na simulação e 409 no confirmar com `detalhes.inicio` e `ultimo_dia_retirada`). A tela já mostrava impedimentos e a mensagem do erro do confirmar; nada de data é calculado nela. `prazo_retirada` e `cancelamento.automatico` não aparecem em tela, como o contrato manda.
- `ReservaDoVeiculo.test.tsx`: rótulo e bloco, ficha nos dois tamanhos, lista, reservado barrado, `inicio_vencido` e início de hoje. Suíte inteira (837), lint e typecheck passam.

**Branch:** a `t-410-backend-reserva` está aberta no worktree do Backend, então trabalhei na local `t-410-frontend` e dei push para `origin/t-410-backend-reserva`. Se o Backend empurrar antes, ele precisa de `git pull` primeiro.

**O que ficou de fora:** não conferi a 1440 e a 390 px no navegador. O texto do 409 `inicio_vencido` no falso é meu (a API real manda o dela). O seed da LOC-2856 segue como o Backend deixou (`[decisão]` no backlog).

**Próximo passo para quem recebe:** conferir o CI do #457 e, para o QA, os CA-410 da tela com o ambiente real.

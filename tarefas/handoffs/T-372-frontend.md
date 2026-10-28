# Handoff · T-372 · Modo suporte e controle do suporte (frontend)

- **Agente:** frontend
- **Branch:** `t-372-modo-suporte`, a partir da `origin/main` com o #429 (T-379).
- **Contrato:** `docs/api/contas.md` ("Modo suporte" e "Controle do administrador") e o cartão `suporte` de `docs/api/configuracoes.md`
- **Telas de referência:** `docs/telas/html/Modo-Suporte-Desktop|Mobile.dc.html` e `Admin-Suporte-Desktop|Mobile.dc.html`
- **Regras:** PLT-07, AUD-09

## O que foi entregue

- **Cliente HTTP (`lib/api/http.ts`):** `definirAccessDeSuporte(token)` guarda o token só em memória e liga o modo suporte. Nesse modo qualquer 401 não chama `auth/renovar/`: apaga o token, sai do modo e avisa quem escuta em `aoTerminarSuporte`. O 403 `PLT-07` segue como erro normal, com a `mensagem` da API, sem sair do modo. `definirAccess` (login comum) desliga o modo.
- **`contas.entrarComoSuporte(token)`** chama `GET /api/auth/eu/` com o token; se a resposta vier sem `suporte` ou falhar, o token não fica na memória. **`contas.sairDoSuporte()`** chama `POST /api/auth/suporte/sair/` e limpa a memória.
- **Página `/suporte/entrar`** (`EntradaDoSuporte`, rota pública): `useTokenDoFragmento` lê e apaga o fragmento antes de qualquer chamada. Com 200 e `suporte`, grava o `eu` no cache e vai para `navegacao.inicio.rota`. Sem fragmento, com 401 ou com token de outra empresa, mostra "O acesso de suporte terminou", sem botão nem campo de login. Com `?saiu=1` mostra "Você saiu do modo suporte".
- **Faixa (`FaixaDoSuporte`)**, no layout de `(empresa)` dentro do `SessaoProvider`: fixa, não fecha, cor de aviso. Mostra "Modo suporte", nome, "Equipe Giro", motivo, `permissao_rotulo`, `fim_rotulo` e "Sair do suporte". Sem contagem regressiva. Erro ao sair aparece na própria faixa.
- **`SessaoProvider`:** o fim do suporte (ouvinte do cliente HTTP ou `eu` com 401 `PLT-07`) leva a `/suporte/entrar`, não ao `/entrar`.
- **`/admin/suporte`** (`ControleDoSuporte`): situação (`situacao_rotulo`), "Bloquear suporte Giro" com diálogo ("Revoga na hora qualquer acesso ativo", motivo opcional) ou "Liberar suporte Giro", os três blocos de texto fixo (com "Cada alteração"), chips Todos/Ativos/Encerrados com `contagens` e `?situacao=`, lista com `status_rotulo`, `permissao_rotulo` e "Revogar acesso" só com `acoes.revogar` (com confirmação). Sem e-mail do operador. Quem não é administrador vê o aviso; o 403 `PLT-07` do token de suporte aparece pela `mensagem` da API.
- **Cartão de Configurações:** `CARTOES.suporte` abre `/admin/suporte`. A tela mostra o que a API manda, então o token de suporte (que não recebe o cartão) não o vê. Bloquear, liberar e revogar invalidam `["suporte"]` e `["configuracoes"]` para o resumo do cartão atualizar.
- **Fixtures:** `falso-suporte.ts` (3 acessos do contrato; `reiniciarSuporteFalso()`), `contasFalso.entrarComoSuporte` ("suporte-valido" entra; outro token dá 401 `PLT-07`) e `sairDoSuporte`.

## Pontos para o orquestrador e o backend

- **`eu.suporte` ainda não traz `permissao_rotulo` e `fim_rotulo`.** O contrato (T-358) manda, mas o backend de contas não os devolve e o OpenAPI (`SuporteDoEu`) também não tem. Tipei os dois como opcionais em `Eu.suporte`. Sem eles, a faixa mostra o rótulo fixo da permissão ("Só ver" / "Ver e editar") e omite o horário de fim. Falta a tarefa de backend (`test_plt_07_eu_traz_rotulos_do_suporte`); depois é só tornar os campos obrigatórios.
- **Enum `CartaoDeConfiguracoesChaveEnum` sem `suporte`** (já faltava `ramo`): acrescentei `| "suporte"` em `tipos-configuracoes.ts`, como foi feito com o `ramo`. Sai quando o backend regenerar o enum.
- **Recarregar a página no modo suporte** perde o token (só memória, como manda o contrato): a renovação por cookie não existe para o suporte, e a pessoa volta a pedir o link.
- A faixa é `sticky top-0`; a sidebar sticky do desktop fica sob ela quando a página rola. Vale uma passada visual do design-system a 1440px e 390px.

## Verificação

- `npx tsc --noEmit` e `npx eslint .`: limpos. `npx vitest run`: 88 arquivos, 799 testes passando.
- Testes novos: `http.test.ts` (token de suporte no Bearer sem cookie, 401 `PLT-07` sem `renovar` com token apagado e aviso, 401 de outra empresa, resposta sem `suporte`, 403 mantém o modo, sair limpa a memória, login comum desliga o modo), `FaixaDoSuporte.test.tsx`, `EntradaDoSuporte.test.tsx` e `ControleDoSuporte.test.tsx`. O apagar do fragmento já é coberto por `fragmento.test.ts`.
- Os testes rodam em `node`, sem DOM: o clique em Bloquear, Liberar, Revogar e Sair está coberto pelas fixtures e pelas chamadas do cliente, não por clique. Vale uma passada manual ou do QA com um link real de suporte.

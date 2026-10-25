# Handoff · T-348 · Diálogo das 2 etapas recentes na Admin-Cancelar (frontend)

- **Agente:** frontend
- **Branch:** `t-348-dialogo-2-etapas`
- **Contrato:** `docs/api/contas.md` ("Reconfirmar as 2 etapas" e "Como a tela trata o 403 `2fa_recente`"), ADR 0032
- **Regras:** USR-02, USR-06, PLT-06

## O que foi entregue

1. **Chamada (`frontend/src/lib/api/contas.ts`):** `contas.reconfirmar2fa({ codigo | codigo_recuperacao })` chama `POST /api/auth/2fa/reconfirmar/` com o access da sessão e troca o access em memória (`definirAccess`). Não toca em cookie nem em refresh.
2. **Auxiliar (`frontend/src/lib/reconfirmar-2fa.ts`):**
   - `comReconfirmacao(acao, pedir)`: roda a ação; no 403 `2fa_recente` chama `pedir(mensagem)` e repete a ação uma vez, com o mesmo corpo. Se a repetição voltar `2fa_recente`, o erro sobe e não há outra volta.
   - `confirmarCodigo(reconfirmar, corpo)`: 400 vira erro no campo (diálogo aberto); 429, 409 `2fa_inativo` e o resto encerram com o erro.
   - `ReconfirmacaoCancelada`: "Cancelar" não envia nada.
3. **Diálogo e hook (`frontend/src/components/acesso/DialogoReconfirmar2fa.tsx`, `useReconfirmar2fa.tsx`):** o hook devolve `executar(acao)` e `dialogo`; a tela renderiza `dialogo`. Texto do diálogo = `mensagem` do 403; campo `CodigoVerificacao` e link "Usar um código de recuperação" com as palavras do `Login`. O código é limpo do estado no envio e não passa pelo TanStack Query.
4. **Admin-Cancelar (`CancelarAssinatura.tsx`):** o cancelamento roda dentro de `executar`. Motivo, observação e nome digitado continuam preenchidos, nada recarrega. 429 e 409 aparecem no aviso de erro da tela, com o horário do bloqueio (`mensagemDoErro`). Cancelar o diálogo não mostra erro.
5. **Falso de desenvolvimento (`frontend/src/testes/falsos/falso.ts`):** `reconfirmar2fa` com o código `123456`.

## Para a fase 2 (backup completo)

Basta `const { executar, dialogo } = useReconfirmar2fa()`, `executar(() => chamada())` e `{dialogo}` na tela.

## Verificação

- `npx tsc --noEmit`: limpo. `npm run lint`: limpo. `npx vitest run`: 74 arquivos, 700 testes passando.
- Testes novos: `reconfirmar-2fa.test.ts` (caminho feliz, sem 403, outros erros, cancelar sem repetir, segunda recusa sem laço, 400 no campo, 400 do código de recuperação, 429, 409), `http.test.ts` (rota, access trocado, 400 mantém o access) e `CancelarAssinatura.test.tsx` (palavras e ordem do diálogo).
- Não há DOM nos testes (ambiente `node`): o fluxo com o diálogo aberto foi coberto na lógica, não por clique. Vale uma passada manual ou do QA em 1440px e 390px.
- Nenhuma tela de Veículos foi tocada.

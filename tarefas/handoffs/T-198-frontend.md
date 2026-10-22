# Handoff · T-198 · Cancelar assinatura e pausa (frontend)

- **Agente:** frontend
- **Branch:** `t-198-cancelar-pausar-tela`
- **Contrato:** `docs/api/cancelamento.md`
- **Telas de referência:** `docs/telas/html/Admin-Cancelar-Desktop.dc.html`, `docs/telas/html/Admin-Cancelar-Mobile.dc.html`, `docs/telas/html/Admin-Assinatura-Desktop.dc.html`, `docs/telas/html/Admin-Assinatura-Mobile.dc.html`
- **Critérios cobertos:** CA-ASS-30, 31, 35 a 38, 43 a 45, 54 a 56 e CA-ASS-69 (`docs/qa/criterios/assinatura.md`)

## O que foi entregue

1. **Cliente tipado e rotas de cancelamento e pausa (`frontend/src/lib/api/tipos-assinatura.ts`, `frontend/src/lib/api/assinatura.ts`):**
   - `npm run api:gerar` conferido com o `openapi.yaml` da `main` (T-195).
   - Rotas `telaCancelamento()` (`GET /api/assinatura/cancelamento/`), `cancelar(corpo)` (`POST /api/assinatura/cancelamento/`), `desfazerCancelamento()` (`DELETE /api/assinatura/cancelamento/`), `pausar(corpo)` (`POST /api/assinatura/pausa/`) e `encerrarPausa()` (`DELETE /api/assinatura/pausa/`).
2. **Tela `Admin-Cancelar` (`/admin/assinatura/cancelar`, `frontend/src/components/admin/CancelarAssinatura.tsx`):**
   - Lê `GET /api/assinatura/cancelamento/`: resumo do plano no cabeçalho, os 5 motivos e campo opcional de observação, bloco "Antes de ir, que tal…" (oferta de pausar por até 3 meses somente quando `alternativas.pausar` vem preenchido na `ativa`, e oferta de mudar para o Essencial abrindo `PlanosDaAssinatura`), quadro "O que acontece" com os rótulos e valores vindos da API (incluindo "termina agora" quando `acesso_ate` é nulo, CA-ASS-69), confirmação com o nome da empresa (`nomeConfere`, CA-ASS-31), atalho "Exportar dados antes" para `/admin/exportar` e aviso de exportação da API (CA-ASS-38).
   - Quando o cancelamento encerra a assinatura na hora (`status: "cancelada"`), mostra a mensagem de assinatura cancelada; quando agenda para o fim do período, atualiza a cache de `["assinatura"]` e volta para `/admin/assinatura`.
3. **Diálogo de pausa e ações em `Admin-Assinatura` (`frontend/src/components/admin/DialogoPausarAssinatura.tsx`, `frontend/src/components/admin/AssinaturaDaEmpresa.tsx`):**
   - Escolha de 1, 2 ou 3 meses para pausar (`POST /api/assinatura/pausa/`, CA-ASS-37, CA-ASS-54).
   - Exibição de `cancelamento.rotulo` + aviso e botão "Desfazer cancelamento" (`acoes.desfazer_cancelamento`, `DELETE /api/assinatura/cancelamento/`, CA-ASS-35, CA-ASS-43, CA-ASS-44).
   - Exibição de `pausa.rotulo` e botões "Voltar da pausa" (`acoes.voltar_pausa`, na `pausada`, CA-ASS-36) e "Desistir da pausa" (`acoes.desistir_pausa`, pausa agendada na `ativa`, CA-ASS-55), ambos chamando `DELETE /api/assinatura/pausa/`.
   - Link "Cancelar assinatura" para `/admin/assinatura/cancelar` quando `acoes.cancelar` é `true`, junto com "Exportar dados antes" e o texto da exportação (CA-ASS-38).
4. **Sessão com `empresa_cancelada` (`frontend/src/lib/sessao.tsx`):**
   - Quando `/api/auth/eu/` responde `403 empresa_cancelada`, `SessaoProvider` exibe a mensagem da API.

## Verificação

- `npm run typecheck`: limpo (0 erros).
- `npm run lint`: limpo (0 erros).
- `npx vitest run src/components/admin/Assinatura.test.tsx src/components/admin/AssinaturaAcoes.test.tsx src/components/admin/CancelarAssinatura.test.tsx`: 3 arquivos, 42 testes passando.
- Nenhuma tela de Veículos foi tocada.

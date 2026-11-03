# T-412 · Faixa de assinatura suspensa ou pausada · frontend → orquestrador

**O que foi feito:**
- `frontend/src/components/casca/FaixaDaAssinatura.tsx`: faixa fixa no topo de todas as telas da empresa enquanto `eu.empresa.status` for `suspensa` ou `pausada` e `somente_leitura` for verdadeiro (`PLT-02`, `PLT-06`). O texto é o `faixa_aviso` de `GET /api/assinatura/` (aberto a todos os perfis); se faltar, entra um texto fixo sem data nem valor. Administrador vê "Pagar a fatura" (suspensa) ou "Ver a assinatura" (pausada), ambos para `/admin/assinatura`; os outros perfis veem "Fale com o administrador da empresa.". Sem pop-up e sem botão de fechar.
- `frontend/src/app/(empresa)/layout.tsx`: a faixa do suporte e a nova ficam num mesmo bloco fixo, para não se sobreporem quando as duas aparecem.
- `FaixaDaAssinatura.test.tsx`: cinco testes (suspensa, pausada, perfil sem administração, estados sem faixa, texto de reserva). Lint, typecheck e Vitest da pasta `casca` passam.

**O que ficou de fora:** não conferi a 1440 e a 390 px no navegador. O layout é `flex-wrap` com alvo de toque de 44 px; vale um olhar do QA ou do design-system. A faixa da `inadimplente` continua só na `Admin-Assinatura` (fora do escopo da tarefa).

**Próximo passo para quem recebe:** abrir o PR da branch `t-412-faixa-assinatura-suspensa` para a `develop` e preencher o número do PR no `tarefas/feito.md`.

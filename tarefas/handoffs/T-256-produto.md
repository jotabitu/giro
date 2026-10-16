# T-256 · Decisões do dono de 16 out e divergências da T-253 · produto → orquestrador, arquiteto, design-system, backend, qa

**O que foi feito:** a branch `t-256-decisoes-16-out` sai da `origin/main`.

- `docs/regras-de-negocio.md`:
  - **Seção nova "Decisões de 16 out 2026",** com os dois pontos da T-247 aprovados pelo padrão: fase B (CRLV-e no MVP, CNH-e na fase 2) e o PDF da CNH-e valendo pelas fotos (A). Os dois saíram de "Pontos em aberto".
  - **`VEI-08`:** entra no MVP.
  - **`CLI-11`:** fase 2; o PDF lido vale pela foto da CNH, frente e verso; selfie e comprovante continuam obrigatórios. A **`CLI-03`** cita a troca.
  - **Etapa 7 da implantação:** o passo 7 mostra o mesmo conteúdo da troca do ramo em Configurações (`Admin-Ramo`). Saem "Como você aluga" e "CNH exigida", porque nenhuma regra os pede. A nota de mudança está em Implantação.
- `docs/qa/criterios/assinatura.md`, **CA-ASS-50:**
  - o caso é marcado como fixture;
  - o texto passa ao da API, "1 venda aberta e 1 comissão a pagar";
  - entra o caso do seed: "51 locações abertas" (42 da carteira e 9 reservas).
- `docs/qa/criterios/T-247.md`: a fase decidida.
- `tarefas/backlog.md`: seção da T-256, com as respostas às divergências da T-253 e uma proposta sem número para o design-system (`Onboarding-Ramo`).

**Regras cobertas:** VEI-08, CLI-11, CLI-03, PLT-12, etapa 7.

**O que ficou de fora:**
- o item (1) da T-253, o cartão `ramo` em `GET /api/configuracoes/`, que é do arquiteto;
- a tela do passo 7, que é do design-system e espera número;
- o "deixar de vender" no seed, que depende das vendas e comissões do seed (T-019): o qa confere o número quando elas existirem.

**Para quem recebe:**
- **Arquiteto:** a ADR da T-247 pode tratar o CRLV-e como MVP e a CNH-e como fase 2.
- **Backend:** quando a CNH-e entrar, o documento lido conta como a CNH no cadastro completo (`CLI-03`).
- **Design-system:** `Onboarding-Ramo` pelo `Admin-Ramo-*`, quando o orquestrador numerar.
- **QA:** a nova linha do CA-ASS-50 com o seed.

# T-262 · Troca do ramo em Configurações (tela) · frontend → qa, backend, orquestrador

**O que foi feito:**
- Rota `/admin/ramo` (`Admin-Ramo-Desktop` e `-Mobile`), componente `AdminRamo`, ligada a `GET` e `PUT /api/ramo/` (`lib/api/ramo.ts`, `ramo.obter` e `ramo.trocar`). Atividades, avisos ("Vendas faz parte do plano Profissional."), tipos e a lista "Módulos que vamos ligar" vêm da API; a tela só marca, e `atividades_aceitas` decide o que dá para desmarcar (no Essencial, "Locação" fica travada).
- Recusa 422 `PLT-12`: mostra a mensagem da API, "Manter o ramo atual" e, no motivo `abertos`, o link para a lista do módulo apontado em `recurso` (`locacoes_vistoria` → `/locacoes`, `vendas_comissoes` → `/vendas`). Salvar ok invalida `configuracoes` e `eu` (cartão e menu mudam).
- Cartão `ramo` no hub de Configurações (ícone e rota em `lib/configuracoes.ts`; título e resumo da API). `/admin/ramo` entra em `rotaPermitida` só para o administrador.
- Dados falsos de teste: `testes/falsos/falso-ramo.ts` (Profissional e Essencial); `falso-configuracoes.ts` ganhou o cartão.

**Onde:** `frontend/src/components/admin/AdminRamo.tsx`, `src/lib/ramo.ts`, `src/lib/api/ramo.ts`, `src/app/(empresa)/admin/ramo/page.tsx`, `src/lib/menu.ts`, `src/lib/configuracoes.ts`.

**Regras cobertas:** PLT-12, PLT-07. Testes: `AdminRamo.test.tsx` (Profissional, Essencial, Salvar desligado sem mudança, rota só do administrador, `podeAlternar`, `recusaDoRamo`) e `Configuracoes.test.tsx` (9 cartões).

**Para o backend:** `CartaoDeConfiguracoesChaveEnum` no OpenAPI não tem `ramo` (a API manda o cartão, o enum não). Alarguei o tipo `ChaveDoCartao` no frontend com `| "ramo"` (`tipos-configuracoes.ts`); quando o enum for regenerado com `ramo`, é só tirar o `| "ramo"`.

**O que ficou de fora:**
- Passo `Onboarding-Ramo` do assistente: o assistente de implantação ainda não tem casca por passo, então não há onde ligar. A `AdminRamo` e `lib/ramo.ts` podem ser reaproveitados.
- O cabeçalho "N módulos no plano {nome}" da referência virou "N módulos no seu plano": o nome do plano não vem em `GET /api/ramo/`.
- Verificação visual em 1440 e 390 px não feita (sem backend no ar nesta sessão); só typecheck, lint e testes afetados.

**Próximo passo:** qa confere o cartão e a troca no navegador com o seed; orquestrador abre o PR (depende do #344).

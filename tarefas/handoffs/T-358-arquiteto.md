# T-358 · Contratos que faltam na fase 1 · arquiteto → orquestrador, backend, frontend, design-system

**O que foi feito:** contratos escritos a partir das decisões do dono de 25 out, da `IMP-07` do Produto (T-356, branch `t-356-regras-decisoes-25-out`) e das telas da T-360 (branch `t-360-telas-referencia-fase-1`). **Nenhuma ADR nova:** a ADR 0007 já cobre os recebimentos, a 0013 cobre o suporte e a 0029 cobre o Admin.

1. **`plataforma.md`:**
   - **"Quando cada passo conta como feito" (`IMP-07`):** `precos` conta no primeiro preço vigente, gravado já valendo hoje. O preço só agendado para o futuro marca na primeira leitura depois da data. `equipe` conta no primeiro convite, sem contar o do administrador da compra. `recebimentos` passa a contar só na subconta **aprovada**: hoje o código marca ao criar a subconta `pendente`. `filial` conta na matriz. Desfazer não desmarca.
   - **"Rotas de cada passo do assistente":** cada passo usa as rotas de Configurações; não há rota nova de assistente.
   - **"Recebimentos da empresa":** `GET /api/recebimentos/` traz a situação com textos prontos, a sugestão de campos para o formulário e a consulta ao parceiro no máximo uma vez por minuto quando `pendente`. `POST /api/recebimentos/` liga a subconta pelo `conectar_recebimentos`. Só o administrador; Essencial 403 `PLT-12`; suporte 403 `PLT-07`.
   - **"Abrir o acesso de suporte pelo Django Admin":** ação na lista de `Empresa` pelo `abrir_acesso_suporte`. O link aparece uma vez, sem passar pelo framework de mensagens, pelo log nem pelo `LogEntry`.
2. **`configuracoes.md`:** cartão `suporte` ("Suporte liberado" ou "bloqueado", com os acessos ativos), que não vem para o token de suporte e abre `/admin/suporte`. O teto de queries vai para 12.
3. **`contas.md`:**
   - página `/suporte/entrar` (fragmento apagado, token só em memória, 401 `PLT-07` sem `renovar`);
   - faixa com `permissao_rotulo` e `fim_rotulo` novos no `eu.suporte`;
   - tela `Admin-Suporte` (`contagens`, `?situacao=`, rótulos, `acoes.revogar`, sem o e-mail do operador);
   - itens `reembolsos` e `pendencias_pagamento` no menu.
4. **`financeiro.md`:** telas `Reembolsos` e `Pendências do pagamento` (indicadores, contagens, filtros, busca, textos prontos e `acoes`).
5. **`painel.md`:** contadores `reembolsos` e `pendencias_pagamento`.

**Divergências das telas de referência, que o design-system ajusta:**
- **`Onboarding-Recebimentos`:** sem banco, agência e chave Pix (S-05), sem os interruptores de forma de cobrança e sem os lembretes configuráveis (`AUT-03` fixa). O formulário passa a ter os dados da subconta.
- **`Reembolsos` e `Pendências`:** sem "Exportar", sem prazo médio e meta, sem a chave Pix do cliente e sem o selo "Integração Asaas · Online". O menu da tela abrevia "Pendências de pgto"; o rótulo é "Pendências do pagamento".
- **`Admin-Suporte`:** sem o e-mail do operador. O bloco da auditoria deve dizer "Cada alteração", não "cada clique, tela vista".
- **`Modo-Suporte`:** sem o "restam 42 min".

**Para o Produto (não bloqueia):**
- nova tentativa de recebimentos depois de `recusada`: no MVP, com a equipe Giro;
- se o texto do cancelamento cita os 30 dias das cópias de segurança (ADR 0033).

## Tarefas que saem daqui (sem número)

| Agente | Pronto quando | Depende de |
| --- | --- | --- |
| backend | `IMP-07`: marca `precos` (gravação e leitura depois da data), `equipe` e `filial` na matriz; `recebimentos` sai do `conectar_recebimentos` e vai para a transição `aprovada`. Testes `test_imp_07_*` de `plataforma.md` | merge da T-356 |
| backend | `GET`/`POST /api/recebimentos/` com consulta limitada, textos, `sugestao`, 403 `PLT-12` e `PLT-07`, eventos. Testes `test_fin_04_*`, `test_plt_12_recebimentos_essencial_403` e `test_plt_07_recebimentos_recusa_suporte`. OpenAPI | — |
| backend | Suporte: ação "Entrar como suporte" no Django Admin com o link uma vez (`test_plt_07_admin_abre_suporte_pelo_servico`); `permissao_rotulo` e `fim_rotulo` no `eu`; `GET /api/suporte/` com contagens, filtro, rótulos e `acoes`; cartão `suporte` em Configurações (teto de 12 queries). OpenAPI | — |
| backend | Reembolsos e pendências: listas com indicadores, contagens, filtros, busca, textos e `acoes`; itens de menu e contadores. Testes `test_dev_02_lista_de_reembolsos_*`, `test_aut_05_*` e `test_plt_12_pendencias_essencial_403`. OpenAPI | — |
| frontend | `/suporte/entrar`, a faixa e "Sair do suporte"; cliente HTTP sem `renovar` com o token de suporte; `/admin/suporte`. Testes vitest de `contas.md` | backend do suporte; merge da T-360 |
| frontend | `/financeiro/reembolsos` e `/financeiro/pendencias-pagamento` pelas telas da T-360 e pelos contratos | backend de reembolsos e pendências; merge da T-360 |
| frontend | Os 5 passos do assistente (T-364), agora com as rotas de cada passo e com o passo Recebimentos | backend de recebimentos e da `IMP-07`; `/admin/precos` (T-359) para os preços |
| design-system | Ajustes de `Onboarding-Recebimentos`, `Reembolsos`, `Pendencias-Pagamento`, `Admin-Suporte` e `Modo-Suporte` pela lista de divergências acima | — |

**Onde:** `docs/api/plataforma.md`, `docs/api/configuracoes.md`, `docs/api/contas.md`, `docs/api/financeiro.md`, `docs/api/painel.md` e `tarefas/feito.md`.
**Regras cobertas:** `IMP-07`, `FIN-04`, `PLT-07`, `PLT-12`, `DEV-02`, `AUT-05`, `AUD-05`, `AUD-09` (nenhuma muda).
**Próximo passo para quem recebe:** o orquestrador numera as tarefas. As do backend saem já; as do frontend vêm depois do backend e do merge da T-360. Branch `t-358-contratos-fase-1`, sem PR.

# T-322 · Guarda de rota sem o `eu` · frontend → orquestrador, qa

**O que foi feito:** investiguei o "Seu perfil não tem acesso a esta página." visto na 1ª carga do quadro das Movimentações (T-321) e **não encontrei no frontend um caminho que decida sem o `eu`**. Não mudei código de produção; acrescentei o teste que fixa o contrato.
- `SessaoProvider` (`lib/sessao.tsx`) é o ponto comum: sem `consulta.data` ele devolve só "Carregando…" (`aria-busy`), e `GuardaDeRota`, `rotaPermitida` e toda tela que lê `pode.*` chamam `useSessao()` dentro dele. Conferi Frota, Despesas, Receber, Aprovações, Admin, Clientes, Locações, Início e Movimentações: todas usam `useSessao`; nenhuma lê `["eu"]` nem `contas.eu()` fora do provider (grep).
- Teste novo `src/lib/sessao-carregando.test.tsx`: com o `eu` ainda carregando, renderiza o provider com a guarda e mostra só "Carregando…" (sem o aviso e sem a tela); com o `eu` pronto e a rota fora do menu, mostra o aviso. Typecheck e eslint limpos; 25 testes (este, `sessao.test.ts`, `GuardaDeRota.test.tsx`) passando.
- Tentei reproduzir três vezes (login pelo formulário e navegação direta, 1440px) e o quadro abriu certo sempre, com o item Movimentações no menu.

**Hipótese para a ocorrência:** naquela carga o **menu também veio sem Movimentações** (o `eu` já estava carregado, mas o `navegacao`/`pode` dele não trazia o item). Isso aponta para a API da pilha atendendo, logo depois da migração, com o processo ainda sem o módulo `movimentacoes` ativo (`GIRO_MODULOS_ATIVOS` só vale depois de reiniciar o backend), e não para a guarda decidir cedo demais. Sugestão ao qa/devops: se voltar a aparecer, conferir `GET /api/auth/eu/` (chave `movimentacoes` em `navegacao`) antes de culpar a tela.

**Próximo passo:** orquestrador decide se basta o teste ou se o devops confirma o reinício do backend após o `migrate_schemas`.

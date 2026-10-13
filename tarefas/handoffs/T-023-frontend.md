# T-023 · Telas do financeiro básico · frontend → orquestrador, qa, design-system, produto

**O que foi feito:** Contas a receber, Caixa do dia e o ajuste do início do financeiro, em desktop e celular, ligados à API real (`/api/financeiro/`, contrato de `docs/api/financeiro.md` com as emendas da T-144).
1. **Contas a receber** (`/financeiro/receber`): indicadores (previsto no mês, recebido, vence hoje, em atraso), faixas de atraso (`FIN-02`), abas Todas, Em atraso, Vencem hoje, A vencer e Pagas com a contagem da API, busca por cliente, contrato ou placa, período Hoje, Semana e Mês, lista com situação (`25 dias`), "Cobrar", "Cobrar todos pelo WhatsApp" (até 100 contas, na aba Em atraso) e "Dar baixa" (celular e detalhe). Detalhe da conta (clique na linha): valor do dia com a composição, forma, Pix e boleto gerados (copia e cola, linha digitável), histórico traduzido de `acao`, cancelar e estornar com motivo. "Novo lançamento" (multa, avaria ou outro) escolhe o cliente pela mesma busca da locação.
2. **Caixa do dia** (`/financeiro/caixa`): sem caixa aberto, pede o troco (`FIN-07`). Aberto: resumo por forma, movimentos (Todos, Entradas, Saídas), "Receber pagamento" (acha a conta, mostra o `valor_hoje`, Pix com `no_caixa`, cartão débito ou crédito, dinheiro), gaveta, sangria e fechar caixa (contado e motivo da diferença). Mostra o status em qualquer estado (`aguardando_aprovacao` com a diferença e o motivo, `fechado` com quem fechou, `fechado_sem_conferencia`) e esconde as ações que a API não liberou (`acoes`).
3. **Início do financeiro** (`/inicio`, já existia): o status do caixa agora cobre os quatro valores da API e a linha do caixa leva a `/financeiro/caixa`.

**Onde:** `frontend/src/components/financeiro/` (`ListaReceber`, `DetalheDaConta`, `BaixaDaConta`, `NovoLancamento`, `CaixaDoDia`, `ReceberNoCaixa`, `Comuns`), `lib/financeiro.ts` (só textos), `lib/api/{financeiro,tipos-financeiro}.ts`, `testes/falsos/falso-financeiro.ts`, rotas em `app/(empresa)/financeiro/{receber,caixa}`. `components/lista/Paginacao.tsx` ganhou o slot `extra` para o botão do lote.

**Contrato:** `docs/api/openapi.yaml` sem mudança; rodei `npm run api:gerar`.

**Regras cobertas:** FIN-01 a FIN-03, FIN-04, FIN-07, FIN-15, APR-04 (a tela mostra o pedido e a diferença; quem aprova é a tela de aprovações). Nada é calculado no cliente: o valor da baixa é o `valor_hoje.total_centavos` que a API devolveu e a diferença do caixa só é mostrada. Testes: `components/financeiro/Financeiro.test.tsx` (ordem do texto contra as referências, R$ 1.646,40 em atraso, 30609 de Carlos, caixa de R$ 1.111,90 e gaveta de R$ 281,00, FIN-01, FIN-07, CA-017-14 e CA-017-15 na camada falsa).

**[divergência] tela × contrato:**
1. "Exportar" (Receber) não existe: o contrato não tem exportação de contas a receber. O botão não aparece.
2. O seletor de período Hoje, Semana e Mês do início do financeiro não aparece: a variante `financeiro` do painel não depende do período (só a `geral` depende).
3. O KPI "Previsto no mês" sai "R$ 52 mil" (formatador comum dos painéis tira o ",0"); a referência mostra "R$ 52,0 mil".
4. O cartão do caixa na referência é um só ("Cartão"); a API exige débito ou crédito na baixa, então escolher Cartão abre a escolha Débito ou Crédito.
5. O fechamento mostra sempre o campo "Motivo da diferença, se houver", porque a tela não pode saber a diferença antes da API; sem motivo e com diferença, a API recusa e o erro aparece no campo.
6. "Saldo em contas", fluxo previsto e conciliação seguem fora (fase 2, `null` na API).

**O que ficou de fora:** renegociar (`acoes.renegociar`) e o estorno de movimento do caixa; Despesas e Reembolsos (os destinos "Pagar" e "Devolver" do início apontam para `/financeiro/despesas` e `/financeiro/reembolsos`, que ainda não têm tela); a régua de cobrança e o histórico da análise (T-148, como pedido). "Cobrar" mostra o que a API respondeu (`enviadas`): 0 vira "Nada foi enviado ... a conta já foi cobrada hoje ou o cliente não tem contato".

**Conferência no compose: NÃO feita.** O worktree não tem `.env`, o compose não subiu e `make` não existe neste Git Bash; o `.env.example` está bloqueado para o agente por regra de permissão, então não criei o `.env`. Falta conferir em `motorapida.localhost:3000` (Lúcia, financeiro; Mariana, administradora; Bruna, caixa) em 1440 e 390 px, com seed e a data de referência.

**Verificação feita:** `npm run lint`, `npm run typecheck`, `npm test` (319 testes) e `npm run build` limpos.

**Para o design-system:** faltam Select, Textarea, campo de dinheiro (usei `TextField` com `centavosDoTexto`), grupo de opções em botão (criei `EscolhaDeOpcao` local) e o filtro em chips (já pedido na T-046).

**Próximo passo:** orquestrador abre o PR depois da conferência no compose. QA: o fluxo "baixa no caixa" da T-025 usa estas telas. Frontend: tarefas de Despesas, Reembolsos e renegociar.

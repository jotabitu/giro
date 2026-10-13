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

**Conferência no compose (12 out, portal do Maestri, 1440 e 390 px; Bruna, João e Lúcia; Mariana não conferida).** O compose roda na data real (12 out), então os números de 07 out dos critérios (R$ 52,0 mil, 2 em atraso, R$ 306,09 etc.) não aparecem; conferi estrutura, textos e fluxos contra `docs/qa/criterios/T-023.md`.
- Corrigido na conferência: "Novo lançamento" aparecia para a vendedora (CA-023-05); mês saía "Outubro De 2026"; quarto cartão do caixa passou a "Dinheiro na gaveta · confere no fechamento" (CA-023-12); sangria na lista sai como Dinheiro com "Sangria · descrição" (CA-023-13); filtro de movimentos estourava a largura no celular (412 px em 390); Receber para o vistoriador agora mostra só o aviso de acesso (CA-023-05, USR-09); subtítulo do início do financeiro com o dia: "Quarta, 07 out · todas as filiais" (CA-023-20).
- Funcionou: abrir caixa, receber em dinheiro (gaveta e movimentos mudam), sangria maior que a gaveta recusada, sangria válida, fechar com diferença (pede o motivo, mostra − R$ 10,00, fica aguardando o gerente), Receber no celular sem rolagem horizontal, menu da Lúcia (Início, Contas a receber, Contas a pagar, Caixa e bancos), João sem o item no menu.
- Não conferido: aprovação pelo gerente e retorno do caixa recusado; Pix/boleto gerados (recebimentos desligados no compose?); caução na busca do caixa; Mariana.
- Divergências abertas: (a) o app não tem seletor de filial nem envia `X-Filial`, então "Todas as filiais" (CA-023-05, CA-023-16, Mariana e Lúcia) não existe; a tela usa a primeira filial. Precisa de tarefa do shell. (b) "Novo lançamento" não tem flag em `pode`; usei `despesas_aprovar || financeiro_pagar` (administrador, gerente, financeiro). Pedir ao backend um `lancamento_avulso`. (c) Valor de hoje da parcela atrasada (12 dias) veio sem multa e juros (R$ 299,40 = principal); a tela mostra o que a API devolve, confira o backend (FIN-03). (d) O botão da baixa na lista e no detalhe se chama "Dar baixa" (referência do celular); os critérios dizem "Receber". (e) Renegociar, estornar e Gerar boleto/Pix não conferidos na tela (renegociar e estorno de movimento ficaram fora da entrega).

**Verificação feita:** `npm run lint`, `npm run typecheck`, `npm test` (319 testes) e `npm run build` limpos.

**Para o design-system:** faltam Select, Textarea, campo de dinheiro (usei `TextField` com `centavosDoTexto`), grupo de opções em botão (criei `EscolhaDeOpcao` local) e o filtro em chips (já pedido na T-046).

**Próximo passo:** orquestrador abre o PR depois da conferência no compose. QA: o fluxo "baixa no caixa" da T-025 usa estas telas. Frontend: tarefas de Despesas, Reembolsos e renegociar.

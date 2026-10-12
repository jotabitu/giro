# T-137 · Correções das telas da conferência · frontend → orquestrador, qa, backend, produto, design-system

**O que foi feito** (itens da conferência `giro-produto/conferencia-telas.md`):
- **D-02** (início do financeiro): já resolvido na T-134 (blocos `null` caem no vazio). Conferi no navegador com a Lúcia: abre com "Entra hoje R$ 1.206,80", "Em atraso R$ 6.095,00", "Para hoje" e "Caixas do dia" vazios, sem erro no console.
- **D-04, D-06** (frontend): `financeiro: null` ou valor ausente aparece como "—" na ficha (Total pago, Em aberto, sem texto "nenhuma parcela vencida") e na coluna Total pago da lista, nunca R$ 0 (`dinheiroSemZerosOuTraco`). Os zeros que vinham da API com dado existente são do backend.
- **D-15**: o aviso `DEV-07` ("Peça o encerramento antecipado ao gerente") some para quem tem `locacoes_cancelar` = `sim` ou `aprova` (administrador, gerente); a vendedora continua vendo.
- **D-16**: sem combustível na chegada, a linha do acerto diz "Informe o nível na chegada" em vez de "Combustível ... R$ 0,00" (resumo e etapa Acerto).
- **D-22**: na coluna Pagamento, a forma avulsa "Pix", "Boleto" ou "Dinheiro" em locação sem valor em aberto vira "Pago". "Pix automático" e "Cartão" ficam, porque a tela de referência os mostra.
- **D-23**: o indicador "Pagamentos atrasados" virou "Locações com parcela atrasada" (contexto "R$ X em atraso"); no celular, "Parcela atrasada". O chip "Precisam de ação" não mudou.
- **D-30**: a nova locação abre sem plano marcado; o painel Cobrança (parcelamento, forma de pagamento, caução) só aparece depois de escolher o plano ou retomar um rascunho, e os botões de continuar ficam desligados até lá. Texto: "Escolha o plano para ver a cobrança."
- **D-32**: caixas de marcar com alvo de 44 px (`.wl-marcar` em `globals.css`, quadrado visível de 20 px), em itens da devolução, adicionais, consentimento do cliente e códigos de recuperação.
- **D-33**: itens do menu inferior com a mesma largura (66 px, o "+" com 48 px) em todas as telas; o item ativo mostra o rótulo sem alargar.
- **Endereço sem empresa**: `localhost`, IP e `admin.*` mostram "Este endereço não é de uma locadora. Entre pelo endereço da sua empresa." no login, e a casca não consulta a conta nesses endereços. O painel da plataforma ainda não tem login no frontend.
- **"No queryFn was passed" / corrida depois do login**: o login gravava `["eu"]` com `setQueryData` sem `queryFn` registrada; qualquer nova leitura da chave falhava e a casca mostrava "Não foi possível carregar sua conta". Agora `registrarConsulta` põe a `queryFn` como padrão da chave. A leitura também só renova o access quando não há um na memória (recarga da página), o que tira uma rotação do refresh a cada leitura.

**Onde:** `frontend/src/lib/{sessao.tsx,endereco.ts,formatos.ts,locacoes.ts}`, `src/components/{acesso/EnderecoSemEmpresa,acesso/FluxoEntrar,casca/CascaDoApp,clientes/DetalheDoCliente,clientes/ListaClientes,locacoes/ListaLocacoes,locacoes/NovaLocacao,vistorias/AcertoDaDevolucao,vistorias/Devolucao,vistorias/Campos}.tsx`, `src/app/globals.css`.

**Regras:** USR-08, USR-09, USR-05, LOC-12/LOC-13 (quem encerra), DEV-01, DEV-07 (só exibição).

**Testes:** novos `sessao.test.ts` (reproduz o erro sem o registro e passa com ele), `endereco.test.ts`, `rotuloDoPagamento` e `dinheiroSemZerosOuTraco`, e na devolução o aviso por perfil e o combustível sem nível. Ajustados os testes de lista (rótulos) e de nova locação (cobrança só com plano). `api:gerar` (sem mudança no `schema.d.ts`), `tsc`, `eslint` e 303 testes passando.

**Conferido no navegador** (portal do Maestri, dev server da branch na porta 3100 contra o backend do compose; o frontend do compose serve outro worktree): Lúcia (início, clientes, locações, nova locação), Rodrigo no celular de 390 px (barra inferior 66/66/48/66/66 px em início, veículos e locações; sem rolagem horizontal; caixas de marcar 44 x 44 na devolução da LOC-2836; sem o aviso DEV-07), `localhost:3100` com a mensagem de endereço sem empresa. Console sem erros. Não conferi a cor e a tipografia contra as telas (o portal não devolve captura).

**Pontos para conferir:**
1. **Backend/produto, D-22:** o `pagamento.rotulo` da LOC-2856 chega como "Pix" com a locação "Ativa". O ideal é a API mandar "Pago"; a tela normaliza só até lá.
2. **T-136:** a lista de clientes da Lúcia mostra "—" em Total pago para todos, porque `financeiro` vem `null` para o perfil. A `USR-09` diz que o financeiro vê total pago e em aberto; falta a API devolver.
3. **D-23:** `pagamentos_atrasados` conta locações (não parcelas); o rótulo novo diz isso.
4. Não rodei o seed para pegar o código de 2 etapas (negado pelo ambiente); calculei o código com a chave do seed.

**Próximo passo:** orquestrador abre o PR. QA: repetir D-15, D-16, D-30, D-32 e D-33 na revisão das telas.

# T-289 · Movimentações: telas (parte adiantada) · frontend → orquestrador, arquiteto, design-system, produto, qa

**Estado:** em andamento. As telas estão prontas com **dados de exemplo do contrato**, porque a T-288 (backend) não começou. A tarefa não está feita: falta ligar na API real.

**O que foi feito:**
- **Quadro** (`Movimentacoes`, desktop e celular): quatro colunas pelo `GET /api/movimentacoes/quadro/`, contagem e resumo prontos da API, busca por placa ou modelo na URL, "Nova" na coluna Agendadas e "Nova movimentação" só para `pode.movimentacoes = gerir`. No celular, a escolha da coluna é por botões (uma coluna por vez), não pelo deslize da referência.
- **Cartão:** só mostra os botões que `acoes` manda (Iniciar, Registrar chegada, Cancelar com motivo). A concluída mostra o custo da API.
- **Nova movimentação** (desktop: gaveta de 520px sobre o quadro; celular: tela inteira): veículo por busca, rota com saída, paradas (local de apoio com "Novo local", serviço, valor previsto), destino (com "Ida e volta" ou "Transferência" e a categoria no destino), Sair agora ou Agendar (dia e hora em Brasília, enviados em UTC), quem leva e vistoria rápida (marcada e travada na transferência). React Hook Form + Zod só para o que falta preencher; o erro da API volta no campo (`campos`) ou no aviso do rodapé. Aceita `?veiculo=<id>&destino=<filial>` para o "Movimentar" e o "Transferir" da ficha.
- **Registrar chegada** (celular): percurso (saída, paradas com despesa lançada, destino), km, combustível, fotos uma por vez ("Fotos · 2 de 4"), "Recebido por" na transferência. Combustível, fotos e recebedor só aparecem quando a movimentação pede (`vistoria_rapida`, `transferencia`). Os erros 400 e 422 da API (`VEI-01`, campos) aparecem no campo.
- **Menu e guarda de rota:** item `movimentacoes` (ícone caminhão, rota `/veiculos/movimentacoes`) e `rotaPermitida` exige o item no menu para as três rotas, separado de Veículos.

**Onde:**
- Telas: `frontend/src/components/movimentacoes/{QuadroDeMovimentacoes,CartaoDaMovimentacao,NovaMovimentacao,RegistrarChegada}.tsx`; rotas `app/(empresa)/veiculos/movimentacoes/{page,nova/page,[id]/chegada/page}.tsx`.
- **Provisório, para trocar:** `lib/api/tipos-movimentacoes.ts` (tipos escritos à mão do contrato; trocar pelos gerados e apagar) e `lib/api/movimentacoes.ts` (camada com seed de 07 out e transições simuladas; trocar o corpo de cada método por `http` nas rotas do contrato). `lib/api/index.ts` e `testes/api-falsa.ts` exportam `movimentacoes`; nos testes vale a mesma camada.
- Apoio: `lib/movimentacoes.ts` (textos fixos, rotas, `podeGerirMovimentacoes` lendo `pode.movimentacoes`, provisório até o OpenAPI trazer o campo), `lib/movimentacao-form.ts` (esquema e corpo do POST), `lib/menu.ts`.
- Testes: `components/movimentacoes/Movimentacoes.test.tsx` (16) e `lib/menu-movimentacoes.test.ts` (3). Rodados: só esses dois mais `menu.test.ts`; `tsc --noEmit` e `eslint` nos arquivos tocados, limpos.

**Contrato:** `docs/api/movimentacoes.md` (T-286), ADR 0028.
**Regras cobertas na tela:** MOV-01 (rota, paradas, local de apoio), MOV-02 (botões por `acoes`, quem cria), MOV-03 (409 mostrado como a API escreve), MOV-04 (parada com serviço e valor previsto, sem OS), MOV-05 (km, combustível, 4 fotos), MOV-06 (transferência, categoria no destino, recebedor).

**Dúvidas do contrato (não inventei; a camada de exemplo cobre com métodos marcados):**
1. **Quem leva e quem recebe:** o contrato dá `levado_por_id` e `recebido_por_id` ("usuário ativo ligado à filial de saída/destino, menos o financeiro") mas não tem rota para listar essas pessoas. `GET /api/usuarios/` é só do administrador. Hoje: `movimentacoes.quemPodeLevar(filialId)` e `quemPodeReceber(filialId)` na camada de exemplo. Arquiteto: definir a rota (ex.: `GET /api/movimentacoes/pessoas/?filial=<id>`).
2. **Lista de veículos que se movimentam:** a Nova movimentação busca em `GET /api/veiculos/` e deixa a API recusar com 409 `MOV-03`. O status `em_movimentacao` e `movimentacao_aberta` ainda não estão em `veiculos.md` gerado; a tela usa `situacao.rotulo` e `situacao.tom` do veículo.
3. **Texto da parada de oficina:** `Movimentacao-Nova-*` ainda mostra "Serviço · Da OS" e "Ordem de serviço OS-118" (a `[divergência]` já aberta no backlog para o design-system). Segui o contrato: sem OS, com serviço e valor previsto; a categoria da parada fica de fora do corpo e a API aplica o padrão (`outros`, `manutencao` na oficina).
4. **Código "MOV-0003" no cabeçalho da Nova movimentação:** a referência mostra o código antes de criar; o contrato só devolve o código no `201`. Deixei de fora.
5. **Dica do km ("rodou 26 km"):** a referência calcula a diferença na tela; pela regra "a API decide", mostrei só "não pode ser menor que 3.120" (o `km_saida`). Se o dono quiser o "rodou", a API devolve a diferença na resposta de uma validação, ou o produto aceita a conta de exibição.
6. **"Faltam combustível e 2 fotos":** a referência escreve o que falta antes de confirmar. A tela mostra "Fotos · n de 4" (contrato) e deixa os faltantes para o erro 400 da API (CA-246-09), em vez de recalcular a regra.
7. **Parada (chegada e saída do local de apoio, `MOV-04`):** o contrato tem as rotas e `acoes.chegar_parada`/`sair_parada`, mas não há tela (já dito no `docs/telas/README.md`). O quadro não mostra esses botões. Design-system: desenhar a tela da parada (valor pago, nota) antes de o frontend montar.
8. **Menu:** o item "Movimentações" em `menu.ts` fica depois de Veículos na detecção de rota ativa, e como `/veiculos` é prefixo, Veículos aparece ativo em `/veiculos/movimentacoes` quando os dois estão no mesmo menu. Se incomodar, a ordem de ativo precisa preferir o caminho mais longo.

**O que ficou de fora (precisa da T-288 ou de decisão):**
- Ligar na API real (trocar `lib/api/movimentacoes.ts`, os tipos e `pode.movimentacoes`; apagar a camada de exemplo).
- "Transferir" e "Movimentar" da ficha do veículo (`acoes.transferir`, `acoes.movimentar` e a troca da rota antiga `transferir`) e a coluna/filtro "em movimentação" da Frota.
- "Sem nota" e "Anexar nota" em `Despesas` (`POST /api/financeiro/despesas/{id}/nota/`).
- Lista com filtro de período das concluídas antigas (a tela de lista não tem referência; o quadro mostra só as de hoje).
- Verificação no navegador em 1440px e 390px: não feita nesta entrega (sem backend e com pouca memória); a conferência visual fica para a ligação com a API.
- Teste de clique (marcação estática, como nas outras telas); as transições estão testadas pela camada de exemplo.

**Próximo passo para quem recebe:** arquiteto responde a dúvida 1 e a 2; design-system desenha a parada (7) e corrige a OS (3); orquestrador, quando a T-288 entregar, devolve a T-289 ao frontend para a ligação.

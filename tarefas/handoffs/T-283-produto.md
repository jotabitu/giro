# T-283 · Regras das decisões do dono de 16 out · produto → orquestrador, arquiteto, backend, frontend, qa

**O que foi feito:** as quatro respostas do dono de 16 out entraram nas regras, na tabela "Decisões de 16 out 2026" e nos critérios, e os três pontos saíram de "Pontos em aberto". A branch `t-283-decisoes-16-out` sai da `origin/main` (20a41d6).

1. **Movimentações no MVP (opção A, contra a recomendação B do produto).** A seção "Movimentações de veículos" deixou de ser fase 2, e o status `em_movimentacao` também: o veículo passa a ter 9 estados.
   - Ficam pelo padrão do produto, marcadas "a conferir pelo dono" no texto:
     - a despesa sem nota;
     - a categoria padrão ("outros"; "manutenção" para oficina);
     - o veículo nunca guardado fora de uma filial.
   - Duas leituras novas, também marcadas: o documento que vence durante a movimentação não muda o status no dia, e a chegada decide (`MOV-05`, `AUT-06`); e o **local de apoio** é da empresa. Administrador e gerente o cadastram na própria parada ("Novo local": nome e tipo), com nome único. Ele não se apaga: só se inativa. As telas não têm esse cadastro.
   - A ligação da parada com a OS (`MAN-05`) espera as ordens de serviço (fase 2). No MVP, a parada de oficina gera despesa como as outras.
   - "Transferir" na ficha abre a Nova movimentação já no MVP (`MOV-06`).
2. **Veículos no menu do vendedor (A):** entre Locações e Clientes, só leitura (`USR-05`, `USR-09`).
3. **Financeiro vê Veículos:** só leitura, no menu do perfil, entre Caixa e bancos e Comissões, com o rendimento e o custo (`VEI-05`). A tabela de perfis ganhou a linha "Consultar veículos". Pus o item no menu do perfil, e não no menu completo, para não repetir o problema do vendedor. A posição é leitura do produto.
4. **Pix Automático nas parcelas da locação: fase 2.** `AUT-04` e `LOC-05`: no MVP, a parcela segue boleto e Pix comum pela régua (`AUT-03`). O padrão da T-261 fica de base para a fase 2. O Pix Automático da assinatura (`PLT-13`) não muda.

**Onde:**
- `docs/regras-de-negocio.md`: entidades (Movimentação, Local de apoio), tabela de perfis, `USR-05`, `USR-09`, Veículos, Movimentações, `LOC-05`, `AUT-04`, Decisões de 16 out, Pontos em aberto. Cada mudança tem a nota "Mudanças em 16 out 2026 (T-283)".
- `docs/qa/criterios/T-246.md`: fase MVP; o CA-246-07 reescrito (oficina sem OS no MVP); os novos CA-246-14 a 16 (sem nota, local de apoio, Transferir pela ficha).
- `docs/qa/criterios/T-283.md` (novo): CA-283-01 a 06, com os menus da Bruna e da Lúcia, a leitura sem ações e a parcela sem Pix Automático.
- `docs/qa/criterios/T-023.md`: CA-023-24 com Veículos no menu da Lúcia.
- `docs/qa/criterios/T-029.md`: CA-029-09 marcado fase 2.
- `docs/plano.md`: 9 estados.
- `tarefas/backlog.md`: a T-283 saiu, e a `[decisão]` do Pix Automático foi respondida.

**Regras cobertas:** MOV-01 a MOV-06, USR-05, USR-09, VEI-05, LOC-05, AUT-03, AUT-04, tabela de perfis.

**Para o arquiteto, no contrato das Movimentações (quando o orquestrador numerar):**
- **App e modelo.** No app `veiculos` ou num app novo, três modelos:
  - `Movimentacao`: código `MOV-` sequencial por empresa; filial de saída; veículo; destino (sempre uma filial); quem leva; agendada para; vistoria rápida obrigatória ou não; km de chegada; "Recebido por"; categoria no destino, quando é transferência; status.
  - `ParadaMovimentacao`: em ordem; local; serviço; valor previsto e valor confirmado; categoria; nota; despesa gerada.
  - `LocalApoio`: da empresa; nome único; tipo `lava_jato`, `oficina`, `despachante` ou `outro`; `ativo`.
  - A OS na parada fica de fora, ou como campo que nasce vazio até a fase 2.
- **Máquina de estados.** Estados `agendada`, `em_transito`, `no_local`, `concluida` e `cancelada`, com as transições da seção. Cancelar só a `agendada`. "Sair agora" já nasce `em_transito`. Evento de auditoria (operação) em cada mudança.
- **Status do veículo.** `em_movimentacao` entra na máquina do veículo com três transições: `disponivel` → `em_movimentacao` ao iniciar; `em_movimentacao` → `disponivel` ou `indisponivel` na chegada.
  - Os veículos `indisponivel`, `em_manutencao` e `a_venda` mantêm o status. A Frota precisa de um sinal "em movimentação" para eles.
  - Iniciar responde 409 se o veículo foi reservado ou alugado depois do agendamento.
  - Uma só movimentação não concluída por veículo, com trava de concorrência contra criar duas e contra reservar o veículo enquanto ele é iniciado.
- **Reflexos fora do app.** Frota (filtro e contadores), Nova locação e reserva sem o `em_movimentacao`, ocupação (`VEI-06`: conta dia na frota, não alugado), painel e contadores do menu.
- **Despesa pela porta do financeiro.** Na saída da parada com valor acima de zero, a despesa nasce na filial de saída: ligada ao veículo, vencendo no dia, com a descrição "MOV-0042 · serviço · local". Ela segue a `FIN-05` (até R$ 500 `a_pagar`, acima `aguardando_aprovacao` com o pedido da `APR-03`).
  - Sem nota, a despesa nasce marcada "sem nota", e a nota pode ser anexada depois no detalhe.
  - A exceção à nota obrigatória da `FIN-06` vale só para essa origem. O lançamento manual pela tela `Despesas` continua exigindo a nota.
- **Chegada.** O km não diminui (`VEI-01`) e grava uma `LeituraKm`. A vistoria rápida tem combustível e 4 fotos; é obrigatória na transferência.
  - Na transferência, a `TransferenciaVeiculo` é gravada na chegada, com a categoria pedida na criação (`VEI-04`).
  - O veículo chega `indisponivel` se o CRLV ou o seguro venceu no caminho (`VEI-03`).
  - Para a `AUT-06` (`MOV-05`, leitura do produto marcada): o veículo `em_movimentacao` com o documento vencendo não muda de status no dia; a tarefa urgente vai aos gerentes, como no `alugado`, e a chegada decide.
- **Permissões.**
  - Criar, agendar, iniciar, cancelar e cadastrar local de apoio: administrador, e gerente com acesso à filial de saída. Inativar local: administrador.
  - Quem leva é qualquer usuário ativo da filial de saída, que registra as chegadas.
  - "Recebido por" é um usuário da filial de destino.
  - Novas chaves em `pode` (`movimentacoes_criar` e a de registrar chegada para quem leva) e itens novos de menu (Movimentações para administrador e gerente) em `contas.md`.
- **Ficha do veículo.** "Transferir" passa a abrir a Nova movimentação. Decidir se `POST /api/veiculos/{id}/transferir/` continua como rota interna ou sai do contrato; a `VEI-04` continua valendo.
- **Telas.** `Movimentacoes`, `Movimentacao-Nova`, `Movimentacao-Chegada-Mobile`. As divergências delas (Pátio Maraponga como origem, destino "Filial ou local") estão na `[divergência]` respondida do backlog.

**Para o arquiteto e o backend, no menu (`contas.md`, `auth/eu`):**
- Hoje `pode.veiculos` é `nao` para o vendedor e o financeiro (`backend/apps/contas/selectors.py`, linha 39), por isso o item não aparece para eles. É preciso um valor de leitura (por exemplo `ver`), e as ações de escrita continuam recusadas.
- `menu_inicio` do vendedor: `inicio`, Operação `locacoes`, `veiculos`, `clientes`.
- `menu_inicio` do financeiro: `inicio`, `receber`, `contas_a_pagar`, `caixa_e_bancos`, `veiculos`, `comissoes`.
- Na barra do celular, `veiculos` aparece para os dois.

**Para o backend, no Pix Automático:** no MVP, sem a tarefa `aut_04_cobranca_recorrente` agendada e sem autorização na locação. O método do provedor (`asaas.py`, T-029) pode ficar.

**O que ficou de fora:**
- A agenda do vistoriador com as movimentações, os avisos de movimentação atrasada e a troca do destino depois de iniciada (como na T-246).
- A parada com OS (fase 2).
- A tela do cadastro do local de apoio: no MVP, ele é criado na parada, e a lista para inativar fica com o design-system, se o dono confirmar a leitura.
- O Pix Automático da locação (fase 2).
- A conferência do dono nas leituras marcadas.

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar o contrato das Movimentações (arquiteto, depois backend e frontend), o menu do vendedor e do financeiro (backend em `auth/eu`, frontend) e, se quiser, a tela de locais de apoio (design-system). Levar ao dono as leituras marcadas "a conferir pelo dono".
- **QA:** CA-246-01 a 16 e CA-283-01 a 06. Os locais de apoio e a Filial Caucaia são criados no teste, não no seed.

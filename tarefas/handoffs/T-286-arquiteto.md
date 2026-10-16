# T-286 · Contrato das Movimentações · arquiteto → orquestrador, backend, frontend, produto, design-system

**O que foi feito:** contrato e modelo das Movimentações, pelo handoff do produto na T-283, e a ADR do app.
**Onde:**
- `docs/api/movimentacoes.md` (novo).
- `docs/decisoes/0028-app-movimentacoes.md` (nova) e o índice das ADRs.
- `docs/decisoes/modelo-de-dados.md`: itens 26 e 27, status do veículo, origem da despesa e restrições.
- Reflexos em `docs/api/veiculos.md`, `financeiro.md` e `contas.md`.
- Seção da T-286 no backlog.
- A branch tem a `t-275-ficha-veiculo-api` mesclada: o bloco `movimentacoes` e `acoes.movimentar` da ficha agora apontam para o app.

**Decisões (ADR 0028):**
- **App novo `movimentacoes`, no nível 11, ao lado de `vistorias`.** Dentro de `veiculos` (nível 6), ele não alcançaria o financeiro nem as locações.
- **Vistoria rápida da chegada no próprio app.** Combustível com o enum da vistoria e 4 fotos com as validações de `comum.arquivos`. Não vira `vistorias.Vistoria`, que é da locação.
- **Uma movimentação aberta por veículo.** Índice único parcial no banco. Criar e iniciar travam a linha do veículo, e `locacoes.services.confirmar` passa a travar a mesma linha. O veículo `disponivel` com locação `aguardando_retirada` conta como reservado (409 `MOV-03`).
- **Frota e ficha pelo registro de leituras (ADR 0015).** Bloco `movimentacao_aberta` (lista e detalhe), bloco `movimentacoes` (detalhe) e o filtro `?em_movimentacao=true`.
- **Despesa da parada pelo `lancar_despesa`.** Com a origem nova `movimentacao` e a nota opcional. A despesa ganha `sem_nota` e `origem`, e a nota se anexa depois por `POST /api/financeiro/despesas/{id}/nota/`. A rota de lançamento continua exigindo a nota.
- **Transferência na chegada por `veiculos.services.transferir`.** Com a origem `movimentacao` e sem exigir `disponivel`. A rota `POST /api/veiculos/{id}/transferir/` sai do contrato quando o frontend trocar o botão.

**Contrato:**
- Quadro, lista, detalhe, criar (com "Sair agora"), editar a agendada, iniciar e cancelar.
- Chegada e saída da parada; a saída com valor gera a despesa.
- Fotos da chegada uma por vez, por causa dos 12 MB do proxy; depois, confirmar a chegada.
- Locais de apoio: listar, criar com nome único, inativar e reativar.
- `pode.movimentacoes` (`gerir`, `levar`, `nao`) e o item de menu.
- Tom `info` e rótulo "Em movimentação" no veículo.

**Regras cobertas:** MOV-01 a MOV-06, VEI-01 a VEI-04, VEI-06, FIN-05, FIN-06, APR-03, AUD-05, USR-07. Critérios CA-246-01 a 16 citados no contrato.

**O que ficou de fora:**
- A OS na parada (fase 2; o modelo deixa o campo para depois).
- A agenda do vistoriador e os avisos de movimentação atrasada.
- A troca de destino depois de iniciar.
- A tela de lista dos locais de apoio.
- Duas [decisão] para o produto: como quem leva chega ao "Registrar chegada", e a janela da coluna Concluídas.
- Uma [divergência] para o design-system: a OS na Nova movimentação.

**Próximo passo para quem recebe:**
- Orquestrador: numera o backend e o frontend pelo "Pronto quando" da seção da T-286. A T-287 (menu do vendedor e do financeiro) é à parte.
- Backend: começa pelo app e por `veiculos` (status, trava, blocos).

# T-246 · Movimentações de veículos (regras) · produto → orquestrador, arquiteto, design-system, qa

**O que foi feito:** escrevi as regras das movimentações a partir das telas do dono (T-238). A branch `t-246-regras-movimentacoes` está empilhada sobre a `origin/t-238-telas-novas` (PR #242).

- `docs/regras-de-negocio.md`:
  - **Seção nova "Movimentações de veículos"**, marcada fase 2:
    - código `MOV-0043` por empresa, como nas telas; o `MT-` do pedido se confundiria com a Yamaha MT-03;
    - estados `agendada`, `em_transito`, `no_local`, `concluida`, `cancelada`; depois de iniciada, a movimentação não se cancela;
    - `MOV-01`, rota: a saída é a filial do veículo; as paradas ficam em locais de apoio cadastrados (lava-jato, oficina, despachante, outro); o destino é sempre uma filial;
    - `MOV-02`, quem: administrador e gerente criam e iniciam; quem leva é qualquer usuário da filial de saída e registra as chegadas; na transferência, "Recebido por" é da filial de destino;
    - `MOV-03`, quais veículos: `disponivel`, `indisponivel`, `em_manutencao` ou `a_venda`, nunca `alugado` ou `reservado`; uma movimentação aberta por veículo; o `disponivel` vai para `em_movimentacao` (status novo), e os outros mantêm o status; a agendada não muda o status, e Iniciar é recusado se o veículo foi reservado; na ocupação, conta como dia na frota;
    - `MOV-04`, paradas: o valor confirmado gera despesa ligada ao veículo, pela `FIN-05` e pela `APR-03`; a parada de oficina que cita a OS não gera despesa, porque o custo é o da OS (`MAN-05`);
    - `MOV-05`, chegada: km obrigatório (`VEI-01`, `VEI-02`); a vistoria rápida (combustível e 4 fotos) é obrigatória na transferência e opcional na volta; o veículo chega `indisponivel` se um documento venceu no caminho;
    - `MOV-06`, transferência: a `VEI-04` acontece na chegada, com a categoria no destino pedida na criação.
  - Veículos: o status `em_movimentacao` e três transições, marcados fase 2. A Movimentação entra na tabela de entidades, e a tabela de perfis ganha uma linha.
  - **Pontos em aberto:** "Fase das movimentações". Opções: A, MVP; B, fase 2. Padrão: **B**.
- `docs/qa/criterios/T-246.md`: CA-246-01 a 13, com SAK-1D39, PMZ-3E17, QXA-4B21 e RHT-9F02 do seed e a lavagem de R$ 35,00. Despesas de outubro passam a R$ 7.101,70, e a despesa por veículo a R$ 82,58.
- `tarefas/backlog.md`: a `[divergência]` das telas respondida, com o que fica para o design-system, e o estado da T-246.

**MVP ou fase 2:** recomendo a **fase 2**, e o dono confirma (ponto em aberto). Ela traz:
- um status novo do veículo, que mexe na Frota, na Nova locação, na reserva e na ocupação;
- um cadastro novo, o dos locais de apoio;
- despesa gerada fora da tela `Despesas`;
- a ligação com a OS, que já é da fase 2.

O MVP já cobre o essencial: mudar de filial (`VEI-04`) e lançar o custo (`Despesas`).

**Regras cobertas:** MOV-01 a MOV-06, VEI-01 a VEI-04, VEI-06, FIN-05, FIN-06, APR-03, MAN-05.

**Leituras do produto, para o dono conferir:**
- Sem a nota, a parada gera a despesa mesmo assim, marcada "sem nota". A nota obrigatória da `FIN-06` vale para o lançamento pela tela `Despesas`.
- Categoria da despesa: "outros", por padrão; "manutenção" para oficina.
- O veículo nunca fica guardado fora de uma filial. Por isso o "Pátio Maraponga" da tela não é origem, e o destino é sempre uma filial.

**O que ficou de fora:**
- o contrato e o modelo (arquiteto), quando o orquestrador numerar;
- a agenda do vistoriador com as movimentações;
- avisos de movimentação atrasada;
- trocar o destino depois de iniciada (hoje não se troca).

**Para quem recebe:**
- **Arquiteto (quando numerado):**
  - app (`veiculos` ou um app novo), modelo da Movimentação, das paradas e do local de apoio;
  - o status novo na máquina de estados do veículo;
  - a despesa gerada pela porta do financeiro;
  - a `TransferenciaVeiculo` gravada na chegada;
  - a regra de uma movimentação aberta por veículo, com trava de concorrência.
- **Design-system:** os itens da `[divergência]` respondida (contadores, placas, origem em pátio, destino "Filial ou local", OS-0193, RHT-9F02 como Biz).
- **QA:** os locais de apoio e a Filial Caucaia são criados no teste, não no seed.

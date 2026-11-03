# T-410 · Locação confirmada reserva o veículo e só cobra depois da retirada · produto → arquiteto, backend, frontend, qa

**O que foi feito:** as três decisões do dono (29 e 30 out 2026, nota "Bug #1") viraram regra, com nota de mudança em cada seção, e os critérios de aceite.

1. **Reserva na confirmação.** Tabela de transições do veículo: `disponivel` → `reservado` na confirmação da locação (`rascunho` → `aguardando_retirada`), com início futuro, hoje ou passado. O `reservado` é o veículo de toda locação `aguardando_retirada`, e a Frota e a ficha mostram "Reservado na LOC-x". `reservado` → `disponivel` ganhou o cancelamento automático. A `MOV-03` deixou de tratar o `disponivel` com locação aguardando como reservado (o comportamento não muda).
2. **Nada vence antes da retirada** (`LOC-05`, `FIN-03`). Enquanto a locação está `aguardando_retirada`, as contas dela ficam `aberta`: sem `vence_hoje`, `atrasada`, `pagamento_atrasado`, régua, bloqueio ou análise do cliente, e fora de "Vence hoje" e "Em atraso" no `Receber`. A 1ª parcela e a caução pagas na retirada não têm multa nem juros (o dia da retirada entra na fórmula da `FIN-03`). O vencimento gravado e o fim previsto **não mudam** com a retirada.
3. **Cancelamento automático** (`LOC-12`, `AUT-17` nova). A locação não retirada até o 3º dia depois da data de início (início 05 nov → último dia 08 nov) cai às 00:10 do dia seguinte, sem `APR-02`, como o cancelamento antes da retirada (sem multa, contas abertas canceladas, o que foi pago é devolvido, contrato `cancelado`, vistoria em rascunho descartada, veículo `disponivel`). Aviso aos gerentes da filial (`FIL-02`) às 08:00 do último dia, no sino, no push e por e-mail. Confirmar com o prazo já passado é recusado (409 `inicio_vencido`).

**Onde:** `docs/regras-de-negocio.md` (Veículos, Movimentações, Locação, Financeiro, Automações, Dados de referência, "Decisões de 29 e 30 out 2026", Pontos em aberto); `docs/qa/criterios/T-410.md` (CA-410-01 a 23).

**Regras cobertas:** tabela de transições do veículo, `LOC-05`, `LOC-12`, `FIN-03`, `AUT-17`, `MOV-03`.

**Leitura do produto sobre o "Pronto quando":** o backlog diz "gera o calendário de parcelas a partir da ativação". Li a decisão do dono ("as parcelas só começam a vencer na retirada; antes dela, nada fica atrasado") como **nada vence antes da retirada**, sem mudar as datas: as contas continuam nascendo na confirmação, com o calendário contado da data de início. Mover o calendário para a retirada mudaria o fim previsto e a carteira de outubro do seed (a LOC-2836 começa em 30 set e é retirada em 01 out). Ficou como ponto em aberto 1, com o padrão A.

**Pontos em aberto para o dono** (padrão A nos três, valendo até a resposta):
1. Período da locação retirada depois do início: A conta da data de início; B anda para a retirada.
2. Contagem dos 3 dias: A início + 3 (Código Civil, art. 132); B o início conta como o 1º dia. Junto, a recusa `inicio_vencido`.
3. Aviso ao cliente: A só o gerente; B o cliente também (modelo novo do WhatsApp, com aprovação da Meta).

**Próximo passo para quem recebe:**
- **Arquiteto:** contrato de `docs/api/locacoes.md` e `veiculos.md` (409 `inicio_vencido`, o rótulo "Reservado na LOC-x" pela API, a notificação nova e a `AUT-17`).
- **Backend:** reservar na confirmação para qualquer início (`apps/locacoes/services.py`, o `if data_local(...) > relogio.hoje()` de hoje); tirar as contas de locação `aguardando_retirada` do `atrasada` e do `vence_hoje` (`apps/financeiro/selectors.py`, o `Q(status=ABERTA, vencimento__lt=hoje)`), da régua, do bloqueio e da análise; multa e juros com o dia da retirada; `AUT-17` (00:10 e 08:00, com recuperação da execução perdida); comando ou seed que acerte o ambiente de desenvolvimento (CA-410-23). Testes com o código no nome (`test_loc_05_...`, `test_loc_12_...`).
- **Seed:** em 07 out, o SAK-1D39 (LOC-2856) passa a `reservado`. As reservas do seed com retirada em novembro (`seed/carteira.py`, `RETIRADAS_DAS_RESERVAS`) e a LOC-2856 (início 07 out) caem pela `AUT-17` se o relógio passar do prazo; com o relógio em 07 out, nada muda. O comentário de `seed/frota.py` ("SAK1D39 fica alugado") não bate com a LOC-2856 `aguardando_retirada`: conferir.
- **QA:** os critérios da T-283 que usam o SAK-1D39 como `disponivel` trocam de veículo (CA-410-06). Nenhum número de valor do seed muda (LOC-2836 R$ 958,00, caixa de 07 out R$ 1.111,90, carteira de outubro).
- **Frontend:** "Reservado na LOC-x" na Frota e na ficha, pelo texto da API; nada de calcular atraso na tela.

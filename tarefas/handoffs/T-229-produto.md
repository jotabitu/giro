# T-229 · Regras de cancelar e pausar (casos da T-194) · produto → orquestrador, arquiteto, segurança, qa, design-system

**O que foi feito:** escrevi nas regras os cinco casos que a `PLT-06` não cobria (T-194, `docs/api/cancelamento.md`) e confirmei a recusa do Essencial para quem só vende (T-223). O dono aprovou a opção A nos seis em 15 out 2026. Junto, resolvi os três pontos do arquiteto na T-201 (PR #227). Branch `t-229-regras-cancelar-pausar`, a partir da `origin/main` com o #223 e o #224.

- `docs/regras-de-negocio.md`:
  - `PLT-06`:
    - **Em teste com a 1ª fatura paga:** segue a `ativa`, com acesso até o fim do período da 1ª fatura e sem estorno; o desfazer vale até lá.
    - **Desistir da pausa:** pela tela, até o último dia do período pago; a fatura que a pausa cancelou nasce de novo.
    - **Diferença de upgrade em aberto:** continua devida durante a pausa, sem a empresa virar `inadimplente`; ela volta `inadimplente` se a fatura ainda estiver atrasada.
    - **Cancelamento marcado:** mudar de plano e pausar são recusados até desfazer, e o downgrade agendado continua.
  - `PLT-04`: aponta para a recusa.
  - `AUD-08`: o que fica no painel da plataforma depois do apagamento.
  - Dados de referência: caso (d) do cancelamento e desistência da pausa.
  - Notas de mudança, tabela em "Decisões de 15 out 2026" e dois pontos em aberto: o prazo de guarda das faturas (dono e contador) e o fornecedor no pedido de despesa (padrão A).
- `docs/qa/criterios/assinatura.md`: CA-ASS-54 a 58.
- `docs/qa/criterios/aprovacoes.md`: CA-APR-10 com "O limite de Bruna é 5%."
- `tarefas/backlog.md`:
  - a `[decisão]` da T-194 marcada como resolvida;
  - seção da T-229, com uma proposta sem número para o arquiteto;
  - seção da T-230 para a segurança;
  - o item da T-204 com 1 evento em configurações.
- `tarefas/feito.md`: linha da T-229, PR a abrir.

**Regras cobertas:** PLT-06, PLT-04, AUD-08, PLT-12, APR-03, FIN-05, AUD-02.

**Para quem recebe:**
- **Arquiteto:** em `cancelamento.md`, tirar as marcas `[decisão]` dos 5 casos. O resto já bate com o contrato. Na T-201: o contrato já diz 1 evento em configurações e as células da despesa sem fornecedor nem forma (o padrão A que recomendei).
- **Segurança (T-230):** o MEI e o empresário individual, cujos nome e CPF ficam na razão social e no CNPJ depois do apagamento.
- **Qa:** CA-ASS-54 a 58 e CA-APR-10. A T-204 fica com 10 eventos, 1 em configurações.
- **Design-system:** se o dono confirmar o padrão A do fornecedor, a tela `Aprovacoes` perde "Fornecedor" e "15 out · boleto" no pedido de despesa.
- **Orquestrador:**
  - levar ao dono a `[decisão]` do fornecedor (padrão A em "Pontos em aberto");
  - o item da T-201 no backlog ainda diz "2 em `?categoria=configuracoes`". Não mexi para não dar conflito com o #227; corrigir para 1 ao fechá-lo.

**Próximo passo:** o orquestrador abre o PR e numera a proposta. Só documentos, sem teste para rodar.

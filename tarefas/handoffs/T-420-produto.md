# T-420 · Locação com intenção de compra · produto → arquiteto, design-system, backend, frontend, qa

**O que foi feito:** as decisões do dono de 29 e 30 out 2026 viraram a `LOC-16` e a `VEN-11`, com a transição nova do veículo, notas de mudança, dois pontos em aberto e os critérios.

1. **`LOC-16`:** tipo de locação `intencao_compra`. Plano de compra em `Precos` (categoria, periodicidade, número e valor das parcelas), congelado na locação; sem desconto e sem extras; modelo de contrato próprio, obrigatório para confirmar; parcelas antecipadas da `LOC-05`; caução da categoria abatida na última parcela (R$ 1.190,00 − R$ 300,00 = R$ 890,00; caução maior que a parcela devolve a sobra); custos com a locadora; sem renovação e sem troca; fim previsto sem devolução (nada de `devolucao_atrasada` pela data); atraso pela régua e encerramento pela locadora sem `APR-02`; encerramento antes do fim sem crédito, devolução ou multa.
2. **Quitação:** todas as parcelas pagas e nenhuma conta da locação aberta → `encerrada` sem vistoria nem acerto, caução usada, veículo `alugado` → `vendido` (transição nova), venda da `VEN-11`, tarefa da transferência para os gerentes da filial, fechada à mão.
3. **`VEN-11`:** venda `vendida` de R$ 0,00, "Quitação da LOC-x", sem contas, contrato de venda ou comissão, fora do funil, da conversão e da meta, sem cancelamento pela tela.

**Onde:** `docs/regras-de-negocio.md` (Veículos, Locação, Vendas, "Decisões de 29 e 30 out 2026", Pontos em aberto); `docs/qa/criterios/T-420.md` (CA-420-01 a 17); `[divergência]` do toggle da `Onboarding-Contrato` no backlog.

**Pontos em aberto para o dono** (padrão A, valendo até a resposta):
1. De onde vem o valor: A plano de compra em `Precos`; B tabela da categoria com o prazo escolhido.
2. Multa no encerramento antes do fim: A sem multa; B a da `LOC-12`.

**Leituras do produto (não vieram do dono):** quem cria e confirma é quem cria locação; sem desconto e sem extras; encerramento por atraso sem `APR-02`; a quitação espera as outras contas da locação; venda fora do funil e da comissão e sem cancelamento; sem contrato de compra e venda; estorno depois da quitação vira conta a receber.

**Próximo passo:**
- **Arquiteto:** ADR e contrato: `Locacao.tipo`, `PlanoCompra` (ou plano especial com tipo), o tipo do modelo de contrato, a quitação como serviço do domínio chamado pelo pagamento, a transição `alugado` → `vendido`, a venda ligada à locação (o app `vendas` ainda está vazio: decidir o mínimo para a `VEN-11` agora), a tarefa da transferência, o texto de andamento ("Parcela 5 de 24 · faltam 19 para a transferência").
- **Design-system:** tipo na Nova locação, planos de compra em `Precos`, andamento na ficha, rótulo em `Vendas`, e o toggle da `Onboarding-Contrato` (divergência).
- **Backend e frontend:** depois do contrato; testes `test_loc_16_...` e `test_ven_11_...`.
- **QA:** CA-420-01 a 17 (valores de teste, nenhum número do seed muda).

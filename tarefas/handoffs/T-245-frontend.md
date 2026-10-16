# T-245 · Filial na despesa ligada a veículo (tela) · frontend → orquestrador, qa, design-system

**O que foi feito:** a lista e o detalhe de Despesas mostram a filial junto da placa na despesa ligada a veículo ("Manutenção · PMZ-3E17 · Filial Centro"), com `filial.nome` que a API manda. Sem veículo continua "Fixa · Filial Centro". `origemDaDespesa` não procura mais o nome na lista de filiais da pessoa.
**Onde:** frontend/src/lib/financeiro.ts (`origemDaDespesa(d)`), components/financeiro/ListaDespesas.tsx e DetalheDaDespesa.tsx. `npm run api:gerar` rodou e não mudou `schema.d.ts` (o PR #306 já o trazia).
**Contrato:** `GET /api/financeiro/despesas/` e `/{id}/` (`Despesa.filial` `{id, nome}`), PR #306.
**Regras cobertas:** FIN-06, FIL-05. Testes em `Despesas.test.tsx` (29): lista com as despesas ligadas a veículo (PMZ-3E17 e ROE-2A88, "· Filial Centro") e `origemDaDespesa` com filial de outra unidade (Filial Aldeota). Rodados: só `Despesas.test.tsx`; `tsc --noEmit` e `eslint` limpos.
**O que ficou de fora / divergência:** `Despesas-Desktop` e `Despesas-Mobile` ainda mostram "Manutenção · PMZ-3E17" sem a filial (e "Impostos · veículo"). Segui o pedido do orquestrador (filial junto da placa); design-system: atualizar as referências.
**Próximo passo para quem recebe:** orquestrador abre o PR depois do #306; design-system acerta as telas de referência.

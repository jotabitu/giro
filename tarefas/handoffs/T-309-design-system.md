# T-309 · Filial na despesa ligada a veículo, nas referências · design-system → orquestrador

**O que foi feito:** em `Despesas-Desktop` (coluna Despesa) e `Despesas-Mobile` (lista "Últimas"), as despesas de manutenção ligadas a veículo passaram de "Manutenção · PMZ-3E17" e "Manutenção · QXA-4B21" para "categoria · placa · filial", como a tela real (`origemDaDespesa`, T-245): "Manutenção · PMZ-3E17 · Filial Centro" e "Manutenção · QXA-4B21 · Filial Centro". Os veículos são do seed, na Filial Centro.
**Onde:** `docs/telas/html/Despesas-Desktop.dc.html`, `docs/telas/html/Despesas-Mobile.dc.html`.
**Regras cobertas:** FIN-06, FIL-05.
**O que ficou de fora:** "Impostos · veículo" (sem placa, nas duas referências) não mudou: não aponta um veículo do seed, e a tela real mostraria a placa e a filial se houvesse veículo. Fica para o produto dizer qual é o veículo, se for um.
**Próximo passo para quem recebe:** nenhum.

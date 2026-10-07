# T-031 · Responder as dúvidas de regra da T-006 · produto → orquestrador, arquiteto

**O que foi feito:** conferi as cinco dúvidas `[decisão]` da T-006 contra as regras e as telas e escrevi uma recomendação para cada uma, com o padrão que vale até a aprovação. Nada foi marcado como decidido; quem aprova é o dono do produto.
**Onde:** `docs/regras-de-negocio.md`, "Pontos em aberto" → "Dúvidas do modelo de dados (T-006, 07 out 2026)"; nota em `tarefas/backlog.md`, seção Decisões.
**Recomendações:**
1. Estados não listados: aceitar a proposta do arquiteto. Só completa a lista de status, sem impacto de negócio. As telas `Admin-Usuarios` e `Conciliacao` já usam esses nomes. Convite vencido continua `convite_pendente`.
2. `VEN-07`: acrescentar `cancelada` (só a partir de `vendida`) e a transição do veículo `vendido` → `a_venda`. Falta o dono decidir quem cancela: A) gerente ou administrador (padrão) ou B) vendedor pede e gerente aprova.
3. Venda aberta: só `proposta`, `negociacao` e `aguardando_aprovacao`. Quando o veículo é vendido, os `interessado` dele vão para `perdida`.
4. `ROUND_HALF_UP` no centavo, arredondando uma vez por valor gravado; nas parcelas, a diferença vai para a última. Nenhum caso do seed muda.
5. Chassi único por empresa em todos os estados (`Onboarding-Importar` já recusa chassi repetido). Veículo recomprado numa troca reaproveita o cadastro, o que pede a transição `vendido` → `indisponivel`.
**Regras citadas:** VEN-05, VEN-07, FIN-09, VEI-01, IMP-02, USR-01, FIN-07, FIN-08, FIN-11, APR-04, PLT-07.
**O que ficou de fora:** não mexi nas tabelas de estados nem nas regras; isso entra depois da aprovação, com o registro da data.
**Próximo passo para quem recebe:** o orquestrador leva os itens 2 e 5 ao dono do produto. O arquiteto mantém o modelo de dados com o padrão; se a aprovação mudar algo, o produto avisa.

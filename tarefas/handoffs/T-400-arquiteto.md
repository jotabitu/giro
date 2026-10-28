# T-400 · Contrato do downgrade na fase 1 · arquiteto → orquestrador

**O que foi feito:** em `docs/api/assinatura.md`, no 422 `PLT-04` de "módulo que sai com algo aberto":
- **Fase 1:** a recusa confere só `despesas_aguardando_aprovacao` e `despesas_a_pagar`, pela decisão do dono de 25 out (T-356 e T-377). A recusa da fase 1 é a do exemplo da Moto Rápida (CA-ASS-15).
- **Fase 2:** os grupos `ordens_servico`, `vendas` e `comissoes` continuam no contrato, marcados como fase 2. Eles entram com os módulos. O exemplo com OS (CA-ASS-24) ficou, também marcado como fase 2.

Nada foi apagado e nenhum código mudou.

**Regras:** `PLT-04`, `PLT-12` (nenhuma muda).
**Próximo passo:** o orquestrador confere e abre o PR. Branch `t-400-contrato-downgrade`.

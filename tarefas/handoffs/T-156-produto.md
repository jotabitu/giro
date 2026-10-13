# T-156 · Custo e rendimento do veículo fora da ficha do vendedor (regra) · produto → orquestrador, backend, frontend

**O que foi feito:** registrei a decisão do dono do produto de 12 out 2026 sobre a M-02 da revisão de segurança (T-024): opção A da análise do produto (`C:/Users/Jota/Documents/giro-produto/analise-t156.md`, fora do git).

- `docs/regras-de-negocio.md`:
  - tabela de perfis: linha nova "Ver rendimento e custo de manutenção do veículo (`VEI-05`)", só administrador, gerente e financeiro;
  - `USR-09`: passa a cobrir a ficha do veículo. Para o vendedor e o vistoriador, o bloco vem ausente e a ficha esconde "Rendeu no ano" e "Custo de manutenção". O valor de compra continua só de administrador e gerente;
  - `VEI-05`: diz quem vê, e o cálculo não muda;
  - notas de 12 out 2026 no fim das seções de usuários e de veículos, e linha na tabela de decisões.
- `tarefas/backlog.md`: T-156 reescrita para o backend e o frontend, com os critérios (Bruna sem a chave; Rodrigo, Mariana e Lúcia com os dois valores; João sem mudança) e o teste `test_usr_09_vendedor_sem_custo_do_veiculo`.
- `tarefas/feito.md`: linha "T-156 (regra)", PR a abrir.

**Regras cobertas:** tabela de perfis, USR-09, VEI-05.

Nenhum número do seed muda. O financeiro continua recebendo o bloco, como hoje.

**O que ficou de fora:** o código. A T-156 continua no backlog para o backend (selector e teste) e depois para o frontend (esconder os dois cartões quando a chave vem ausente).

**Próximo passo:** o orquestrador abre o PR desta branch e passa a T-156 ao backend.

# T-284 · Corrigir placa e chassi pela tela · frontend → orquestrador, backend, design-system, qa

**O que foi feito:** na edição do veículo, o administrador tem "Corrigir placa ou chassi", que abre um diálogo (Dialogo do design system) com placa, chassi e motivo obrigatório; grava por `POST /api/veiculos/{id}/corrigir-identificacao/` mandando só o que mudou. Erro da API volta no campo: 400 `validacao` por campo (chassi com 17 caracteres, motivo) e 409 `VEI-01` no campo de `detalhes.campo` (placa ou chassi únicos). Ao concluir, relê a ficha e a lista e mostra "Identificação corrigida. A mudança ficou na auditoria." A dica dos campos somente leitura muda para o administrador. O diálogo fica fora do `<form>`, para o Enter não salvar a edição.
**Onde:** frontend/src/components/frota/CorrigirIdentificacao.tsx e EditarVeiculo.tsx, lib/api/veiculos.ts e tipos-frota.ts, falso-frota.ts; testes em CorrigirIdentificacao.test.tsx.
**Contrato:** `POST /api/veiculos/{id}/corrigir-identificacao/` (docs/api/veiculos.md).
**Regras cobertas:** VEI-01.
**O que ficou de fora:**
- **[decisão] para o backend:** `acoes` do veículo não tem uma flag para essa ação. A tela usa `pode.administracao` (flag da API, não perfil escrito na tela). Registrei no backlog a sugestão `acoes.corrigir_identificacao`; quando existir, a troca é uma linha.
- O design-system não tem tela de referência do diálogo; montei com o Dialogo e os campos da ficha. Se o design-system quiser desenhar, a troca é só visual.
- Sem teste de clique (testes de marcação estática); a gravação é testada pelo falso e pelo cliente HTTP.
- `veiculos.test.ts` linha 30 ainda dá erro de typecheck estrito nesta base; a correção é a do PR #284.
**Próximo passo para quem recebe:** orquestrador abre o PR; backend decide a flag em `acoes`.

# Feito

Formato: `T-0xx · título · agente · PR #n · handoff`.

- T-003 · Ambiente de desenvolvimento · devops · PR #1 · tarefas/handoffs/T-003-devops.md · db e redis sobem saudáveis; backend e frontend validados quando T-001 e T-002 entregarem
- T-006 · ADRs iniciais revisadas e modelo de dados · arquiteto · PR #2 · tarefas/handoffs/T-006-arquiteto.md
- T-031 · Responder as dúvidas de regra da T-006 · produto · PR #2 · tarefas/handoffs/T-031-produto.md · aprovadas pelo dono do produto e registradas como regra
- T-032 · Revisão de segurança do desenho da fundação · seguranca · PR #2 · tarefas/handoffs/T-032-seguranca.md · altos resolvidos nas ADRs 0013 e 0014; médios viraram T-033, T-034, T-035 e critérios em T-012, T-014, T-015, T-029
- T-002 · Esqueleto do frontend · frontend · PR #3 · tarefas/handoffs/T-002-frontend.md · compose testado com --no-deps; completo depende da T-001
- T-030 · Contratos da API de plataforma e filiais · arquiteto · PR #2 · tarefas/handoffs/T-030-arquiteto.md · inclui ADRs 0013 e 0014
- T-036 · Contratos da API de contas, veículos e clientes · arquiteto · PR #6 · tarefas/handoffs/T-036-arquiteto.md · inclui ADR 0015
- T-001 · Esqueleto do backend · backend · PR #4 · tarefas/handoffs/T-001-backend.md · 88 testes; compose completo verificado com T-002
- T-037 · Dúvidas da T-030 e critérios de aceite de T-010 a T-014 · produto · PR #6 · tarefas/handoffs/T-037-produto.md · item 12 decidido (A)
- T-004 · Portar o design system para código · design-system · PR #5 · tarefas/handoffs/T-004-design-system.md · conferência visual feita; Geist e ilustração de moto corrigidas
- T-026 · Desenhar telas que faltam para o MVP · design-system · PR #6 · tarefas/handoffs/T-026-design-system.md
- T-038 · Contratos da API de locações, vistorias e devolução · arquiteto · PR #6 · tarefas/handoffs/T-038-arquiteto.md · inclui contratos.md
- T-039 · Revisão de segurança do código da T-001 · seguranca · PR #6 · tarefas/handoffs/T-039-seguranca.md · sem altos; C-01 e C-02 na T-033, C-03 e C-05 na T-034, C-04 na T-035
- T-041 · Critérios de aceite de T-015 a T-018 · produto · PR #6 · tarefas/handoffs/T-041-produto.md · itens 11 a 20 decididos pelo dono
- T-043 · Contratos da API de financeiro e auditoria · arquiteto · PR #6 · tarefas/handoffs/T-043-arquiteto.md · inclui aprovacoes.md e ADR 0016
- T-044 · Contrato da API de importação por planilha · arquiteto · PR #7 · tarefas/handoffs/T-044-arquiteto.md · ADR 0017; correções da ADR 0014 (id_cifra no dado associado, só AES-256-GCM)
- T-045 · Conferir decisões de implementação da T-001 contra as ADRs · arquiteto · PR #8 · tarefas/handoffs/T-045-arquiteto.md · ADR 0018; pontos distribuídos em T-033, T-034, T-035, T-010, T-011, T-017
- T-005 · CI · devops · PR #9 · tarefas/handoffs/T-005-devops.md · o próprio PR roda o workflow
- T-042 · Componente de código de 6 dígitos · design-system · PR #10 · tarefas/handoffs/T-042-design-system.md
- T-020 · Telas de acesso e casca do app · frontend · PR #11 · tarefas/handoffs/T-020-frontend.md · dados falsos até a T-011; 390 px a validar com emulação (Edge headless não abre abaixo de 492 px)
- T-033 · Dados sensíveis na fundação · backend · PR a abrir (branch t-033-dados-sensiveis) · tarefas/handoffs/T-033-backend.md · 127 testes; inclui C-01, C-02 e o ator das tarefas (ADR 0018 item 3)
- T-033 · Dados sensíveis na fundação · backend · PR #16 · tarefas/handoffs/T-033-backend.md · 127 testes; dependência cryptography
- T-046 · Componentes pedidos pela T-020 · design-system · PR #15 · tarefas/handoffs/T-046-design-system.md · sem dependência nova
- T-049 · Divergências de tela restauradas · produto · PR #13 · tarefas/handoffs/T-049-produto.md

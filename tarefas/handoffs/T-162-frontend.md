# T-162 · Flag `lancamento_avulso` em `pode` (frontend) · frontend → orquestrador, qa

**O que foi feito:** o botão "Novo lançamento" de contas a receber passa a depender só de `pode.lancamento_avulso` (antes `despesas_aprovar || financeiro_pagar`). Cliente tipado regenerado com `npm run api:gerar`; os perfis do falso ganharam a flag (administrador, gerente e financeiro `true`; vendedor e vistoriador `false`).
**Onde:** frontend/src/components/financeiro/ListaReceber.tsx, lib/api/tipos.ts, testes/falsos/falso.ts, components/financeiro/Financeiro.test.tsx
**Regras cobertas:** tabela de perfis, FIN-07 (testes "T-162": por perfil e com a flag trocada à mão, para provar que a tela lê só ela).
**O que ficou de fora:** nada. A T-162 sai do backlog.
**Próximo passo para quem recebe:** orquestrador abre o PR.

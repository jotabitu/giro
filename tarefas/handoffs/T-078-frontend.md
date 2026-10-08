# T-078 · Menu segue a navegação da T-071 · frontend → orquestrador, qa

**O que foi feito:**
- `frontend/src/lib/api/falso-navegacao.ts` reescrito como porte de `backend/apps/contas/navegacao.py`: cada item definido uma vez (permissão, recurso do plano, atividade, módulo), `MENU_COMPLETO` e `MENU_INICIO` iguais aos do backend.
- As 5 diferenças da T-071 estão cobertas:
  1. `vendas` no menu do gerente;
  2. grupo Vendas do vendedor;
  3. `comissoes` no lugar de `relatorios` no financeiro;
  4. contador de `despesas` só para quem aprova;
  5. filtro de plano, atividade e módulos.
- `navegacaoFalsa(perfil, pode, variante, contexto?)` aceita `{ recursos, atividade, modulos }`. Sem contexto vale o plano Profissional, aluga e vende, com todos os módulos (menu cheio no desenvolvimento).
- A casca (`CascaDoApp`) e o início (`InicioPorPerfil`) já liam só `eu.navegacao`; não precisaram mudar.

**Testes:** `lib/api/falso-navegacao.test.ts` espelha `test_usr_05_usr_08_navegacao_por_perfil` e `test_usr_05_plano_atividade_e_modulos_escondem_itens` (5 perfis, módulos, plano Essencial, atividade, vendedor sem módulo de vendas) [USR-05] [USR-08].

**Check:** eslint, `tsc --noEmit`, vitest (135 passaram) e `next build` limpos.

**Fora do escopo:** ligar `contas` na API real continua em outra tarefa.

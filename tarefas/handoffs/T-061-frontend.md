# T-061 · Rotas do menu corrigidas na T-055 · frontend → orquestrador, qa

**O que foi feito:**
- `DESTINOS` de `frontend/src/lib/menu.ts` segue a tabela "Rotas do menu" de `docs/telas/README.md`: `avarias` `/vistorias/avarias`, `consultar_veiculo` `/veiculos`, `contas_a_pagar` `/financeiro/despesas`, `caixa_e_bancos` `/financeiro/caixa`, `propostas` `/vendas?aba=propostas`, `minhas_vendas` `/vendas`, `veiculos_a_venda` `/veiculos?status=a_venda`, `minhas_comissoes` `/financeiro/comissoes`.
- Rota ativa compara só o caminho (sem `?aba=` e `?status=`). Como vários itens dividem o caminho (`/veiculos`, `/vendas`), só o primeiro item que bate fica ativo.
- `hrefDoDestino` junta a query da rota com o `filtro` do painel (`/vendas?aba=propostas&...`).
- `InicioVistoriador`: "Consultar veículo" vai a `/veiculos` e "Avarias abertas" a `/vistorias/avarias`.
- `falso-painel.ts`: `a_receber_hoje_centavos` e KPI `entra_hoje` em 90740 com "3 parcelas", como em `painel.md` (T-055).

**Onde:** `frontend/src/lib/menu.ts`, `menu.test.ts`, `components/inicio/InicioVistoriador.tsx`, `lib/api/falso-painel.ts`.
**Regras:** USR-05. **Dependências novas:** nenhuma.
**Check:** `eslint`, `tsc --noEmit`, 111 testes e `next build` verdes. Não abri o navegador: a mudança é de rota e de texto do falso.

**O que ficou de fora:** as telas de destino (`/vistorias/avarias`, `/aprovacoes`, `/vendas`, `/financeiro/*`) ainda não existem; o link abre a página de não encontrada até a tarefa de cada módulo. `/financeiro/reembolsos` (só em `hrefDoDestino`) não está na tabela: produto/arquiteto confirmam.
**Próximo passo:** orquestrador abre o PR e tira a T-061 do backlog.

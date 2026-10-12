# T-141 · Menu do perfil nas telas próprias · produto → backend, frontend, qa, orquestrador

**O que foi feito:** decidi quais telas mantêm o menu do perfil e o que entra no menu completo de cada perfil, a partir do achado no compose (`main` b675292): o João (vistoriador) tem no início o menu do perfil, mas na própria agenda (`/vistorias`) recebia o `menu_completo` (Visão geral, Veículos 86, Locações 51), sem a agenda.
**Onde:** `docs/regras-de-negocio.md` (`USR-05` reescrita com os perfis, frase do menu na `USR-08`, nota de mudança de 12 out 2026); `docs/api/contas.md` (menu e início); `tarefas/backlog.md` ("Inclui" da T-136).
**Regras cobertas:** USR-05, USR-08.

## Decisões

1. **Telas próprias:** o menu do perfil vale no início e nas rotas que os itens desse menu abrem, com as sub-rotas (só o caminho, sem a query). Fica geral e sai da própria navegação da API, sem lista de rotas no frontend.
   - Vistoriador: todas as telas (menu único).
   - Gerente: início, Aprovações, Veículos, Locações, Vendas, Clientes, Manutenções, Caixa da filial, Relatórios. Completo em Contas a receber e Despesas.
   - Vendedor: início, Locações, Clientes (fase 2: Vendas, Veículos à venda, Minhas comissões). Completo em Veículos, Caixa, Contas a receber e Despesas.
   - Financeiro: início, Contas a receber, Contas a pagar, Caixa e bancos, Comissões. Completo em Clientes, Conciliação e Relatórios.
   - Administrador: sem menu próprio, completo sempre.
2. **Menu completo do vistoriador = menu do perfil** (`agenda`, `consultar_veiculo`, `avarias`). Sai "Visão geral" (a tabela de perfis não dá painel a ele) e sai "Locações": o contrato de locações já dizia que a lista é de "todos menos vistoriador" (`docs/api/locacoes.md`), e ele chega à vistoria e à devolução pela agenda (`VIS-05`). Por isso `locacoes` no menu pede só `locacoes_criar`; para os outros perfis nada muda.
3. **Rótulo do início** no menu completo é o do início do perfil: Visão geral (administrador), Visão da filial (gerente), Início (vendedor e financeiro).
4. **Barra do celular:** `veiculos` entra também quando há `consultar_veiculo`, para o vistoriador não perder Veículos.

Nada muda o que um perfil pode fazer, só o menu; a lista de locações já era negada ao vistoriador pela API. Por isso não abri `[decisão]` para o dono do produto.

**O que ficou de fora:** o contador de Locações do vendedor (todas da filial ou só as dele) não foi tratado aqui.

**Próximo passo para quem recebe:**
- **Backend (T-136):** `menu_completo` por perfil como em `docs/api/contas.md`; teste `test_usr_05_menu_completo_do_vistoriador`.
- **Frontend (T-136):** `gruposDaRota` (`frontend/src/lib/menu.ts`) com o `menu_inicio` nas rotas dos itens dele; teste com `usr_05` no nome.
- **QA:** conferir João em `/vistorias` e `/vistorias/avarias` e Lúcia em `/financeiro/receber` e `/clientes`, como no "Inclui" da T-136.
- **Orquestrador:** abrir o PR.

# T-047 · Menu por permissão e agregados do painel · arquiteto → frontend, backend, orquestrador

**O que foi feito (as três `[decisão]` da T-020):**
1. **Menu por permissão (`USR-05`):** `GET /api/auth/eu/` ganhou `navegacao` em `docs/api/contas.md`: `menu_inicio` (menu da tela inicial do perfil), `menu_completo` (telas compartilhadas) e `barra_celular`, já filtrados por permissão, recurso do plano, atividade da empresa (aluga/vende) e módulos entregues (`GIRO_MODULOS_ATIVOS`). Cada item traz `chave`, `rotulo` e a chave do contador. O frontend deixa de mapear item → `pode` em `lib/menu.ts` e só liga `chave` → rota e ícone.
2. **Início por perfil (`USR-08`, decidida com o produto, commits 0a81a9b e seguinte na t-041-criterios-locacao):** rota única `/inicio` e `navegacao.inicio.variante`: `implantacao` (administrador até a `IMP-01`), `geral` (Main), `gerente`, `vendedor` (fase 1: locação), `vistoriador` (agenda) e `financeiro` (sem o que é fase 2).
3. **Agregados:** `docs/api/painel.md` com `GET /api/painel/contadores/` (contador de cada item do menu, com escopo e o `APR-09` nas aprovações) e `GET /api/painel/inicio/` (blocos de cada variante, valores tipados, textos prontos, blocos de módulo inexistente vindo `null`).

**Ajustes do produto aplicados:** aprovações do gerente sem os pedidos dele; equipe hoje só da filial; "meus" do vendedor = locações que ele criou, com o bloco de parcelas atrasadas dessas locações; sem comissão prevista na fase 1; "Para hoje" do financeiro só com reembolsos a fazer e despesas a pagar vencendo; nunca número de exemplo.

**Onde:** `docs/api/contas.md` (seção "Menu e início"), `docs/api/painel.md`, `docs/decisoes/modelo-de-dados.md` (`meta_ocupacao_pct` em `ConfiguracaoEmpresa`).

**Para o frontend (T-020):** trocar em `falso.ts` os KPIs com valor em texto ("R$ 18,4 mil") por `{ tipo, valor }` em centavos e formatar na tela; ler `navegacao` em vez de montar o menu a partir de `pode`; esconder todo bloco `null`.

**Para o backend:** os agregados ficam em `relatorios` (só leitura, nível 13); o menu é montado em `contas` (tabela da seção "Menu e início"). `GIRO_MODULOS_ATIVOS` é uma configuração nova do backend (lista de módulos entregues).

**Divergência para T-028:** a tela `Pos-Dashboard` tem "Instalar o app no celular do vistoriador" e "Conectar o WhatsApp da loja", que dependem de recursos ainda sem regra nem contrato; o contrato só os mostra quando existirem. A meta de ocupação de 80% das telas virou configuração da empresa com esse padrão.

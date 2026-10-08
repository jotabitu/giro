# T-055 · Contratos alinhados à T-053 e conferência da T-010 · arquiteto → orquestrador, backend, frontend, qa

**O que foi feito:**
- **CNPJ do seed:** `docs/api/filiais.md` e `docs/api/plataforma.md` com a Moto Rápida em `12345678000195` e a Filial Caucaia em `12345678000276` (os dois conferidos pelo dígito verificador).
- **`docs/api/financeiro.md` (`FIN-15`):** `recebido_pct` "29.11" (2160000 ÷ 7420000). `contagens` são as quatro abas mais `todas` = soma delas (2 + 3 + 226 + 72 = 303); `canceladas` não é aba. `previsto_mes_parcelas` fecha com as abas no período `mes` (pagas + vencem hoje + a vencer + atrasadas do próprio mês = 301). Escrito de onde vem cada indicador, que eles não mudam com `?periodo=`/`?situacao=`, e que o contador `receber` do menu é `contagens.atrasadas`.
- **Vence hoje** (`financeiro.md`, `painel.md` `caixa_hoje.a_receber_hoje_centavos` e KPI `entra_hoje`): saiu o 189000 em "9 parcelas" (9 parcelas custam no mínimo R$ 2.511,00). Ficou um exemplo que fecha com a tabela de preços: 90740 em 3 parcelas (Urbana semanal 29940 + Street semanal 32900 + Entregador 27900), marcado como ilustrativo até o seed ter a carteira de outubro. Os três lugares usam o mesmo número.
- **Previsto, recebido, a vencer e pagas** continuam os da tela (74,2 mil, 21,6 mil, 226, 72), marcados como ilustrativos: a carteira de outubro ainda não existe (T-053). Não inventei números de seed.

**Conferência das 8 decisões de implementação da T-010** (nenhuma muda decisão de ADR, então não há ADR nova):
1. Login da equipe em `contas/api/plataforma.py` e o administrador criado por `contas` assinando `plataforma.empresa_criada`: **de acordo** com a ADR 0011 (`contas`, nível 4, importa de `plataforma`, nível 3; o fato sobe por evento). O evento está documentado em `apps/plataforma/README.md`, como a 0011 pede.
2. `dados` = passo `importar`, etapa = primeira do funil não concluída, "Parada no passo N" pelo primeiro dos 10 passos aberto: **de acordo** com `IMP-05`; escrito em `plataforma.md`. `ramo`, `contrato`, `recebimentos` e `equipe` contam em `concluidos` e não movem o funil.
3. `Empresa.TRANSICOES` só com as saídas da tabela de estados: **de acordo** (máquina de estados igual à regra; pausar e cancelar entram com as ações da fase 2).
4. `contagens` (`em_teste` e `ativa` pelo status; `com_problema` e `saindo` pela aba; `pagantes` = todas − `em_teste`): **aceito** e escrito em `plataforma.md`. Consequência registrada: empresa em teste com implantação parada conta em `em_teste` e em `com_problema`.
5. `cancelada` depois de `acesso_ate` e `fatura_atrasada` sem dias na fase 1: **aceito**; linha `cancelada` acrescentada à tabela de `situacao` e nota da fase 1.
6. `acoes` tudo `false` e `chamados_abertos: 0` na fase 1: **aceito**; nota no detalhe da empresa (o exemplo mostra a fase 2).
7. Bloqueio do `PLT-08` feito pelo Giro e atraso progressivo do django-otp desligado: **de acordo** com a ADR 0013 (o bloqueio de 3 códigos por 15 minutos já estava no contrato, 429 `PLT-08`). A T-011 tem que fazer o mesmo para os usuários da empresa (`USR-06`), já que o desligamento vale para todos.
8. Token do convite fora da fila, gerado na tarefa: **de acordo** com as ADRs 0008 (só o hash no banco) e 0012 (tarefa recebe só ids). Efeito igual ao "reenviar convite": o link anterior deixa de valer.

**Rotas inventadas da T-048:** nova seção "Rotas do menu" em `docs/telas/README.md`, com a rota de toda `chave` da navegação. Confirmadas: `/aprovacoes`, `/vistorias` (agenda). Corrigidas: `avarias` → `/vistorias/avarias`; `consultar_veiculo` → `/veiculos`; `contas_a_pagar` → `/financeiro/despesas`; `caixa_e_bancos` → `/financeiro/caixa`; `propostas` → `/vendas?aba=propostas`; `minhas_vendas` → `/vendas`; `veiculos_a_venda` → `/veiculos?status=a_venda`; `minhas_comissoes` → `/financeiro/comissoes`.

**Onde:** `docs/api/filiais.md`, `docs/api/plataforma.md`, `docs/api/financeiro.md`, `docs/api/painel.md`, `docs/telas/README.md`.

**Check:** só documentação; nenhum arquivo de `backend/` ou `frontend/` mudou, então não rodei `make backend-check` nem o check do frontend.

**O que ficou de fora:**
- O quadro (`backlog.md`, `em-andamento.md`, `feito.md`): o orquestrador pediu para não mexer até o PR #28 entrar.
- `backend/tests/aceitacao/test_t014_clientes.py:18` ainda cita `12.345.678/0001-10` no texto de um critério em `xfail`: fica para a T-014 (backend) ou o qa.
- Os números de seed de previsto, recebido e vence hoje esperam a carteira de outubro (proposta da T-053).

**Próximo passo para quem recebe:**
- **Frontend:** trocar em `DESTINOS` de `lib/menu.ts` as 8 rotas corrigidas; para itens com query (`?aba=`, `?status=`), a rota ativa compara só o caminho. Em `falso-painel.ts`, `a_receber_hoje_centavos` e `entra_hoje` passam a 90740 em "3 parcelas".
- **Backend (T-011):** bloqueio de código errado do `USR-06` feito pelo Giro, já que o atraso do django-otp está desligado para todos. **(T-017):** `contagens.todas` = soma das quatro abas e `recebido_pct` com 2 casas, como em `financeiro.md`.
- **QA:** teste da `FIN-15` pode usar o exemplo de vence hoje (3 parcelas = R$ 907,40) como caso pequeno próprio.

**Acréscimo (pedido do backend na T-012):** `docs/api/filiais.md` dizia que, na criação da filial, os feriados nacionais já entravam confirmados. Corrigido para seguir a `FIL-03` e o CA-012-08: a filial nasce sem feriados, e os nacionais são só sugestão até o administrador confirmar.

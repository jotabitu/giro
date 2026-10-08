# T-071 · Navegação do eu · backend → frontend, qa, devops, orquestrador

**O que foi feito:**
- `GET /api/auth/eu/` (e o `usuario` do `pronto`) devolve `navegacao`, como em `docs/api/contas.md`, "Menu e início":
  - `inicio`, com `rota` e `variante`;
  - `menu_inicio`;
  - `menu_completo`;
  - `barra_celular`.
- **`apps/contas/navegacao.py`:** cada item é definido uma vez, com a permissão (a partir do `pode`), o recurso do plano, a atividade e o módulo.
  - O `menu_completo` segue a tabela do contrato.
  - O `menu_inicio` de cada variante segue as telas Gerente, Vendedor, Vistoriador e Financeiro.
  - As variantes `geral` e `implantacao` usam o `menu_completo`.
  - Item sem permissão não vem, e grupo vazio também não.
- **Variante (`USR-08`):**
  - O administrador fica em `implantacao` até o passo `primeira_locacao` (`IMP-01`, `UsoEmpresa.passos_implantacao`). Depois passa a `geral`.
  - Os outros perfis têm a variante do próprio perfil.
  - No modo suporte, a variante é a do administrador, e o menu segue o `pode` do suporte. Com "ver", só aparecem `inicio`, `veiculos`, `relatorios` e a Administração.
- **Aprovações:** aparecem para quem decide pedidos, ou seja, quem tem `desconto_acima_limite` ou `locacoes_cancelar` em `aprova` ou `sim`. Isso cobre o gerente, o administrador e as permissões extras.
- **`GIRO_MODULOS_ATIVOS`** é uma configuração nova, com a lista de apps entregues. O padrão é `contas,filiais,plataforma`. O mapa de cada item para o seu app está no contrato.
- **Atividade:** `ConfiguracaoEmpresa.atividade` ainda não existe, porque entra com a tela Config. Até lá, a navegação considera que a empresa aluga e vende. O `montar()` já recebe a atividade e tem teste.

**Onde:**
- `backend/apps/contas/navegacao.py` (novo), `selectors.py`, `api/acesso.py` (`NavegacaoSerializer`) e `README.md`.
- `backend/config/settings/base.py`.
- O contrato em `docs/api/contas.md`, com a tabela do `menu_inicio`, o mapa de módulos e a barra. O OpenAPI em `docs/api/openapi.yaml` só ganhou o objeto `navegacao`.

**Testes** (`tests/aceitacao/test_t011_contas.py`):
- `test_usr_05_usr_08_navegacao_por_perfil`: Mariana, Rodrigo, Bruna, João e Lúcia, com o menu do início, o menu completo, os rótulos, o contador de despesas e a barra. Também a extra `aprovar_desconto` trazendo Aprovações para a vendedora.
- `test_usr_05_plano_atividade_e_modulos_escondem_itens`: os módulos padrão, o plano Essencial e as atividades "só aluga" e "só vende".
- `test_usr_08_administrador_ve_o_geral_depois_da_primeira_locacao`: a variante `geral` e o suporte com "ver".

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `345 passed, 43 xfailed`.
- OpenAPI regerado com `--validate`, sem aviso.
- Rodado no Postgres descartável, com `--rm` e `POSTGRES_HOST`.

**Diferenças em relação ao `frontend/src/lib/api/falso-navegacao.ts`** (o formato é o mesmo de `tipos.ts`):
1. O `menu_inicio` do gerente tem `vendas` em Operação, como na tela Gerente.
2. O `menu_inicio` do vendedor ganhou o grupo "Vendas", com `propostas`, `minhas_vendas`, `veiculos_a_venda` e `minhas_comissoes`, como na tela Vendedor. O grupo só aparece com o módulo `vendas` ativo.
3. O `menu_inicio` do financeiro termina em `comissoes` e não tem `relatorios`, como na tela Financeiro. Relatórios continua no `menu_completo`.
4. O `contador` de `despesas` só vem para quem aprova despesas. Para quem só lança, vem `null` (`painel.md`).
5. Todos os itens também passam pelo plano, pela atividade e pelos módulos. Com o padrão de hoje, o menu fica bem curto.

**Próximo passo para quem recebe:**
- **Frontend:** trocar o `falso-navegacao.ts` pela `navegacao` do `eu`, numa tarefa própria. Para ver o menu cheio no desenvolvimento, use `GIRO_MODULOS_ATIVOS` com todos os apps.
- **DevOps:** a variável `GIRO_MODULOS_ATIVOS` é nova. Ela é uma lista separada por vírgula e não precisa ser definida em produção enquanto o padrão servir.
- **Backend (módulos novos):** cada entrega acrescenta o seu app ao padrão de `GIRO_MODULOS_ATIVOS` em `config/settings/base.py`.

# T-131 · Registrar a primeira locação na implantação (IMP-01) · backend → orquestrador, qa, frontend, arquiteto

**O que foi feito:**
- `plataforma.services.concluir_implantacao(objeto)`: registra o passo `primeira_locacao` em `UsoEmpresa.passos_implantacao` (data de hoje, `relogio`) uma vez só, com o evento `implantacao.concluir` (categoria `configuracoes`, regra `IMP-01`, objeto = a locação, ator = quem confirmou) na auditoria da empresa. Antes de travar `UsoEmpresa`, uma leitura sem trava (`passos_implantacao__has_key`) evita disputar a linha a cada locação depois da primeira. Devolve se concluiu agora.
- `registrar_passo_implantacao` passa a devolver `bool` (passo novo ou não); quem já chamava não muda.
- `locacoes.services.confirmar` chama `concluir_implantacao` no fim da mesma transação: se a confirmação desfaz, o passo e o evento saem juntos. Rascunho e confirmação recusada (ex.: `IMP-04`) não concluem.
- **Cache do painel:** a chave de `GET /api/painel/inicio/` e `/contadores/` ganhou a variante (`painel:<schema>:<pessoa>:<filial>:<rota>:<variante>[:<periodo>]`). A navegação passa a ser calculada antes do cache (uma leitura de `UsoEmpresa`). Assim, depois da 1ª locação, a Mariana sai de `implantacao` para `geral` na hora, no `eu` e no painel, sem esperar os 5 minutos.
- `docs/api/plataforma.md` ("Interface interna"): linha de `concluir_implantacao`. **Arquiteto:** conferir a linha.

**Regras cobertas:** IMP-01 (e o funil da IMP-05, pelo mesmo `registrar_passo_implantacao`). Testes em `backend/tests/aceitacao/test_t131_primeira_locacao.py`: `test_imp_01_primeira_locacao_conclui_a_implantacao` (passo `2026-10-07`, um evento na LOC-2856 por Bruna, `eu` e painel de `implantacao` para `geral`, com o painel já em cache), `test_imp_01_segunda_locacao_nao_registra_de_novo` (LOC-2857 não grava outra data nem outro evento), `test_imp_01_confirmacao_desfeita_nao_conclui` (falha na auditoria desfaz a confirmação e o passo), `test_imp_01_locacao_recusada_nao_conclui` (`IMP-04`).

**Testes ajustados:** a carteira de outubro dos testes confirma locações pelo serviço, então conclui a implantação. `test_usr_08_imp_01_implantacao` (T-129) volta os passos para antes da 1ª locação; o teste do cache (agora `test_usr_08_cache_por_pessoa_rota_e_variante`) espera a variante na chave.

**Checks:** ruff, format, mypy e `makemigrations --check` limpos (sem migração); testes afetados rodados um arquivo por vez, todos passando: aceitação da T-010, T-011, T-015, T-016 (1 xfail que já existia), T-056, T-081, T-090, T-091, T-111, T-123, T-129 (painel e marca) e T-131, e os testes de `apps/plataforma` e `apps/contas`. OpenAPI sem mudança (nenhuma rota ou serializer mudou), frontend não precisa de `api:gerar`.

**O que ficou de fora:**
- **Venda:** o app `vendas` ainda não tem serviço. Quando a confirmação da venda existir, ela chama `plataforma.services.concluir_implantacao(venda)` na mesma transação (a função já vale para qualquer objeto do Giro).
- **Seed da T-127:** a branch `t-127-seed-parcial` (ainda fora da main) confirma as locações por `locacoes_services.confirmar`, então com este PR a Mariana já cai em `geral` (tela `Main`) sem mudança no seed. Não deu para rodar o seed aqui porque ele não está na main.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR. Mergear a T-127 depois desta (ou junto) para o seed deixar a Mariana na `Main`.
- **QA:** na T-127, um teste de que, depois do seed, `GET /api/auth/eu/` da Mariana traz `navegacao.inicio.variante == "geral"` e `passos_implantacao.primeira_locacao` existe; o teste de rodar o seed duas vezes deve continuar com um só evento `implantacao.concluir`.
- **Frontend:** nada a mudar; a variante continua vindo do `eu` e do painel.

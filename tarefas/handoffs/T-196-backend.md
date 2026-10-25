# T-196 · Módulos por plano · backend → orquestrador, frontend, qa, produto, segurança

Branch `t-196-modulos-por-plano`, criada da `origin/main` (626d432). Contrato: ADR 0024; `docs/api/plataforma.md` ("Planos", "Módulos por plano", "Interface interna"); `docs/api/assinatura.md` (422 `PLT-04`); handoffs T-192, T-224 e T-262 ("O que ficou de fora (T-196)").

**O que foi feito:**

- **Enum e planos (item 1).** `plataforma.Recurso` com a lista nova:
  - entram `conciliacao`, `recebimento_parceiro` ("Pix e boleto automáticos") e `cobranca_whatsapp` ("Cobrança pelo WhatsApp");
  - saem `dominio_proprio` e `api_integracoes`.
  - A migração `plataforma.0013_recursos_dos_planos` regrava os três planos pela tabela de `plataforma.md`. Um plano criado à mão só perde os dois recursos que saíram.
  - `Plano.recursos` ganhou o validador `validar_recursos`: valor fora do enum é recusado.
- **`tem_recurso` (item 2).** `comum.empresa.tem_recurso(recurso)` e `recursos()`, registrados pelo `ready()` do `plataforma` (`selectors.recursos_ligados` e `recusa_do_modulo`).
  - No `public`, ou sem empresa na conexão, tudo vale.
  - A conta (plano mais ramo) é feita uma vez por pedido, pelo middleware novo `RecursosDoPedidoMiddleware`. Fora de um pedido (tarefas, serviços), a conta é refeita a cada chamada.
  - `mudar_ramo` limpa a conta guardada (`esquecer_recursos`).
- **403 `PLT-12` (item 4).** `comum.permissoes.ModuloDoPlano` entrou em `DEFAULT_PERMISSION_CLASSES` logo depois de `IsAuthenticated`, antes de perfil e filial. A view declara `recurso_do_plano`, ou `recurso_por_acao`. A recusa vale também para o suporte.
  - `locacoes_vistoria`: todas as views de `locacoes` e `vistorias` (bases `ViewDeLocacao` e `ViewDeVistoria`).
  - `manutencao_despesas`: as 4 rotas de despesas, e também o pedido de exportação de despesas (`financeiro.exportacao.validar`).
  - `recebimento_parceiro`: `POST contas-receber/{id}/cobranca/`.
  - Corpo de `plataforma.md`: `motivo: "plano"` com `Recurso.label`, ou `motivo: "ramo"` ("Sua empresa não está configurada para alugar.").
  - `test_permissoes_das_rotas.py::test_plt_12_rotas_por_recurso` confere a tabela "Rotas por recurso".
- **Menu (item 3).** `contas.navegacao.da_empresa` usa `recursos_para(plano, atividade)`, que é o `recursos_da_empresa`. O item `conciliacao` tem recurso próprio, então sai do menu do Essencial.
- **Fora das rotas (item 5).**
  - `comum.leituras`: anotação, contador e total aceitam `recurso=`. Com o recurso desligado, o bloco não vem, o contador vale 0 e o total `None`, sem rodar a query. Usado nos blocos e contadores de `locacoes` e `vistorias`.
  - `comum.tarefas.tarefa_de_empresa(recurso=...)`: a empresa sem o módulo é pulada sem erro (`aut_02_marcar_devolucao_atrasada` e `locacoes_cancelar_rascunhos_sem_uso`).
  - Régua e "Cobrar" (`AUT-03`): sem `cobranca_whatsapp`, só e-mail; sem `recebimento_parceiro`, não gera Pix e usa "Pague na loja", mesmo com a subconta aprovada.
  - Implantação: sem `recebimento_parceiro`, o passo `recebimentos` sai também de `plataforma.selectors.implantacao`, e `concluidos` e `total` contam 9 (`GET /api/plataforma/empresas/{id}/`). O assistente já fazia isso. Agora vale de verdade, porque o recurso existe.
- **Downgrade (itens 7 e 10).**
  - `pendencias_dos_modulos(empresa, recursos_que_saem)` conta no schema da empresa, ou no corrente com `empresa=None`.
  - `financeiro` registra os grupos `despesas_aguardando_aprovacao` e `despesas_a_pagar`.
  - `excede_no_plano` calcula os recursos que saem com o ramo de hoje e acrescenta `detalhes.atividade` quando o plano novo não aceita o ramo. A 422 `PLT-04` usa então "O plano Essencial não inclui vendas. Para mudar, sua empresa precisa alugar."
  - Valem o simular, o pedido, o `excede` de `planos/` e a conferência de `gerar_faturas`.
  - `mudar_ramo` passou a chamar `pendencias_dos_modulos(None, ...)`.
- **Comissão (item 11).** `financeiro.lancar_comissao` só cria com `vendas_comissoes` ligado no momento. Confirmar, pagar e estornar continuam mexendo só na comissão que já existe.
- **Consultas.** A Configurações voltou ao teto de 11: `plataforma.selectors.empresa_carregada()` lê a empresa com o plano uma vez, e `assinatura(empresa, carregada=True)` não relê.

**Onde:**
- `backend/apps/plataforma/` (models, migração 0013, selectors, services, apps);
- `backend/comum/` (empresa, permissoes, middleware, leituras, tarefas);
- `backend/config/settings/base.py`;
- views de `locacoes`, `vistorias` e `financeiro`;
- `financeiro` (services, apps, exportacao);
- `locacoes` (leituras, tasks) e `vistorias/leituras.py`;
- `contas/navegacao.py`;
- `empresas` (selectors, services);
- `relatorios/selectors.py`.

O OpenAPI não mudou: `recursos` é uma lista de texto, conferido com `--validate` e sem diferença.

**Critérios e testes** (`tests/aceitacao/test_t196_modulos_por_plano.py`, 10 testes):

| Critério | Testes |
| --- | --- |
| CA-ASS-22 | `test_plt_12_essencial_sem_modulos_do_profissional` (403 com o mesmo corpo para administrador, gerente e suporte; menu; 9 passos; `recursos_da_empresa`), `test_plt_12_profissional_com_os_modulos`, `test_aut_03_essencial_so_email` |
| CA-ASS-23 | `test_plt_12_dados_guardados_ao_descer` |
| CA-ASS-24 | `test_plt_12_downgrade_recusado_com_modulo_aberto`, só com a despesa a pagar: as OS entram com o app `manutencao` |
| CA-ASS-15 | `test_plt_04_downgrade_nao_cabe_com_os_abertos_do_seed`, com a 422 e o `excede` de `planos/` |
| CA-ASS-52 | `test_plt_12_downgrade_so_vende` |
| CA-ASS-53 | `test_plt_12_comissao_so_depois_do_upgrade` (pelo serviço, sem a locação inteira) |
| Ramo e tarefas | `test_plt_12_ramo_desliga_modulo` (motivo `ramo`, menu, contador 0), `test_plt_12_tarefa_pulada_sem_o_modulo` |
| Rotas | `tests/test_permissoes_das_rotas.py::test_plt_12_rotas_por_recurso` |

Critérios que já existiam:
- CA-ASS-20 e 21: catálogo e oferta, em `test_t185_assinatura.py`.
- CA-ASS-25: filial acima do limite pelo `PLT-03`, nos testes da T-012 e da T-185. Nada mudou.
- CA-ASS-50 e 51: `test_t262_ramo.py`.

Nenhum `xfail` dependia da T-196.

**Testes que mudaram:**
- `test_t262_ramo.py`: os nomes dos 9 módulos do Profissional.
- `test_t011_contas.py`: o Essencial perde Conciliação no menu (CA-ASS-22).
- `test_t202_telas_resolvidas.py` e `test_t341_implantacao_placa.py`: só o comentário.

**Testes rodados** (contêiner avulso na rede `giro-backend-teste`, banco `giro`, uma parte por vez, com `docker ps` antes de cada uma):

- Conferências: `ruff check`, `ruff format --check`, `mypy` (402 arquivos), `makemigrations --check` e o OpenAPI com `--validate` passaram.
- Resultado por parte:

  | Parte | Resultado |
  | --- | --- |
  | 1. plataforma (`apps/plataforma`, `apps/empresas` e a aceitação da assinatura, com `--create-db`) | 384 passaram, 2 xfail e 2 falharam: o teto da Configurações e os nomes no t262. Corrigidos; reteste das duas e da plataforma: 105 passaram |
  | 2. financeiro | 95 passaram |
  | 3. locações, vistorias, contratos e aprovações | 211 passaram |
  | 4. contas, auditoria e segurança | 139 passaram e 1 falhou (o menu do Essencial no t011). Corrigido; reteste: 5 passaram |
  | 5. `comum` e `tests/*.py` | 284 passaram |
  | 6. o resto (aceitação, `apps/filiais`, `apps/importacao`) | 461 passaram, 5 xfail e 1 falhou: `test_t265_leitura_crlv.py::test_adr_0026_filho_so_com_path_e_lang_e_os_limites`. Sozinho, passa. É o processo filho da leitura do CRLV, com limites de recursos, numa rodada longa da máquina com pouca memória. Não toca no que a T-196 mudou |

**O que ficou de fora:**
- `para_cada_empresa` não filtra por recurso: ela enfileira todas, e a tarefa marcada com `recurso=` pula a empresa no schema dela. O resultado é o mesmo, sem entrar em cada schema só para enfileirar.
- Os grupos `ordens_servico` e `vendas` valem 0 até os apps `manutencao` e `vendas` existirem. O mesmo vale para as rotas da fase 2 (vendas, manutenção, conciliação, relatórios), já previstas na tabela do teste.
- O painel: nenhum número de hoje vem de módulo que o Essencial não tem (as despesas não estão no painel), então nada mudou nele.
- **Para a T-377 (depois da T-356, PR #395):** a comissão de locação nasce hoje no Profissional, que tem `vendas_comissoes`. Isto é, um plano à venda na fase 1 tem o recurso, e a comissão nasce. A T-377 faz `lancar_comissao` exigir também o módulo entregue (`GIRO_MODULOS_ATIVOS`) e ajusta os testes e o seed (QA).
- **Para a T-378:** o Completo fora da venda (CA-ASS-70), com um campo próprio de "à venda".

**[decisão] para o Produto:** no e-mail do downgrade agendado recusado ("Giro: a mudança para o plano ... não aconteceu"), o motivo da atividade sai como "a empresa só vende". O texto é meu: o contrato não o traz.

**Próximo passo para quem recebe:**
- **Frontend:** o 403 `PLT-12` mostra a `mensagem`. Nada a calcular: o menu já vem sem os módulos desligados. Na 422 `PLT-04`, `detalhes.atividade` pode vir.
- **QA:** os testes acima. Na `docs/qa/cobertura-de-regras.md`, a linha "CA-ASS-20 a 25, 50 a 53" deixa de esperar a T-196.
- **Segurança:** a permissão vem antes de perfil e filial e vale para o token de suporte.
- **Produto:** a [decisão] acima.

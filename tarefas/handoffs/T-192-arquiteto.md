# T-192 · ADR dos módulos por plano · arquiteto → orquestrador, backend (T-196, T-185, T-186), frontend, produto, qa

**O que foi feito:** ADR 0024 (`docs/decisoes/0024-modulos-por-plano.md`) e os contratos que ela toca. Branch `t-192-adr-modulos-por-plano`, a partir da `origin/main`.

- **Módulo do plano = `plataforma.Recurso`, não o app** (o `financeiro` tem partes do Essencial e do Profissional). Lista nova: `locacoes_vistoria`, `contas_receber`, `contrato_digital` (Essencial, Profissional e Completo); `vendas_comissoes`, `manutencao_despesas`, `conciliacao`, `relatorios`, `recebimento_parceiro`, `cobranca_whatsapp` (Profissional e Completo); `suporte_prioritario` (Completo). Saem `dominio_proprio` e `api_integracoes` (`PLT-11`). O núcleo não tem recurso.
- **Por empresa:** `recursos_da_empresa()` = `Plano.recursos` menos `locacoes_vistoria` se o ramo não aluga e menos `vendas_comissoes` se não vende. Calculado a cada pedido, nada guardado. `GIRO_MODULOS_ATIVOS` continua global e só diz o que já foi entregue.
- **Recusa:** 403 `PLT-12` com `detalhes.recurso` e `motivo` (`plano` ou `ramo`), em leitura e escrita, antes de perfil e filial. Tabela "Rotas por recurso" em `plataforma.md`.
- **Fora das rotas:** leituras compostas, contadores e totais com `recurso=` (bloco `null`); painel `null` para módulo desligado; tarefas por empresa com `recurso=` (empresa pulada); assinantes de evento não agem; régua só por e-mail sem `cobranca_whatsapp`, sem Pix sem `recebimento_parceiro`; passo `recebimentos` fora no Essencial (9 passos).
- **Downgrade:** `comum.modulos.registrar_pendencia(recurso, grupo, contar)` nos apps donos; `plataforma.services.pendencias_dos_modulos` soma no schema da empresa. 422 `PLT-04` com `detalhes.abertos` (lista com `grupo`, `quantidade`, `texto`) e `abertos_texto` ("1 despesa a pagar e 1 OS aberta", CA-ASS-24); o mesmo em `excede.abertos` de `planos/` e no downgrade agendado que deixa de caber.

**Onde:** `docs/decisoes/0024-modulos-por-plano.md`, `docs/decisoes/README.md`, `docs/decisoes/modelo-de-dados.md` (`Plano.recursos`), `docs/api/plataforma.md` ("Planos" e a seção nova "Módulos por plano", interface interna), `docs/api/assinatura.md` (422 e `excede`, T-185 e T-186), `docs/api/contas.md` (menu: `conciliacao` com recurso próprio, exemplo do Essencial), `docs/api/configuracoes.md` (9 passos no Essencial, `precos`), `docs/api/financeiro.md` (canais da régua, 403 no `cobranca/`), `docs/api/painel.md`, `docs/api/README.md` (403).

**Regras cobertas:** PLT-12, PLT-11 (recursos), PLT-04 (recusa por módulo aberto), AUT-03 (canal no Essencial), USR-05. Critérios CA-ASS-20 a 25.

**O que muda para a T-196 (backend):**
1. `plataforma.Recurso` com a lista nova; migração de dados regrava os três planos (tabela em `plataforma.md`, "Planos"); validação do enum.
2. `plataforma.selectors.recursos_da_empresa()` e `comum.empresa.tem_recurso()` (registrado no `ready()` de `plataforma`); `comum.empresa.atividade()` registrado por `empresas` (`ambos` até existir `ConfiguracaoEmpresa.atividade`).
3. `comum.permissoes.ModuloDoPlano` em `DEFAULT_PERMISSION_CLASSES`, depois de `IsAuthenticated`; `recurso_do_plano` / `recurso_por_acao` nas views (hoje: `locacoes`, `vistorias`, despesas e `cobranca/` do `financeiro`); `test_permissoes_das_rotas.py` cobra a tabela.
4. `contas.navegacao.da_empresa` passa a usar `recursos_da_empresa()`; item `conciliacao` com o recurso `conciliacao`.
5. `comum.leituras` com `recurso=`; `tarefa_de_empresa` e `para_cada_empresa` com `recurso=`; assinantes de evento conferem `tem_recurso`.
6. Régua (`AUT-03`) e "Cobrar": canal WhatsApp só com `cobranca_whatsapp`; Pix só com `recebimento_parceiro`.
7. Passo `recebimentos` fora da lista sem `recebimento_parceiro` (`plataforma.selectors.implantacao` e `configuracoes`).
8. `comum.modulos.registrar_pendencia` e `plataforma.services.pendencias_dos_modulos`; registrar hoje os grupos de despesas (`financeiro`); `ordens_servico`, `vendas` e `comissoes` entram com os apps deles (valem 0 até lá).
9. Testes com o código: `test_plt_12_essencial_sem_modulos_do_profissional` (menu, 403 e passo 10, CA-ASS-22), `test_plt_12_dados_guardados_ao_descer` (CA-ASS-23), `test_plt_12_downgrade_recusado_com_modulo_aberto` (CA-ASS-24), `test_plt_12_ramo_desliga_modulo`, `test_aut_03_essencial_so_email`. Os testes que hoje trocam `settings.GIRO_MODULOS_ATIVOS` continuam valendo para "entregue".

**Para as outras tarefas:** T-185 usa `pendencias_dos_modulos` em `mudar_plano`, `simular` e `excede` (se fechar antes da T-196, os grupos valem 0). T-186 usa o mesmo na virada do downgrade agendado e põe o `abertos_texto` no e-mail. Frontend: tratar o 403 `PLT-12` mostrando a `mensagem`; nada a calcular.

**Pontos em aberto (backlog, `[decisão]` para o produto):** mudar o ramo sem conferir pendências; Essencial com "só vende" no passo 7; comissão de locação no Essencial; e um ajuste de critério: o CA-ASS-15 passa a listar também as despesas abertas do seed na recusa do Essencial.

**O que ficou de fora:** OpenAPI não mudou (só documentos); as rotas de vendas, manutenção, conciliação e relatórios entram na tabela com os contratos delas.

**Próximo passo:** orquestrador abre o PR. Só documentos, sem teste para rodar. Paro aqui, como pedido: não pego T-194, T-201, T-213 nem T-217 sem nova ordem.

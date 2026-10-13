# T-027 · Importação de veículos e clientes por planilha · backend → frontend, qa, arquiteto, produto

**O que foi feito:** app novo `importacao` (ADR 0017) com todo o contrato `docs/api/importacao.md`: envio da planilha (`.xlsx` ou `.csv`), validação linha a linha numa task com as mensagens da tela `Onboarding-Importar`, "Corrigir aqui" (revalida na hora), ignorar linha, importar até o limite do plano com aviso `IMP-03`, importar de novo as corrigidas e as que ficaram acima do limite, cancelar, lista dos últimos 30 dias, planilha modelo com aba "Instruções" e limpeza diária depois de 30 dias. Caso do seed coberto: 86 linhas → 83 prontas e 3 com erro (linhas 14, 37 e 52, com os textos da tela) → 83 importadas → corrigidas as 3 → 86 veículos.

**Onde:**
- `backend/apps/importacao/` (models, `planilha.py`, `linhas.py`, services, selectors, tasks, api, migração `0001_importacao`, README);
- `backend/apps/veiculos/services.py`: `validar_novo(dados)` e `cadastrar(dados, origem=...)`; `Origem.IMPORTACAO` (migração `0004_origem_importacao`): o histórico do veículo mostra "Importação";
- `backend/apps/clientes/services.py`: `validar_novo(dados)` (inclui e-mail e categoria da CNH, que o serializer conferia);
- `backend/apps/plataforma/services.py`: `vagas_no_plano(item)` (trava o `UsoEmpresa` e diz quantos cabem);
- `backend/comum/arquivos.py`: no S3, `apagar` remove também as versões antigas (arquivo de clientes);
- `config/settings/base.py` (app e Beat `importacao_limpar`, 04:00), `config/urls.py`, `tests/test_limites_entre_apps.py` (nível 13).

**Contrato:** `/api/importacoes/...` (ver `docs/api/openapi.yaml`). Detalhes que o contrato deixava aberto e que o arquiteto deve conferir:
- `plano` vem `null` em importação de clientes (não têm limite); `filial_padrao` também.
- `enviada_por` é o nome da pessoa; para o suporte, "Suporte Giro". A auditoria guarda o atendente com o destaque do `AUD-03`.
- Linha de cliente para o suporte: `dados = {nome, tipo, documento_mascarado, celular}`.
- O suporte lê as importações nos dois modos ("só ver" e "ver e editar"); escrever só com "ver e editar".
- A coluna `tipo` de clientes pode faltar no cabeçalho (o valor vazio já é deduzido pelo documento).
- 409 novos: `linha_fechada` (corrigir ou ignorar linha importada/ignorada) e `importacao_fechada` (corrigir em importação que não está `validada` nem `concluida`); estado inválido para importar ou cancelar: 409 `transicao_importacao`.
- Planilha ilegível ou com entidade XML: 400 `validacao` em `campos.arquivo`; cabeçalho incompleto: 400 `validacao` com `detalhes.colunas_faltando`.
- Aviso no sino: tipo `importacao_concluida`, link `/implantacao`, para quem pediu (ou para os administradores, se foi o suporte).

**Dependências novas (motivo também vai no PR):** `openpyxl` (ler o `.xlsx` em streaming e gerar o modelo) e `defusedxml` (protege o openpyxl de entidades XML e explosão quadrática), as duas previstas no contrato; `types-openpyxl` no dev, para o mypy. A imagem do backend precisa ser reconstruída (`requirements.txt` mudou).

**Regras cobertas:** IMP-02 (`test_imp_02_*`), IMP-03 (`test_imp_03_importa_ate_o_limite_e_avisa`), IMP-05 (`test_imp_05_conclusao_marca_o_passo_audita_e_avisa`), CLI-01/CLI-03 (`test_cli_01_clientes_validados_cifrados_e_incompletos`), AUD-09 (`test_aud_09_suporte_ve_linha_de_cliente_resumida`), AUD-03 (`test_aud_03_importacao_pelo_suporte_audita_ator_suporte`), segurança da revisão T-044 (`test_importacao_xlsx_com_entidades_recusado`, `test_importacao_zip_acima_de_50mb_recusado`, `test_importacao_arquivo_de_clientes_apagado_apos_validar`), isolamento (`test_importacao_isolada_por_empresa`). Tudo em `backend/tests/aceitacao/test_t027_importacao.py`.

**Critérios (`docs/qa/criterios/T-027.md`, PR #165 da T-152):** lidos e seguidos. Por eles: placa ou chassi já cadastrados saem como "Placa X já cadastrada" / "Chassi X já cadastrado"; CPF na empresa sai "CPF já cadastrado", sem dizer de quem; arquivo ilegível depois de aceito vai a `falhou` com a mensagem em `aviso`; o nome do arquivo não entra na auditoria. Uma diferença para o produto olhar: o CA-027-05 dá `validacao` para a placa "AB1234", mas o contrato e o CA-027-01 tratam formato de placa como `VEI-01`; mantive `VEI-01` para os dois casos.

**O que ficou de fora / dúvidas:** duas `[decisão]` no backlog (seção "Levantadas pelo backend em T-027"): a cor (opcional no contrato, obrigatória no cadastro; hoje a linha fica com erro) e a célula longa no `.csv` (hoje recusa o arquivo). Ainda sem teste automático: a corrida com o cadastro pela tela (CA-027-12) e o caso de 64 vagas com a frota já cadastrada (CA-027-11); o código cobre os dois (savepoint por linha e `UsoEmpresa` travado), o qa pode incluir os testes.

**Verificação:** `ruff check`, `ruff format --check`, `mypy` limpos; suíte completa 759 de 760 antes dos últimos ajustes (a falha era a lista de rotas que o suporte lê, atualizada com as 4 rotas de leitura da importação) e depois os testes afetados (T-027, T-011 rotas do suporte, T-013, T-014, campos sensíveis) 88 de 88; OpenAPI regerado sem avisos; no frontend, `api:gerar` e `typecheck` limpos.

**Próximo passo para quem recebe:**
- **frontend:** tela `Onboarding-Importar` no assistente: `POST` multipart, acompanhar `status` (`validando` → `validada`; `importando` → `concluida`) pelo `GET /api/importacoes/{id}/`, lista `?status=com_erro` para "Corrigir aqui" (`PATCH` com só os campos mudados), "Importar os N" com `contagens.prontas`, mostrar `aviso.mensagem` quando vier; o nome do arquivo sai escapado.
- **qa:** comparar com os critérios do produto quando chegarem; o caso 83 + 3 = 86 já está no teste.
- **arquiteto:** conferir os detalhes de contrato acima e registrar em `importacao.md` o que aprovar.

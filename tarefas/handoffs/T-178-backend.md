# T-178 · Despesas no backend: busca, exportar, despesa por veículo e nota obrigatória · backend → frontend, qa

**O que foi feito:** as decisões do dono de 13 out 2026 sobre a tela de Despesas (T-176), pelo contrato da T-177 (PR #187), com as duas decisões do PR #187: o financeiro também exporta e a placa sai com hífen no CSV.

**Onde:**
- **Busca (`FIN-16`):** `Despesa.descricao_busca` (minúsculas e sem acento, NFKD, por `financeiro.models.texto_de_busca`), gravado em `lancar_despesa`, com migração de dados (`financeiro/migrations/0007_despesa_descricao_busca.py`). `selectors.termo_de_busca` e `buscar_despesas`: descrição **ou** placa (`normalizar_placa`, só se o termo não ficar vazio). Muda a lista e as `contagens`; os `indicadores` não mudam com nenhum filtro. Vazio ou só espaços é ignorado; acima de 60 caracteres, 400 no campo `busca`.
- **Despesa por veículo (`FIN-16`):** `veiculos.selectors.frota_ativa_em(dia, filiais)`, pelo último status do `HistoricoStatusVeiculo` até o fim do dia em São Paulo. `financeiro.selectors.despesa_por_veiculo` divide em `Decimal` e arredonda uma vez (`ROUND_HALF_UP`): o dia é o último do mês pedido, ou hoje no mês corrente e num mês futuro. Sem veículo, `null`. As filiais são as do escopo do `X-Filial` (`_filiais_do_escopo`).
- **Exportação (`FIN-16`, `AUD-07`):**
  - `auditoria/exportacao.py`: registro de itens (`registrar_item`, `item_registrado`).
  - `financeiro/exportacao.py`: `validar`, `linhas` e `conteudo` do item `despesas`, registrado em `FinanceiroConfig.ready()`.
  - `auditoria/services.py`: `solicitar`, `gerar` e `conteudo_rotulo` consultam o registro, e o mês vira `periodo_inicio` e `periodo_fim`.
  - Campo novo `Exportacao.parametros` (`auditoria/migrations/0005_exportacao_parametros.py`), item `despesas`, `DISPONIVEIS` com `("despesas", "csv")` e a mensagem nova do 422 `exportacao_indisponivel`.
  - Perfis por item nas views: `POST`, a lista e o `baixar` aceitam o administrador e o financeiro, e o financeiro só com as despesas (a lista dele traz só as de despesas). O token de suporte continua com 403 `PLT-07`.
  - `pode.despesas_exportar` (administrador e financeiro) em `contas`.
- **Lançamento (`FIN-05`, `FIN-06`, `FIN-07`):**
  - `nota` obrigatória no `DespesaEntradaSerializer`, com a mensagem "Envie a foto da nota.".
  - As recusas de perfil vêm antes da validação: 403 `FIN-06` e 403 `FIN-05` ("Seu perfil não paga despesa pelo caixa.", para o vistoriador com `pago_no_caixa`).
  - A mensagem do 422 `FIN-07` agora é "Abra o caixa do dia para pagar por ele".
  - `lancar_despesa` continua aceitando `nota=None`, para a despesa que vai nascer da OS (`MAN-05`).
- **Seed:** as 6 despesas de outubro com uma nota em PDF pequeno (`seed/financeiro.py`).
- **Frontend:** só o falso de `listarDespesas` ganhou `despesa_por_veiculo_centavos: null`, para o `typecheck` passar com o OpenAPI novo.

**Contrato:** `GET/POST /api/financeiro/despesas/`, `POST/GET /api/exportacoes/` e `GET /api/exportacoes/{id}/baixar/` (`docs/api/openapi.yaml` regenerado e conferido com `financeiro.md`, `auditoria.md` e `contas.md`).

**Regras cobertas:** FIN-05, FIN-06, FIN-07, FIN-16, AUD-07. Testes em `backend/tests/aceitacao/test_t178_despesas.py`:
- `test_fin_16_busca_descricao_e_placa` (CA-DES-04, CA-DES-05);
- `test_fin_16_despesa_por_veiculo` (8217, e 6902 no CA-DES-02) e `test_fin_16_despesa_por_veiculo_sem_veiculos` (CA-DES-03);
- `test_fin_16_exportar_despesas_csv` (CA-DES-06, CA-DES-07, CA-DES-09) e `test_fin_16_exportar_despesas_valida_o_pedido` (400, 422 e proteção contra fórmula);
- `test_fin_16_financeiro_exporta_despesas` (CA-DES-06b) e `test_aud_07_despesas_administrador_e_financeiro` (CA-DES-08 e `pode`);
- `test_fin_06_nota_obrigatoria` (CA-DES-15);
- `test_fin_05_pago_no_caixa_sem_caixa_aberto` (CA-DES-12) e `test_fin_05_pago_no_caixa_perfil_e_limite` (CA-DES-11, 13, 14).

No seed, `test_fin_16_despesa_por_veiculo_no_seed` (`test_t019`) confere 8217 e as notas. `make backend-check` limpo (ruff, mypy, migrações); a suíte inteira passa.

**O que ficou de fora:**
- As descrições do seed continuam "Pneus (2)" e "IPVA ROE2A88" (como na T-019); o contrato usa "Pneus (2 unidades)" e "IPVA ROE-2A88" só como exemplo. A busca acha as duas formas.
- O 422 `FIN-07` com o caixa **fechado** usa o mesmo caminho do caixa não aberto (`_caixa_aberto`). O teste cobre o não aberto, porque fechar o caixa no teste pede a conferência inteira.
- O tipo `Pode` escrito à mão em `frontend/src/lib/api/tipos.ts` ainda não tem `despesas_exportar`: fica para a T-179.

**Próximo passo para quem recebe:**
- **Frontend (T-179):** o contrato está implementado. O botão Exportar aparece por `pode.despesas_exportar`, com o corpo `{ itens: ["despesas"], formato: "csv", mes, filial_id | null }`. O indicador vem `null` sem veículo. Sem `nota`, a resposta é 400 `campos.nota`.
- **QA:** CA-DES-01 a 15 com testes no backend. O CSV sai com `;`, BOM e a placa com hífen (PMZ-3E17, QXA-4B21).

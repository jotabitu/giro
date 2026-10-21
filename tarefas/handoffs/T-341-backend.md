# T-341 · Continuar implantação e placa com hífen nos textos · backend → orquestrador, qa, frontend

Branch `t-341-implantacao-placa`, criada da `origin/main`. Contrato `docs/api/configuracoes.md` e `docs/api/README.md` (Convenções), da T-340 (`tarefas/handoffs/T-340-arquiteto.md`).

**O que foi feito:**

- **"Continuar implantação" (`IMP-05`, `PLT-12`):** na `GET /api/configuracoes/`, o `implantacao.acao` segue o `proximo` do assistente:
  - com `proximo`: `{ "rotulo": "Continuar implantação", "destino": "implantacao", "passo": "<proximo>" }`;
  - sem `proximo` e só `primeira_locacao` aberto: `nova_locacao`, como antes;
  - nenhum dos dois: `null`.
  - O `proximo` vem de uma função pura nova, `plataforma.selectors.proximo_do_assistente(feitos, recebe)`. O `andamento_do_assistente` (`GET /api/implantacao/`) também passou a usá-la, então os dois sempre dão o mesmo passo. A Configurações passa os passos que já leu, sem consulta nova; o teto de 11 queries continua coberto por `test_usr_05_configuracoes_no_maximo_11_queries`.
  - Sem `recebimento_parceiro` (Essencial), `recebimentos` sai também de `total` e de `faltam`: "6 de 9", como o contrato pede. Até a T-196 pôr o recurso no enum, todo plano recebe, e o caso só aparece nos testes com o `monkeypatch`, como na T-202.
- **Placa com hífen nos textos (`FIN-16`, convenção da T-340):**
  - **Formatador:** um só, `comum.documentos.placa_com_hifen`. Ele limpa a placa (só letras e dígitos, em maiúsculas) e põe o hífen depois do 3º caractere quando ela tem 7. Fora disso, devolve a placa como veio. O `financeiro.exportacao.placa_com_hifen` saiu, e o CSV das despesas passou a usar o de `comum`.
  - **Onde passa a valer:**
    - o resumo da despesa na aprovação (`financeiro/services.py`, CA-APR-11: "Honda Pop 110i · PMZ-3E17");
    - o `detalhe` do `APR-06` ("SAK-1D39 · 3.500 → 3.400 km · ...");
    - os títulos dos avisos de documento vencendo e vencido (`veiculos`, `AUT-06`);
    - o recibo de devolução (PDF), o `locacao.veiculo` da devolução e as descrições da troca e do combustível no acerto (`vistorias`);
    - o marcador `{{veiculo.placa}}` do contrato (`locacoes/contrato.py`) e o exemplo dele na lista de marcadores ("SAK-1D39");
    - a mensagem "Placa GEN-0001 já cadastrada" da importação.
  - **O que não mudou:** o campo `placa` sozinho continua sem hífen em todas as respostas. Ficaram como estavam o `origem_codigo` do pedido `APR-06` (identificador, não texto) e as mensagens de placa inválida da importação, que mostram o que a pessoa digitou.
  - **Auditoria:** nenhum texto da auditoria monta a placa no código. O "Pneus PMZ-3E17" do teste da T-018 é dado de teste.
- **CA-APR-11:** o xfail estrito de `test_apr_03_ca_apr_11_resumo_dos_pneus_com_placa_pmz_3e17` saiu (`test_t204_decisoes_seed.py`). O PR #372 já estava na main, então não foi preciso acertar nada no merge.

**Onde:** `backend/comum/documentos.py`; `backend/apps/plataforma/selectors.py`; `backend/apps/relatorios/configuracoes.py` e `selectors.py`; `backend/apps/financeiro/services.py` e `exportacao.py`; `backend/apps/veiculos/services.py`; `backend/apps/vistorias/recibo.py`, `selectors.py` e `services.py`; `backend/apps/locacoes/contrato.py`; `backend/apps/contratos/marcadores.py`; `backend/apps/importacao/linhas.py`.

**Contrato:** sem mudança no `docs/api/openapi.yaml` (regenerado com `--validate`, 0 erros, diff vazio). O `AcaoDaImplantacaoSerializer` já tinha o `destino` `implantacao` e o `passo`.

**Regras cobertas:** IMP-05, PLT-12, FIN-16. Testes novos em `backend/tests/aceitacao/test_t341_implantacao_placa.py`:

- `test_imp_05_continuar_implantacao_pelo_proximo` (6 de 10, `passo: "contrato"`, igual ao `proximo` de `GET /api/implantacao/`);
- `test_imp_05_plt_12_essencial_sem_recebimentos` (6 de 9) e `test_imp_05_plt_12_essencial_pula_recebimentos` (`passo: "importar"`);
- `test_imp_05_oito_passos_do_assistente_feitos_vai_a_nova_locacao`, `test_imp_05_so_conta_aberto_fica_sem_botao` e `test_imp_05_textos_da_faixa_com_o_proximo`;
- `test_fin_16_placa_com_hifen`, `test_fin_16_placa_no_contrato_e_no_exemplo_do_marcador` e `test_fin_16_placa_no_texto_da_devolucao`.

Testes ajustados à convenção nova: `test_t181_configuracoes.py` (o caso de 6 de 10 agora tem o botão), `test_t013_veiculos.py`, `test_t016_vistorias.py`, `test_t027_importacao.py`, `test_t081_aprovacoes.py` e `test_t123_decisoes_troca.py`.

**Testes rodados** (num container avulso na rede `giro-backend-teste`, banco `giro`, uma rodada por vez): `ruff check`, `ruff format --check`, `mypy` (397 arquivos), `makemigrations --check` (sem mudança) e o OpenAPI com `--validate` (0 erros, sem diff). Pytest de `test_t341`, `t181`, `t202`, `t013`, `t016`, `t027`, `t081`, `t123`, `t204`, `t090`, `t017`, `t178`, `t018`, `apps/aprovacoes`, `apps/relatorios` e `comum`: 423 passaram e 1 falhou, o teto de 11 queries da Configurações (a leitura do plano). Corrigido com a leitura preguiçosa acima e rodado de novo: `t341`, `t181` e `t202` passam (39).

**O que ficou de fora:** nada do item. **Atenção para a T-196:** quando `recebimento_parceiro` entrar no enum `Recurso`, a Configurações passa a ler o plano da empresa (`plataforma.selectors.empresa_tem_recebimentos`), e isso é 1 consulta a mais. Hoje ela não acontece porque o recurso não existe. Nessa hora, carregar o plano junto com a empresa (ou devolvê-lo do `assinatura()`) para continuar em 11; o `test_usr_05_configuracoes_no_maximo_11_queries` pega a diferença. O frontend não muda: a Configurações já leva `acao.destino` à rota, e a casca tem `/implantacao/[passo]`.

**Próximo passo para quem recebe:**

- **QA:** conferir o CA-APR-11 com `PMZ-3E17` e o "Continuar implantação" levando a `/implantacao/contrato` no exemplo de 6 de 10.
- **Frontend:** nada a fazer. Conferi: o `placa()` de `src/lib/formatos.ts` só é aplicado ao campo `placa` sozinho, nunca a um texto já pronto da API, então o hífen não sai duplicado.

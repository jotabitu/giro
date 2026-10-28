# T-377 · Textos do downgrade recusado (T-391) e downgrade da fase 1 sem conferir comissão · backend → orquestrador, qa, arquiteto

Branch `t-377-comissao-fase-1`, criada da `origin/main` e com o merge da `origin/main` (d310fc1, com o #422 e o #423).

**Escopo:** pela decisão do dono de 28 out, a parte (a) da tarefa saiu. A comissão de locação continua nascendo como hoje (`FIN-09`, `lancar_comissao` sem mudança), e na fase 2 o trabalho continua dela. Ficaram os textos da T-391 e a conferência do downgrade.

**O que foi feito:**

- **Downgrade da fase 1 só confere as despesas (`PLT-12`, decisão de 25 out, T-356).** Antes, uma comissão de locação a pagar recusava a mudança do Profissional para o Essencial com 422 "1 comissão a pagar". Isso foi conferido com um teste contra a main antes da correção.
  - `excede_no_plano` filtra os abertos por `GRUPOS_DO_DOWNGRADE` (`despesas_aguardando_aprovacao` e `despesas_a_pagar`). OS, vendas e comissões entram quando os módulos existirem.
  - Vale para os quatro caminhos que usam `excede_no_plano`: simular e mudar de plano, o `excede` de `planos/`, a alternativa do Essencial e a conferência do downgrade agendado na geração da fatura.
  - **A troca de ramo não muda.** "Deixar de vender" continua contando as comissões a pagar (`empresas.md`). Ela usa `pendencias_dos_modulos` direto, sem passar pelo filtro.
- **E-mail do downgrade agendado que não aconteceu (CA-ASS-71, itens 1 a 5 do `T-391-produto.md`):**
  1. `texto_do_que_excede` traz só os limites e os abertos ("4 de 3 usuários"), sem "a empresa só vende".
  2. A 1ª linha sai de `motivo_do_downgrade_recusado`: com a lista, "...mas o uso de hoje não cabe nele: {lista}."; só com a atividade, "...mas o plano {plano} não inclui vendas, e a empresa hoje só vende. Para mudar, ela precisa alugar."; com os dois, a frase da lista seguida de "Além disso, ...".
  3. A abertura passou a ser "A empresa {nome} ia mudar".
  4. A última frase passou a ser "Para mudar, resolva o que está acima e escolha o plano de novo em Assinatura."
  5. Teste `test_plt_04_email_do_downgrade_recusado`, com os três casos (fixture "Pedal Norte").

**Onde:** `backend/apps/plataforma/services.py` (`GRUPOS_DO_DOWNGRADE`, `excede_no_plano`, `texto_do_que_excede`, `motivo_do_downgrade_recusado`), `backend/apps/plataforma/tasks.py` (`plataforma_avisar_downgrade_recusado`).

**Regras cobertas:** PLT-04, PLT-12. Testes novos:
- `test_plt_12_fase_1_downgrade_nao_confere_comissao` (`test_t196_modulos_por_plano.py`);
- `test_plt_04_email_do_downgrade_recusado[os_dois|so_a_atividade|limite_e_aberto]` (`test_t186b_faturas_cobranca.py`).

**Testes rodados** (num contêiner avulso na rede `giro-backend-teste`, banco próprio `giro_b2`, um por vez):
- `ruff format`, `ruff check` e `mypy` (410 arquivos): sem erro.
- `test_t196`, `test_t186b` e `test_t262` (ramo): 43 passaram.
- Rodada completa com `--create-db`, depois do merge da main: 1454 passaram, 6 xfail e 1 falhou. O `-x` parou nessa falha, então os arquivos depois do `test_t265` rodaram de novo à parte: 479 passaram e a mesma falhou.
- **A falha não é da T-377:** `test_adr_0026_filho_so_com_path_e_lang_e_os_limites` (`test_t265_leitura_crlv.py`).
  - Sozinho, ele passa. Junto com o `test_t270_sentry.py`, ele falha. Isso foi reproduzido: 1 falhou e 5 passaram.
  - O t270 liga o Sentry, e o sentry-sdk 2.73.0 da imagem passa a pôr `SUBPROCESS_BAGGAGE` e `SUBPROCESS_SENTRY_TRACE` no ambiente de todo `Popen`. Assim, o filho da leitura do CRLV-e não sai só com `LANG` e `PATH`.
  - O pytest-django joga os testes sem banco para o fim, e por isso esse teste roda depois do t270 em qualquer rodada completa.
  - Nenhum dos dois arquivos mudou nesta branch. O conserto (o t270 desligar o Sentry no fim, ou o `executar` montar o ambiente sem passar pelo patch) fica com o orquestrador, para ver a quem passar. A ADR 0026 (M-01) é da segurança.

**Para o Arquiteto:** em `docs/api/assinatura.md` (422 `PLT-04`), a lista de grupos ainda diz que `ordens_servico`, `vendas` e `comissoes` vêm no downgrade. Na fase 1, só as despesas vêm. Não mudei o contrato. Vale uma linha "na fase 1, só as despesas (`PLT-12`)".

**Para o QA:** o CA-ASS-71 já pode ser conferido pelo e-mail. Na fase 1, uma comissão a pagar não segura mais o downgrade.

**OpenAPI:** nenhum serializer mudou, e o `detalhes` da 422 tem o mesmo formato.

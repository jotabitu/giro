# T-066 · Textos revisados da T-010 · backend → frontend, qa, orquestrador

**O que foi feito:** troquei os textos pela tabela de `tarefas/handoffs/T-059-produto.md`. Os assuntos dos e-mails e a faixa de `inadimplente` continuam iguais, como a tabela pede.
- `faixa_aviso` de `suspensa`: "Sua empresa está suspensa. Você pode ver e exportar os dados, mas não criar locações, vendas nem cobranças. Ao pagar, o acesso volta na hora."
- `faixa_aviso` de `pausada`: "Sua empresa está pausada. Você pode ver os dados. Para voltar a operar, retome a assinatura."
- Corpo do e-mail de 90% do limite: "Sua empresa usa {usado} de {limite} {item} do plano. Ao chegar a {limite}, não dá para cadastrar mais {item}, e o que já está cadastrado continua funcionando. Para aumentar o limite, mude de plano em Assinatura."
- Corpo do e-mail de convite: "Olá, {nome}. A {marca} convidou você para acessar o sistema." As linhas do link e da validade de 7 dias não mudaram.

**Onde:** `backend/apps/plataforma/selectors.py` (`FAIXA_AVISO`), `backend/apps/plataforma/tasks.py`, `backend/apps/contas/tasks.py` e `backend/tests/aceitacao/test_t010_plataforma.py`.

**Contrato:** sem mudança. `faixa_aviso` continua um texto pronto da API, e o OpenAPI gerado é igual ao `docs/api/openapi.yaml`.

**Regras e testes:** PLT-02 e PLT-03 (faixa e e-mail de limite) e USR-01 (convite). Agora três testes conferem os textos exatos:
- `test_plt_03_ca_010_11_empresa_sem_operacao_fica_so_leitura`: `faixa_aviso` de `suspensa` e `pausada`; `cancelada` sem faixa.
- `test_plt_03_ca_010_07_aviso_em_90_por_cento`: o corpo do e-mail, com 135 de 150 veículos.
- `test_plt_01_ca_010_02_moto_rapida_nasce_em_teste`: o assunto e o corpo do convite da Mariana.

**Check:** ruff check, ruff format --check e mypy limpos. O pytest dá `280 passed, 71 xfailed`. Rodei no Postgres descartável (porta 55432), como na T-058, e o removi no fim.

**O que ficou de fora:** nada da T-066. O EscopoDeFilial com o financeiro vai para a T-011, como decidido pelo Orquestrador.

**Próximo passo para quem recebe:** o frontend só exibe `faixa_aviso`. Se houver texto fixo de faixa em algum dado falso, troque pelo texto acima. O qa pode usar os textos exatos nos testes ponta a ponta.

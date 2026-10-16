# T-185 (parte 1) · Rotas da assinatura: GET completo, planos, mudança de plano e dados fiscais · backend → orquestrador, frontend (T-187), qa (T-204, T-215), segurança, arquiteto

Corte aprovado pelo orquestrador em 15 out 2026: a T-185 sai em dois PRs. Esta é a parte 1 (branch `t-185-rotas-assinatura`, a partir da `origin/main`). A parte 2, forma de pagamento e faturas, vem na `t-185b-forma-faturas`, empilhada sobre esta.

**O que foi feito:**

- **`GET /api/assinatura/`** com os campos novos do contrato: `plano.id`, `teste.inicio`, `proxima_fatura` (a mensalidade em aberto mais antiga, ou a que nasce depois do último período pago; nula na `pausada`, na `cancelada` e com o cancelamento marcado), `plano_proximo` (downgrade ou ciclo da equipe agendados, com `vale_em`) e, só para o administrador, `forma_pagamento` (situação na ordem do contrato, `cartao` só com bandeira e final, `prazo` só em teste sem forma), `dados_fiscais`, `oferta` (cartão "Precisa de mais veículos ou filiais?") e `acoes`. Para os outros perfis esses quatro blocos ficam fora da resposta. O suporte lê os blocos com todas as `acoes` em `false`.
- **Catálogo da `PLT-11`** em `plataforma/catalogo.py`: `inclui` (Comparar planos) e `a_mais` (o cartão do plano acima), com teste que confere a tabela da regra e que nenhum texto cita NF-e, domínio, portal, API ou integrações.
- **`GET /api/assinatura/planos/`**: planos ativos e o atual mesmo desativado (`PLT-05`), preço de tabela, `itens`, `mudanca`, `cabe` e `excede` (Moto Rápida no Essencial: 86 de 30 veículos, 5 de 3 usuários; a filial cabe e não aparece).
- **Mudança de plano** (`PLT-04`, `PLT-05`), serviço único `plataforma.services.mudar_plano(empresa, plano, ciclo, por, motivo)`, que trava a `Empresa` e o `UsoEmpresa`:
  - no teste com a 1ª fatura em aberto, vale na hora e sem cobrança: a FAT-0001 passa ao valor novo, e a cobrança já emitida no parceiro é cancelada para sair de novo (CA-ASS-13);
  - upgrade com período pago: vale na hora, com fatura avulsa `diferenca_plano` que vence em 3 dias (CA-ASS-14: R$ 304,84, 04 nov; no teste com a 1ª paga, R$ 450,00 vencendo em 22 out). As mensalidades em aberto de períodos que ainda não começaram passam ao valor novo. Um upgrade desfaz o downgrade agendado;
  - downgrade: só se couber; agendado em `plano_proximo`, e a fatura da virada já gerada sai pelo plano menor (CA-ASS-16);
  - `por=POR_EQUIPE` com outro ciclo: `plano_proximo` e `ciclo_proximo`, valendo na próxima fatura, com auditoria `empresa.mudar_ciclo` e o motivo. Não tem rota no MVP: chame o serviço (Django Admin ou ação da plataforma, fase 2).
  - `POST mudanca-plano/simular/` não grava; `POST mudanca-plano/` exige `confirmar_valor_centavos` (409 `valor_mudou` com a diferença de agora); `DELETE mudanca-plano/` desfaz até a véspera, e a fatura da virada volta ao plano de hoje.
  - Recusas: 409 "Pague a fatura em atraso antes de mudar de plano." na `inadimplente` e na `suspensa`; 409 "Desfaça o cancelamento antes de mudar de plano." com o cancelamento marcado (`acesso_ate` preenchido); 409 da segunda mudança agendada; 422 `mudanca_ciclo`, `mesmo_plano` e `PLT-04`; 404 de plano inativo que não é o atual.
- **`PATCH /api/assinatura/dados-fiscais/`** (`PLT-15`): razão social, endereço (o bloco inteiro; `null` dá 400) e e-mail de cobrança; CNPJ dá 400 "O CNPJ não muda por aqui. Fale com o suporte."; a filial não muda (CA-ASS-48). Atualiza o pagador na conta principal depois do commit (tarefa `plataforma_atualizar_pagador`, só se ele já existe) e pede as notas que esperavam o endereço.
- **Auditoria nos dois lugares** (`empresa.mudar_plano`, `empresa.mudar_ciclo`, `empresa.desfazer_mudanca_plano`, `empresa.dados_fiscais`, também na cópia do endereço da matriz): no `public`, a razão social, o nome, o endereço, o e-mail de cobrança e os dados do responsável vão como `{"alterado": true}` (`AUD-08`, `auditoria.md`). Para isso, `comum.classificacao` ganhou a chave `omitir_no_public`, e o endereço da `Empresa` deixou de ser omitido no schema da empresa.
- **Requisitos da segurança para a T-185** (revisão da T-189), com teste:
  1. suporte: toda rota de escrita com `suporte_proibido` e a mensagem do contrato (`mensagem_suporte_proibido`), testado nos dois modos, sem mudança no banco nem no parceiro;
  2. exceção da `suspensa`: `EmpresaOperando` aceita escrita só na view que declara `escreve_na_suspensa` (por método), sem usar a lista `EXCECOES`; o teste confere que a lista de rotas é exatamente `PATCH dados-fiscais/` nesta parte, e que `pausada` e `cancelada` seguem com 403. A `recusa_na_suspensa` dá o 409 da `PLT-04` em vez do 403;
  3. só o administrador em todas as rotas novas (403 `permissao`, "Só o administrador mexe na assinatura"), com teste por perfil, e os blocos ausentes do `GET` para os outros perfis.

**Onde:** `backend/apps/plataforma/{catalogo,services,selectors,tasks}.py`, `backend/apps/plataforma/api/{assinatura,serializers,urls,views}.py`, `backend/comum/{permissoes,autenticacao,classificacao,auditoria,documentos}.py`, `backend/apps/plataforma/models.py` (`CAMPOS_AUDITORIA`, sem migração), `backend/config/settings/base.py` (nomes de enum do OpenAPI). Testes: `backend/tests/aceitacao/test_t185_assinatura.py` (42). Frontend: os dois falsos da assinatura ganharam `plano.id`, `teste.inicio`, `proxima_fatura` e `plano_proximo`, para o typecheck com o contrato novo.

**Contrato:** `docs/api/assinatura.md`; OpenAPI regenerado em `docs/api/openapi.yaml`.

**Regras cobertas:** PLT-01, PLT-04, PLT-05, PLT-07, PLT-11, PLT-13, PLT-15, AUD-08 (testes `test_plt_04_upgrade_em_teste`, `test_plt_04_upgrade_proporcional`, `test_plt_04_upgrade_no_teste_com_primeira_paga`, `test_plt_04_downgrade_nao_cabe`, `test_plt_04_downgrade_agendado_e_desfeito`, `test_plt_06_mudar_de_plano_com_cancelamento_marcado`, `test_plt_11_*`, `test_plt_15_*`, `test_aud_08_*`, `test_plt_07_ca_ass_19_*`, `test_plt_13_ca_ass_27_*`). Isolamento: `test_plt_04_mudanca_de_plano_isolada_por_empresa`.

**O que ficou de fora:**

- **Parte 2** (`t-185b-forma-faturas`): `PUT forma-pagamento/`, `GET faturas/`, `GET faturas/{codigo}/`, `POST faturas/{codigo}/pagar/` e os requisitos 4 a 8 da segurança. Até lá, `acoes.escolher_forma_pagamento` já vem `true` como o contrato manda, mas a rota ainda não existe. A cobrança da diferença do upgrade no cartão guardado, na hora, também entra na parte 2; nesta parte a fatura nasce `aberta` e a emissão é da `gerar_faturas` (T-186).
- **T-195:** `acoes.cancelar`, `desfazer_cancelamento`, `pausar`, `voltar_pausa`, `desistir_pausa` e os blocos `cancelamento` e `pausa`. Aqui, "cancelamento marcado" é `acesso_ate` preenchido com a empresa ainda não `cancelada`; a T-195 confirma.
- **T-196:** `pendencias_dos_modulos` devolve vazio; os `abertos` do CA-ASS-15 e o CA-ASS-24 (`test_plt_12_downgrade_recusado_com_modulo_aberto`) e o ramo `atividade` (CA-ASS-52) ficam com ela.
- **T-186:** a conferência do downgrade na geração da fatura e a virada no dia do vencimento (`aplicar_mudanca_agendada`, CA-ASS-40 e 41). Até ela existir, o plano agendado não vira sozinho.
- Os testes desta parte montam os estados `ativa`, `inadimplente`, `suspensa` e a fatura `paga` direto no banco, porque as transições e a baixa pela régua são da T-186.

**Pontos para confirmar:**

- **Produto:** o rótulo da forma "cartão" no anual. O contrato só dá "Cartão Visa final 4242 · cobrança automática todo mês"; no ciclo anual a API diz "todo ano". Se o produto preferir outro texto, muda em `selectors._situacao_do_cartao`.
- **Arquiteto:** a mensagem do 409 `valor_mudou` ("O valor da mudança mudou. Confira antes de confirmar.") e a do desfazer no dia da virada ("A mudança para o plano X já vale desde 22 nov.") não estão no contrato; usei estas. O 404 de "nada agendado" usa `nao_encontrado`.

**Próximo passo para quem recebe:**

- **Frontend (T-187):** pode ligar Mudar e Comparar planos, o cartão da `oferta`, o desfazer do downgrade e os dados fiscais. Forma de pagamento e faturas esperam a parte 2. A tela mostra só as `acoes` que vierem `true`.
- **QA (T-204, T-215):** CA-ASS-01, 13, 14, 15 (sem os `abertos`), 16, 17, 18, 19 (mudar plano e dados fiscais), 20, 21, 27 (dados fiscais), 29 (sem a nota), 48, 56 e 58 têm teste aqui.
- **Segurança:** os requisitos 1 a 3 da seção "Para a T-185" estão nesta parte; os 4 a 8, na parte 2.

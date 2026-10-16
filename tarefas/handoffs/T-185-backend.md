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

---

# T-185 (parte 2) · Forma de pagamento e faturas · backend → orquestrador, frontend (T-187), qa (T-204, T-215), segurança, arquiteto, backend (T-186)

Branch `t-185b-forma-faturas`, empilhada sobre a parte 1 (PR #289).

**O que foi feito:**

- **`PUT /api/assinatura/forma-pagamento/`** (`PLT-13`, ADR 0023), sem campo de cartão. Boleto: grava e vale. Pix automático: cria o pagador e a autorização recorrente na conta principal (frequência do ciclo, valor = preço contratado, a partir da próxima fatura) e devolve `proximo_passo` `autorizar_pix` com o copia e cola e `expira_em` (24 h, a validade do QR no parceiro). Cartão: grava a forma; com fatura atrasada, ou aberta já emitida, devolve `pagina_parceiro` com a página da fatura. A forma não muda o estado da empresa (CA-ASS-02). A troca cancela a autorização do Pix, esquece o token, a bandeira e o final do cartão na linha travada, e cancela no parceiro a cobrança viva de outra forma (se o parceiro diz que já foi paga, nada é cancelado). Parceiro fora: 503, nada gravado. Auditoria `assinatura.forma_pagamento` nos dois lugares, só com a forma antiga e a nova.
- **`GET /api/assinatura/faturas/`**: 25 por página, da mais nova para a mais antiga, `?status=`; a linha do teste no fim da última página, sem filtro (`teste_ativo` ou `teste_concluido`); `situacao` na ordem do contrato e `acoes` (`pagar` pela tabela de estados e pela forma; o suporte lê com `pagar` desligado).
- **`GET /api/assinatura/faturas/{codigo}/`**: a linha, mais `cobranca` (o que a tela precisa para pagar), `recibo_url` (gravado na baixa pelo webhook) e `nota_fiscal` (nula com a emissão desligada).
- **`POST /api/assinatura/faturas/{codigo}/pagar/`**: sem `meio`, pela forma (cartão: página do parceiro; Pix automático: Pix avulso; boleto); com `meio`, por outro meio sem trocar a forma. Mesma cobrança viva no mesmo meio (não cria duas); em outro meio, cancela a antiga antes. 409 `fatura_nao_pagavel`, 422 `sem_forma_pagamento`, 404 de fatura de fora.
- **Modelo:** na `FaturaAssinatura`, `cobranca_tipo`, `cobranca_pix_copia_e_cola`, `cobranca_linha_digitavel`, `cobranca_boleto_url`, `cobranca_url_pagina` e `recibo_url` (migração `plataforma.0010`), omitidos da auditoria. `SituacaoCobranca.recibo_url` na interface de pagamentos (Asaas: `transactionReceiptUrl`; falso: um link fixo).
- **Requisitos 4 a 8 da segurança** (T-189), com teste: 4, a forma só com `bandeira` e `final` (serializer com campos listados); 5, trocar de forma apaga o token e um aviso atrasado não regrava o cartão; 6, `pagar/` com `meio` não grava a forma; 7, faturas sempre filtradas pela empresa da requisição, com duas empresas com a FAT-0001; 8, linha digitável, Pix e página do parceiro nunca na auditoria, nos dois schemas. A lista `escreve_na_suspensa` agora é exatamente `PATCH dados-fiscais/`, `PUT forma-pagamento/` e `POST faturas/{codigo}/pagar/`.
- **T-290 (Produto):** o 409 `valor_mudou` diz "O valor da diferença mudou. Confira o novo valor antes de confirmar."; o cartão no anual já dizia "todo ano".

**Onde:** `backend/apps/plataforma/{models,services,selectors}.py`, `migrations/0010_cobranca_da_fatura.py`, `api/{assinatura,urls}.py`, `backend/integracoes/pagamentos/{base,asaas,falso}.py`, `backend/config/settings/base.py` (nomes de enum). Testes: `backend/tests/aceitacao/test_t185b_forma_faturas.py` (21).

**Contrato:** `docs/api/assinatura.md`; OpenAPI regenerado.

**Regras cobertas:** PLT-02, PLT-07, PLT-13, PLT-14 (testes `test_plt_13_*`, `test_plt_14_*`, `test_plt_02_situacao_*`, `test_adr_0023_trocar_de_forma_apaga_o_token`, `test_plt_07_ca_ass_19_suporte_nao_paga_nem_troca_a_forma`).

**O que ficou de fora:**

- **Pix automático autorizado:** nenhum código ainda escuta o aviso de autorização da conta principal; a forma fica `aguardando_autorizacao` até isso existir. Vai junto da emissão pela autorização na T-186 (ou numa tarefa nova, se o Orquestrador preferir). `primeira_cobranca_centavos` vai 0: a confirmar no sandbox do Asaas.
- **Diferença do upgrade no cartão guardado, na hora:** ninguém chama `cobrar_cartao_salvo` ainda, e decifrar o token tem de passar pela porta de `integracoes/pagamentos` (ADR 0023). Fica com a T-186, que cobra o cartão no vencimento pelo mesmo caminho; até lá a fatura da diferença nasce `aberta` e é emitida com as outras.
- Cancelar e pausar (T-195), módulos (T-196), régua e virada (T-186), NFS-e (T-197).

**Pontos para confirmar:**

- **Arquiteto:** os campos novos da `FaturaAssinatura` não estão em `modelo-de-dados.md` (o contrato pede `cobranca` e `recibo_url` no detalhe, e não havia onde guardá-los). Peço que entrem no modelo.

**Próximo passo para quem recebe:**

- **Frontend (T-187):** forma de pagamento (QR do Pix pelo copia e cola, página do cartão com volta à tela, boleto), tabela de faturas com "Pagar" (Pix ou boleto depois da 2ª recusa, com `meio`) e o recibo.
- **QA:** CA-ASS-02, 11, 12 (a situação), 19, 26, 27 e 28 têm teste aqui.
- **Backend (T-186):** a emissão 5 dias antes deve gravar a cobrança pelos campos novos (`_emitir_cobranca` já faz para o "Pagar") e a baixa já grava o `recibo_url`.

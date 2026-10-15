# T-224 · ADR 0024 e contratos pelas decisões da T-223 · arquiteto → orquestrador, backend (T-196, T-185, T-186), frontend, design-system, produto, qa

**Branch:** `t-224-adr-modulos-decisoes`, **empilhada** sobre `origin/t-223-regras-modulos-plano` (PR #224, ainda não mesclado), porque cita a `PLT-12` e a `FIN-09` revistas lá. Mesclar o #224 antes deste; depois, o PR desta aponta para a `main` sem conflito esperado (só documentos, arquivos diferentes dos da T-223, fora `tarefas/`).

**O que foi feito:** a ADR 0024 revista (status "revista em 15 out 2026") e os contratos que ela toca, pelas três decisões do dono (T-223).

- **Troca de ramo confere o que está aberto (item 9, CA-ASS-50).** `empresas.services.mudar_ramo(atividade, trabalha_com, por)` é o único caminho (passo 7 e Configurações). Recursos que saem = `recursos_da_empresa()` menos `recursos_para(plano atual, atividade nova)`; `pendencias_dos_modulos(None, ...)` conta no schema corrente; com algo aberto, 422 `PLT-12` com `detalhes.motivo: "abertos"`, `abertos` e `abertos_texto`, no formato do downgrade. Grupo novo `locacoes` (`locacoes_vistoria`, registrado por `locacoes`: `aguardando_retirada`, `ativa`, `devolucao_atrasada`; "1 locação aberta"). Substitui o padrão antigo, que desligava sem conferir. Janela entre contar e gravar aceita (dado fica guardado e volta com o ramo), como no downgrade.
- **Ramo aceito pelo plano (item 10, CA-ASS-51 e 52).** `plataforma.selectors.atividades_aceitas(plano)`: atividades com pelo menos um módulo de operação; Essencial = `aluga`, `ambos`. `GET /api/ramo/` devolve `atividades` (com `aviso` "Vendas faz parte do plano Profissional." em "vende" quando o plano não liga vendas), `atividades_aceitas`, `tipos` e `modulos` por atividade aceita (nomes de `Recurso.label`, bloco "Módulos que vamos ligar"). `PUT` fora da lista: 422 `PLT-12`, `motivo: "plano"`. No downgrade, atividade não aceita no plano novo: 422 `PLT-04` "O plano Essencial não inclui vendas. Para mudar, sua empresa precisa alugar." com `detalhes.atividade`; também em `excede.atividade` de `planos/` e na virada do downgrade agendado.
- **Comissão de locação (item 11, CA-ASS-53).** Criada só se `tem_recurso("vendas_comissoes")` na confirmação da locação; ativação, pagamento e estorno só mexem em comissão existente. Locação confirmada antes do upgrade nunca ganha comissão.
- **CA-ASS-15:** exemplo do 422 com limites e `abertos` do seed (1 despesa aguardando aprovação, 2 a pagar), e o mesmo em `excede` de `planos/`.
- **Função pura** `plataforma.selectors.recursos_para(plano, atividade)`, base de `recursos_da_empresa`, do downgrade e da troca de ramo.

**Onde:** `docs/decisoes/0024-modulos-por-plano.md` (itens 2, 7, 9, 10, 11 e consequências), `docs/api/empresas.md` (seção nova "Ramo da empresa", interface interna), `docs/api/assinatura.md` (`planos/`, 422 do CA-ASS-15, 422 de quem só vende, testes, tabela de erros), `docs/api/plataforma.md` ("Módulos por plano" e interface interna), `docs/api/locacoes.md` (comissão).

**Regras cobertas:** PLT-12 (os três itens novos), PLT-04, FIN-09, etapa 7 da implantação. Critérios CA-ASS-15, 50 a 53.

**O que muda para a T-196 (backend):**
1. `recursos_para`, `atividades_aceitas`; `recursos_da_empresa` passa a usar `recursos_para`.
2. `empresas.services.mudar_ramo` e as rotas `GET`/`PUT /api/ramo/` (administrador; suporte só lê), com `registrar_passo_implantacao("ramo")` e auditoria `empresa.mudar_ramo`.
3. `pendencias_dos_modulos` aceita `empresa=None`; `locacoes` registra o grupo `locacoes`.
4. `mudar_plano` (pedido, simular, `excede`) e `gerar_faturas` conferem a atividade com `atividades_aceitas(plano_novo)`.
5. Assinante da comissão de locação (`financeiro`, quando as comissões existirem) cria só com o recurso; os passos seguintes nunca criam.
6. Testes: `test_plt_12_troca_de_ramo_com_algo_aberto`, `test_plt_12_essencial_sem_so_vende`, `test_plt_12_downgrade_so_vende`, `test_plt_12_comissao_so_depois_do_upgrade` (este quando houver comissões; até lá, conferir que nada nasce no Essencial) e o `test_plt_04_downgrade_nao_cabe` com os `abertos` do seed.

**Para as outras tarefas:** T-185 e T-186 recebem a conferência da atividade no downgrade (mesma 422 `PLT-04`). Frontend do `Onboarding-Ramo`: os dois botões seguem `atividades_aceitas` (no Essencial, "Locação" não desliga), o `aviso` aparece em "vende", "Módulos que vamos ligar" mostra `modulos[combinação]`; a recusa mostra a `mensagem`. Nada a calcular.

**Pontos em aberto (backlog):**
- Design-system: a troca do ramo em Configurações não tem tela nem cartão; a rota já está pronta.
- Produto: (1) o texto da recusa de "só vende" no `PUT` do Essencial é meu ("O plano Essencial não inclui vendas. Escolha locação, ou locação e venda."); (2) o CA-ASS-50 diz "1 comissão não paga", e o texto do grupo já contratado é "1 comissão a pagar".

**O que ficou de fora:** OpenAPI não mudou (só documentos). `modelo-de-dados.md` não muda: `ConfiguracaoEmpresa.atividade` e `trabalha_com` já estavam lá.

**Próximo passo:** orquestrador abre o PR (base `t-223-regras-modulos-plano`, ou `main` depois do #224). Só documentos, sem teste para rodar.

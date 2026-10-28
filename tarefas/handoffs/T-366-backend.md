# T-366 · Rota de recebimentos e marcação dos passos · backend → frontend, qa, seguranca

**O que foi feito:**
- `GET` e `POST /api/recebimentos/`, pelo contrato da T-358 (`plataforma.md`, "Recebimentos da empresa"), com os quatro achados da T-384 que eram desta tarefa:
  - **M-01:** `conectar_recebimentos` trava a `Empresa` no `public` (`select_for_update`) antes do `exists()` e só solta depois do `save`, com o parceiro no meio. Dois envios ao mesmo tempo criam uma subconta só, e o outro recebe 409 `recebimentos_conectados`. Se o `save` falhar depois de o parceiro criar a subconta, o log leva só a empresa e o `conta_externa_id`, nunca a chave, e o erro original sobe.
  - **B-01:** o `GET` em `pendente` chama `consultar_recebimentos`, que pega a trava do minuto com `cache.add` por empresa. Quem não pega, ou acha o parceiro fora do ar, responde a situação gravada. `atualizar_recebimentos` relê a conta com `select_for_update` antes de transicionar: se outra consulta já transicionou, devolve a situação nova, sem 409.
  - **B-02:** o corpo vai só ao parceiro e não entra no evento `conta_pagamento.criar` nem no log (o teste confere com `caplog`). O limite é de 10 envios por hora por empresa (`RecebimentosPorEmpresa`, escopo `recebimentos_empresa`), com 429 `muitas_requisicoes`. A leitura não conta.
  - **B-03:** a `sugestao` usa o e-mail e o celular do administrador logado (`request.user`).
- Textos de `situacao`, `rotulo` e `mensagem` iguais aos do contrato, e `acoes.conectar` só em `desconectado`.
- Recusas:
  - outros perfis: 403 `permissao`;
  - suporte nos dois modos: 403 `PLT-07`, pelo `suporte_proibido`;
  - Essencial: 403 `PLT-12`, com `detalhes: { recurso: "recebimento_parceiro", motivo: "plano" }`, antes da conferência de perfil.
- `tipo_empresa` entra com a lista do parceiro (`MEI`, `LIMITED`, `INDIVIDUAL`, `ASSOCIATION`), e a view traduz para as chaves internas do serviço.
- Marcação dos passos (`IMP-07`):
  - **`precos`:** `_gravar_preco` marca quando o preço já vale hoje, a categoria está ativa e diária, semanal ou mensal é maior que zero; só a caução não conta. O preço agendado marca na primeira leitura de `GET /api/implantacao/` ou de `GET /api/configuracoes/` na data, por `plataforma.services.conferir_passos_na_leitura`, com a conferência `veiculos.selectors.tem_preco_vigente` registrada no `ready()`. Não há tarefa agendada.
  - **`equipe`:** o primeiro convite pelo `convidar`. O `convidar_administrador` da compra passa `marca_equipe=False`.
  - **`filial`:** só quando a filial nasce matriz.
  - **`recebimentos`:** sai do `conectar_recebimentos` e vai para a transição `pendente → aprovada`.

**Onde:**
- `backend/apps/plataforma/api/recebimentos.py` (novo), `apps/plataforma/api/urls.py` e `apps/plataforma/services.py`: `conectar_recebimentos`, `atualizar_recebimentos`, `consultar_recebimentos` e os registros `registrar_conferencia_de_passo` e `registrar_endereco_da_matriz`.
- `apps/plataforma/api/assinatura.py` (`ImplantacaoView`) e `apps/relatorios/api/views.py` (`ConfiguracoesView`): a conferência na leitura.
- `apps/veiculos/{services,selectors,apps}.py`, `apps/contas/services.py` e `apps/filiais/{services,selectors,apps}.py`.
- `comum/limites.py` e `config/settings/base.py` (o limite).
- `docs/api/plataforma.md`: só a coluna "Situação no código" da tabela da `IMP-07`. O OpenAPI foi regenerado.

**Contrato:** `GET` e `POST /api/recebimentos/` (ver `docs/api/openapi.yaml`).

**Regras cobertas:** `FIN-04`, `IMP-07`, `PLT-07`, `PLT-12`. Os testes estão em `backend/tests/aceitacao/test_t366_recebimentos.py`:
- `test_fin_04_*`, inclusive `test_fin_04_conectar_em_paralelo_cria_uma_subconta`, com duas conexões reais e o parceiro de mentira contando as chamadas;
- `test_plt_12_recebimentos_essencial_403` e `test_plt_07_recebimentos_recusa_suporte`;
- `test_imp_07_*`: os seis do contrato e mais três.

O `test_fin_04_t029_conectar_recebimentos_guarda_a_chave_cifrada` passou a conferir que o passo **não** fica marcado ao conectar.

**O que ficou de fora:**
- **Dependência da T-196:** na `main`, `recebimento_parceiro` ainda não está no enum `Recurso`, e `empresa_tem_recebimentos` devolve `True` para todo plano. Por isso o 403 `PLT-12` só vale de verdade depois da T-196, e o teste do Essencial troca `assistente_tem_recebimentos`, como o `test_imp_05_andamento_sem_recebimentos_tem_7_passos` já faz. A view já declara `recurso_do_plano = "recebimento_parceiro"`: com a T-196 na `main`, o `ModuloDoPlano` dela recusa antes, e a permissão `ComRecebimentoPeloParceiro` desta tarefa fica redundante, mas sem conflito. Quem mesclar a segunda das duas pode tirá-la.
- **Suporte no Essencial:** recebe `PLT-07`, e não `PLT-12`, porque a recusa do suporte acontece na autenticação, antes das permissões. As duas são 403.
- **Novo pedido depois da recusa:** fica com a equipe Giro (contrato).

**Próximo passo para quem recebe:**
- **Frontend (T-364):** o passo Recebimentos usa `GET` e `POST /api/recebimentos/`. Rode `npm run api:gerar`. Os erros do `POST`:
  - 400 com `campos`;
  - 409 `recebimentos_conectados`;
  - 422 `parceiro_recusou`, com a mensagem do parceiro;
  - 429;
  - 503.

  Os passos `precos` e `equipe` passam a vir `feito` pela API depois do "Continuar".
- **QA:** conferir os testes com os números do seed.
- **Segurança:** a M-01 e as B-01 a B-03 estão implementadas como o relatório pediu.

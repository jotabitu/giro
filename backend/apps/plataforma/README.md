# app `plataforma`

**Schema:** public
**Escopo:** Planos, empresas (tenants), faturas da assinatura, usuários da plataforma, acesso de suporte, implantações e chamados.
**Regras:** PLT, IMP (ver `docs/regras-de-negocio.md`)
**Telas:** Plat-*, Plataforma, Compra-*, Admin-Assinatura, Admin-Cancelar (ver `docs/telas/README.md`)

## Estrutura esperada

```
plataforma/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/plataforma.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-010, fase 1)

- `models.py`: `Plano` (os três do seed na migração 0005), `Empresa` (máquina de estados, `transicao_empresa`), `Dominio`, `UsoEmpresa` (resumo no public).
- `services.py`: `criar_empresa` (Django Admin no MVP; schema, domínio, uso, auditoria e o evento abaixo numa transação), `validar_criacao`, `exigir_limite`, `atualizar_uso`, `registrar_contador`, `recalcular_uso`, `registrar_passo_implantacao`, `registrar_acesso`.
- `selectors.py`: `empresa_atual`, `uso_do_plano`, `assinatura`, `com_situacao` (a ordem da tabela de situação em uma anotação SQL), `filtrar_empresas`, `contagens_das_empresas`, `detalhe_empresa`.
- `permissoes.py`: tabela do PLT-09, `pode(funcao)` e `exige_permissao(...)` (403 `PLT-09`).
- `tasks.py`: `plataforma_avisar_limite_90` (e-mail aos administradores, uma vez por item e por mês) e `plataforma_recalcular_uso` (Beat, 03:30).
- `api/`: `GET /api/plataforma/planos/`, `/empresas/`, `/empresas/{id}/` (host admin) e `GET /api/assinatura/` (host da empresa). Método de fase 2 responde 404.

## Implementado (T-070: modo suporte, PLT-07)

- `AcessoSuporte` (máquina `ativo` → `encerrado` ou `revogado`; `fim - inicio` de 15, 30 ou 60 min). Tudo do acesso roda em `schema_context(public)`, porque do host da empresa o `search_path` acharia a tabela de usuários da empresa.
- `services.py`: `abrir_acesso_suporte` (422 `PLT-07` com o suporte bloqueado; e-mail aos administradores depois do commit), `conferir_acesso_suporte` (registrada em `comum.autenticacao` no `ready()`), `sair_do_suporte`, `revogar_acesso_suporte`, `definir_bloqueio_do_suporte` (bloquear revoga os ativos na hora) e `encerrar_acessos_vencidos` (AUT-15). Cada fato vai para as duas auditorias; na da empresa, a entrada e a saída têm o ator `suporte` com o `acesso_suporte_id` (AUD-03).
- `api/suporte.py`: `POST /api/plataforma/empresas/{id}/acessos-suporte/` (função com `entrar_como_suporte`; a URL de entrada leva o token no fragmento) e, no host da empresa, `GET /api/suporte/`, `POST /api/suporte/bloquear/`, `liberar/` e `acessos/{id}/revogar/` (administrador; o suporte nunca usa).
- Tarefas: `plataforma_avisar_entrada_do_suporte` e `aut_15_encerrar_acessos_de_suporte_vencidos` (Beat, a cada minuto).

## Implementado (T-184: faturas da assinatura e conta principal)

Contrato: `docs/api/assinatura.md` ("Faturas, cobrança e régua", "De onde vem o endereço", "Tomador da fatura"); ADR 0023.

- `models.py`: `Empresa.email_cobranca`, `endereco_*`, `ciclo_proximo`, `dia_vencimento`; `FaturaAssinatura` (máquina `aberta` → `paga`, `atrasada`, `cancelada`; código `FAT-0001` por empresa, sequência `FAT-<empresa_id>` no public; uma mensalidade viva por competência; campos da nota, do tomador e do cancelamento); `FormaPagamentoAssinatura` (1:1, token do cartão cifrado, nunca na API nem na auditoria).
- `calendario.py`: `proximo_periodo`, `vencimento_seguinte` (mês sem o dia vence no último) e `descricao_da_fatura` (PLT-01, PLT-14), funções puras.
- `services.py`: `criar_empresa` cria a FAT-0001 (vence `teste_fim + 1`) e a forma vazia; `criar_fatura` (única porta), `criar_primeira_fatura`, `preco_no_ciclo`; `copiar_endereco_da_matriz` (chamado por `filiais.criar_filial`); `atualizar_pagador` (pagador na conta principal); `registrar_webhook_principal` e `processar_webhook_fatura` (baixa idempotente, consulta o parceiro, guarda o cartão só com a forma `cartao`); `gravar_tomador` (na baixa enquanto a NFS-e está desligada).
- `tasks.py`: `plataforma_processar_webhook_fatura` (tenta de novo com o parceiro fora) e `plataforma_pedir_notas_pendentes` (só conta enquanto a T-197 não existe).
- `admin.py`: faturas de todas as empresas só para leitura, com o filtro "nota pendente".
- O webhook (`financeiro/api/views.py`) procura a `ContaPagamento` pelo token; sem ela, confere o hash da conta principal (`GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH`) e grava o aviso no public.

## Implementado (T-185, parte 1: rotas da assinatura)

Contrato: `docs/api/assinatura.md`. A parte 2 (forma de pagamento e faturas) vem na branch `t-185b-forma-faturas`.

- `catalogo.py`: os textos da `PLT-11` num lugar só (`inclui` para Comparar planos, `a_mais` para o cartão do plano acima). Mudou a regra, muda só ele.
- `services.py`: `mudar_plano` (serviço único da tela e da ação da plataforma; `por=POR_EQUIPE` também muda o ciclo, valendo na próxima fatura), `simular_mudanca_plano`, `desfazer_mudanca_plano`, `proxima_mensalidade`, `excede_no_plano`, `atualizar_dados_fiscais`. `pendencias_dos_modulos` devolve vazio até a T-196. Os fatos da empresa vão para as duas auditorias (`_registrar_nos_dois`), a cópia do endereço da matriz também.
- `selectors.py`: `assinatura(empresa, usuario)` com `proxima_fatura`, `plano_proximo` e, só para o administrador, `forma_pagamento`, `dados_fiscais`, `oferta` e `acoes`; `planos_da_assinatura`.
- `api/assinatura.py`: `GET assinatura/planos/`, `POST assinatura/mudanca-plano/simular/`, `POST` e `DELETE assinatura/mudanca-plano/`, `PATCH assinatura/dados-fiscais/`. Só o administrador (403 `permissao`); o suporte lê e nunca escreve (403 `PLT-07`, "O suporte não mexe na assinatura da empresa").
- `tasks.py`: `plataforma_atualizar_pagador` (dados fiscais mudados, pagador na conta principal).
- Em `comum`: `EmpresaOperando` aceita `escreve_na_suspensa` (lista explícita, conferida em teste) e `recusa_na_suspensa` (o 409 da regra no lugar do 403); `suporte_proibido` usa a `mensagem_suporte_proibido` da view; a classificação da auditoria ganhou `omitir_no_public` (dados que o apagamento limpa, `AUD-08`).

## Implementado (T-185, parte 2: forma de pagamento e faturas)

- `models.py`: na `FaturaAssinatura`, a cobrança viva (`cobranca_tipo`, Pix, linha digitável, boleto, página do cartão) e o `recibo_url` da baixa (migração `0010`); fora da auditoria.
- `services.py`: `escolher_forma_pagamento` (Pix automático pela autorização recorrente, cartão pela página do parceiro, boleto; a troca cancela a autorização, esquece o token e cancela a cobrança viva de outra forma) e `pagar_fatura` (pela forma ou por outro `meio`, sem trocar a forma; uma cobrança viva por fatura; com Pix automático e o boleto vivo emitido sem a autorização, devolve o boleto, T-298).
- `selectors.py`: `faturas_da_empresa` (sempre da empresa da requisição), `item_da_fatura`, `linha_do_teste`, `detalhe_da_fatura`.
- `api/assinatura.py`: `PUT assinatura/forma-pagamento/`, `GET assinatura/faturas/`, `GET assinatura/faturas/{codigo}/`, `POST assinatura/faturas/{codigo}/pagar/`. Com as três rotas de pagar, a lista `escreve_na_suspensa` fica completa (CA-ASS-27).
- Interface de pagamentos: `SituacaoCobranca.recibo_url` (Asaas: `transactionReceiptUrl`).

## Implementado (T-186, parte 1: estados e virada)

Contrato: `docs/api/assinatura.md` ("Transições da empresa" e "Downgrade agendado: conferência e virada"). As partes 2 (geração e emissão das faturas, cartão guardado, Pix automático autorizado) e 3 (mensagens da régua `AUT-13`) vêm nas branches `t-186b` e `t-186c`.

- `services.py`: `virar_estados` (faturas vencidas em `atrasada` em D+1, `aplicar_mudanca_agendada` e `estado_do_dia` por empresa, cada uma na sua transação, idempotente); `transicionar_empresa` (o estado no public e o mesmo fato na empresa); `voltar_a_ativa_ao_pagar`, chamada na baixa (`_processar_fatura`): `inadimplente` ou `suspensa` sem outra atrasada, ou `em_teste` com a 1ª paga depois do fim do teste, vira `ativa` na hora. `DIAS_ATE_SUSPENDER = 15` conta do vencimento da atrasada mais antiga.
- `models.py`: `Empresa.TRANSICOES` ganhou `em_teste` → `inadimplente` (com forma e sem pagar, em D+1).
- `tasks.py`: `plataforma_virar_estados`, no Beat às 00:05.
- `comum.estados`: `refresh_from_db` passa a atualizar o status salvo, para a cópia relida salvar outros campos.

## Implementado (T-186, parte 2: geração, emissão e cartão guardado)

- `services.py`: `gerar_faturas` (Beat, 06:00), em três passos, cada fatura ou empresa na sua transação e idempotente:
  1. `gerar_fatura_do_periodo`: 5 dias antes do vencimento seguinte (`DIAS_DE_ANTECEDENCIA`), a mensalidade do período seguinte para `em_teste`, `ativa`, `inadimplente` e `suspensa`, nunca depois do `acesso_ate`. Com downgrade agendado, confere o uso de novo (`excede_no_plano`, `Empresa` e `UsoEmpresa` travados): não cabe, o agendamento cai, a fatura sai pelo plano atual, auditoria `empresa.mudar_plano_recusado` nos dois lugares e e-mail com o motivo (CA-ASS-40); cabe, a fatura sai pelo plano agendado (CA-ASS-41).
  2. `emitir_cobranca_da_fatura`: a fatura `aberta` sem cobrança que vence em até 5 dias sai pela forma: boleto (e o e-mail no dia), Pix automático pela autorização ativa (`cobranca_tipo = pix_auto`), página do parceiro para o cartão ainda não digitado. Cartão guardado espera o vencimento; sem forma, nada sai. Pix automático com a autorização pendente sai em boleto com Pix, com a linha da `PLT-13` no e-mail, e fica no boleto até o fim, mesmo autorizado depois (T-297, CA-ASS-63).
  3. `cobrar_cartao_da_fatura`: o cartão guardado no vencimento (a diferença do upgrade, na hora), pelo token decifrado só em `integracoes.pagamentos.cobrar_cartao_guardado` (ADR 0023). Recusado: `cartao_recusado_em` e mais uma tentativa; a 2ª é no dia seguinte, e com `TENTATIVAS_DO_CARTAO` (2) não há outra (CA-ASS-12).
- Diferença do upgrade com cartão guardado: `mudar_plano` agenda `plataforma_cobrar_cartao` depois do commit (tenta de novo com o parceiro fora). Nas outras formas, a diferença sai no passo 2.
- Aviso do Pix automático autorizado: o webhook da conta principal lê o aviso da autorização (`EventoWebhook.autorizacao_id`), consulta a autorização no parceiro (`consultar_autorizacao`, novo na interface) e, ativa, leva a forma a `ativa` (`assinatura.forma_ativa`). Outra situação não muda a forma e fica no resultado do aviso.
- `tasks.py`: `plataforma_gerar_faturas`, `plataforma_cobrar_cartao`, `plataforma_enviar_boleto` e `plataforma_avisar_downgrade_recusado`. Os e-mails vão para o `email_cobranca` e os administradores ativos (`destinatarios_da_cobranca`), com a marca Giro.

## Implementado (T-186, parte 3: régua da assinatura)

- `services.py`: `regua_da_assinatura` (`aut_13_regua_assinatura`, Beat 09:00, `PLT-02`): no dia exato de cada marco (`MARCOS_DA_REGUA`), `avisar_pela_regua` manda o D-3 por e-mail, o D0 e o D+3 por e-mail e WhatsApp (`responsavel_telefone`) e o D+7 por e-mail, com a tarefa de ligação (`_pedir_ligacao`: e-mail ao Dono e ao Financeiro da plataforma e o evento `fatura_assinatura.pedir_ligacao`, até a `Plat-Cobranca` da fase 2). Uma vez por marco: o evento `fatura_assinatura.regua` (`depois.marco`) é a marca. Fatura paga ou cancelada e empresa `cancelada` ficam fora (`PLT-06`).
- `mensagem_da_regua`: os textos de cada marco, com o caminho de pagar da fatura (boleto, página do cartão, cartão guardado, Pix automático, cartão recusado como na tela).

## Eventos publicados

| Evento | Quando | Dados |
| --- | --- | --- |
| `plataforma.empresa_criada` | `criar_empresa`, já no schema da empresa nova | `empresa_id`, `administrador` (`nome`, `email`, `celular`) |

## Para os outros apps

Ao criar, desativar ou reativar filial, veículo ou usuário: `exigir_limite(item)` e `atualizar_uso(item, ±1)` na mesma transação. No `ready()`, registre a contagem real com `registrar_contador(item, funcao)` (contas já registra `usuarios`).

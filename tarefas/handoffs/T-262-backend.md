# T-262 · Troca do ramo em Configurações (backend) · backend → frontend, qa, arquiteto

**O que foi feito:**
- O ramo passa a ser guardado: `ConfiguracaoEmpresa.atividade` (`aluga`, `vende`, `ambos`; padrão `ambos`) e `trabalha_com` (`motos`, `carros`, `ambos`; padrão `motos`), migração `empresas.0005_ramo`. Muda só por `empresas.services.mudar_ramo(atividade, trabalha_com, por)`.
- `comum.empresa.atividade()`, registrada por `empresas` no `ready()` (ADR 0024, item 2). O menu (`contas.navegacao.da_empresa`) passa a ler o ramo guardado: quem só aluga deixa de ver Vendas no pedido seguinte.
- Em `plataforma.selectors`: `recursos_para(plano, atividade)` (função pura), `atividades_aceitas(plano)` (Essencial: `aluga` e `ambos`), `recursos_da_empresa()` e `primeiro_plano_com(recurso)` (o nome do plano no aviso de "vende").
- `comum.modulos`: o registro de pendências da ADR 0024, item 7 (`registrar_pendencia`, `pendencias(recursos)`), com os textos dos seis grupos na ordem do contrato. Contadores registrados: `locacoes` (em `locacoes`, `aguardando_retirada`, `ativa`, `devolucao_atrasada`) e `comissoes` (em `financeiro`, nem `paga` nem `estornada`). `vendas` vale 0 (o app ainda não tem model).
- `GET /api/ramo/` e `PUT /api/ramo/` pelo contrato (`empresas.md`): só administrador; o suporte lê e recebe 403 `PLT-07` no `PUT`; empresa pausada, suspensa ou cancelada: 403 `empresa_sem_operacao`. O `PUT` trava a linha, recusa com 422 `PLT-12` (`motivo: "plano"` ou `motivo: "abertos"`), grava, audita `empresa.mudar_ramo` (configurações, `PLT-12`, com `recursos` antes e depois) e marca o passo `ramo`. Mesmo ramo: 200 sem evento.
- Cartão `ramo` em `GET /api/configuracoes/` logo depois de `marca` ("O que a empresa faz", "Locação e venda · motos" no seed), do app `empresas` como a marca, fora para o token de suporte.

**Onde:** `backend/apps/empresas/` (models, migração, selectors, services, api), `backend/comum/empresa.py`, `backend/comum/modulos.py`, `backend/apps/plataforma/selectors.py`, `backend/apps/locacoes/apps.py`, `backend/apps/financeiro/apps.py`, `backend/apps/contas/navegacao.py`, `backend/apps/relatorios/configuracoes.py` e `selectors.py`.

**Contrato:** `GET`/`PUT /api/ramo/` e o cartão `ramo` (`docs/api/openapi.yaml` regenerado; `npm run api:gerar` e `typecheck` limpos).

**Regras cobertas:** PLT-12, PLT-07 (testes em `tests/aceitacao/test_t262_ramo.py`: `test_plt_12_troca_de_ramo_com_algo_aberto` (CA-ASS-50), `test_plt_12_essencial_sem_so_vende` (CA-ASS-51), `test_plt_12_configuracoes_cartao_ramo`, `test_plt_12_configuracoes_ramo_ausente_para_o_suporte`, `test_plt_12_suporte_le_o_ramo_e_nao_troca` e outros). `test_t181_configuracoes.py` passou a esperar o cartão.

**O que ficou de fora (T-196):**
- O enum novo de `Recurso` (entram `conciliacao`, `recebimento_parceiro`, `cobranca_whatsapp`; saem `dominio_proprio`, `api_integracoes`; `contrato_digital` no Essencial) e a migração dos planos. Até lá, `modulos` do `GET /api/ramo/` traz os nomes de hoje (seis no Profissional, sem "Conciliação", "Pix e boleto automáticos" e "Cobrança pelo WhatsApp"; `dominio_proprio` e `api_integracoes` ficam fora da lista), e o Essencial não mostra "Contrato digital".
- `ModuloDoPlano` (403 `PLT-12` nas rotas do módulo desligado), `comum.empresa.tem_recurso`, a comissão só com o módulo ligado (item 11), e a contagem do downgrade: `plataforma.services.pendencias_dos_modulos` segue devolvendo `[]`; a T-196 pode chamar `comum.modulos.pendencias` e registrar os grupos de despesas e OS.

**Para o arquiteto:** o teto de consultas de `GET /api/configuracoes/` (`configuracoes.md`, "no máximo 10") virou 11 no teste: o cartão `ramo` lê a linha de `ConfiguracaoEmpresa`, que a T-259 pôs nas fontes. Dá para voltar a 10 tirando a leitura repetida de `UsoEmpresa` (`assinatura` e `implantacao` leem cada um a sua) em `plataforma.selectors`, que os PRs #339 e #342 também tocam (lá é `services.py` e `tasks.py`; aqui só `selectors.py`). Confirme o número ou peça a troca.

**Próximo passo para quem recebe:** (frontend) a rota `/admin/ramo` pela referência `Admin-Ramo`, ligada a `GET` e `PUT /api/ramo/`, com as opções, os avisos e os módulos que a API manda e a recusa 422 `PLT-12` com o `abertos_texto`. (qa) conferir o cartão no seed e a troca no navegador.

# Backlog

Ordem = prioridade. A fase 1 entrega o MVP (rodar uma locação de ponta a ponta numa filial piloto). O orquestrador revisa esta lista a cada fim de tarefa.

## Decisões

As pendências de regra foram decididas em 07 out 2026 (seção "Decisões de 07 out 2026" de `docs/regras-de-negocio.md`). Continuam com o dono do produto, fora do código:

- [bloqueada] Registrar girolocadoras.com.br e girolocacao.com.br.
- [bloqueada] Busca no INPI da marca "Giro" (classes 42 e 9).
- [bloqueada] Abrir a conta do Asaas (a integração começa no sandbox, não depende disso).

A dúvida da segurança S-02 (T-032: o suporte Giro vê CPF e CNH completos?) foi decidida em 07 out 2026 e virou a regra `AUD-09` (mascarado, nunca completo).

As dúvidas levantadas pelo arquiteto em T-006 foram aprovadas em 07 out 2026 e viraram regra (T-031; ver "Decisões de 07 out 2026" em `docs/regras-de-negocio.md`).

As dúvidas de filiais da T-030 e de contas da T-036 (itens 6 a 10) foram decididas em 07 out 2026 e viraram regra (T-037: seção Filiais, `LOC-11`, `VEI-04`, `USR-01`, `USR-06`). O item 12 (desbloqueio manual) foi decidido em 07 out 2026 e virou regra (`CLI-05`, `APR-05`, T-041). Os itens 11 e 13 de clientes foram decididos em 07 out 2026 e viraram regra (`CLI-07`, `CLI-09`, T-041). As dúvidas da T-038 (locações e vistorias) e a do pro rata dos juros foram decididas em 07 out 2026 e viraram regra (T-041: `FIN-03`, `DEV-01`, `DEV-03`, `LOC-08`, `LOC-09`, `FIN-09` e a tabela de perfis); no merge da branch do arquiteto, as linhas `[decisão]` da T-038 saem.

Levantadas pelo arquiteto em T-030 (07 out 2026):

- [divergência] Dados de exemplo nas telas da plataforma (para T-028): `Plat-Empresa-Detalhe` mostra CNPJ 41.208.733/0001-52 (seed: 12.345.678/0001-10), FAT-0001 vencendo em 21 out (PLT-01: dia seguinte ao fim do teste, 22 out) e "13 dias" de teste em 07 out (contrato: 14); `Plat-Empresas` mostra Moto Rápida com 4 usuários (seed: 5).

Levantadas pelo arquiteto em T-036 (07 out 2026):

- [divergência] `Frota` mostra a reserva do Kwid como `RES-0412`, mas a reserva é uma locação `aguardando_retirada` com código `LOC-` (regras, Veículos e Locação). `docs/api/veiculos.md` mostra o código `LOC-`. Para T-028, junto com as diárias da Frota que não batem com a tabela (CG 160 R$ 49,90, Pop R$ 39,90, NMax R$ 69,90, Mobi R$ 119,00).

Levantadas pelo arquiteto em T-038 (07 out 2026); as dúvidas foram decididas pelo dono do produto (T-041) e já estão nos contratos:

- [divergência] Telas de locação (para T-028): `Devolucao` mostra "faltou 1/2 tanque" para LOC-2836, mas o seed fecha R$ 32,00 com chegada em 3/4 (16 L × 1/4 × R$ 5,50 + R$ 10); `Locacao` diz "Com 3 dias de atraso numa parcela, o contrato entra na lista de bloqueio" (`CLI-05`: 15 dias) e tem o campo "Filial de devolução" (`FIL-05`: a devolução é na filial da locação); `Vistoria` mostra LOC-2856 com diária R$ 44,90, 30 dias, franquia de 3.000 km, caução R$ 500 e total R$ 1.347 (é semanal Street: R$ 329,00 + caução R$ 300,00, km livre); `Locacoes` mostra ROE-2A88 como Pop 110i e RHT-9F02 como Biz 125 (na `Frota` são Mobi e Kwid) e LOC-2848 com Kwid QYC-4D72 (no `Vistoriador`, QYC-4D72 é uma CG 160); `Contratos-Modelos` tem "Termo de devolução" como modelo, mas modelo de contrato só tem finalidade locação ou venda e o recibo da devolução é documento do sistema.

Levantadas pelo arquiteto em T-043 (07 out 2026):

- [decisão] Devolução de caução e reembolsos por Pix: no MVP o sistema registra o valor a devolver (`Reembolso`, `a_fazer`) e a pessoa faz o Pix pela conta da locadora e marca como feito com o comprovante; transferência automática pelo parceiro só depois das proteções de saque da subconta (S-05). Confirmar se atende o botão "Encerrar e devolver R$ 183,00 por Pix" da `Devolucao`.
- [divergência] Telas do financeiro e da auditoria (para T-028): `Receber` usa faixas 1–7, 8–15, 16–30 e 30+ (`FIN-02`: 1–7, 8–30, mais de 30) e mostra Rafael com parcela de R$ 350,00 de 05 set; `Caixa` gera Pix de R$ 299,40 para a parcela atrasada de Carlos (com multa e juros, `FIN-03`, são R$ 306,09); `Admin-Auditoria` diz "3 senhas erradas" (`USR-06`: 5); `Admin-Exportar` mostra Lúcia (financeiro) exportando, mas exportar é da Administração (só administrador).


## Fase 0 · Fundação

### T-001 · Esqueleto do backend
- **Agente:** backend
- **Depende de:** T-003
- **Regras:** convenções de `CLAUDE.md`
- **Pronto quando:** `backend/` com projeto Django 5, settings divididos (base, dev, test, prod), django-tenants configurado com schema público e de empresa, DRF, drf-spectacular servindo `/api/schema/`, pytest rodando, `make backend-check` verde. Inclui `backend/comum/`: model base com código sequencial por empresa (`LOC-2856`), campos de dinheiro em centavos, erro de negócio com código de regra e o registro de evento de auditoria (AUD-01), para que todo módulo já nasça auditado.

### T-002 · Esqueleto do frontend
- **Agente:** frontend
- **Depende de:** T-003
- **Pronto quando:** `frontend/` com Next.js App Router, TypeScript estrito, Tailwind lendo os tokens de `src/design-system/tokens.ts`, grupos de rota `(publico)`, `(empresa)`, `(plataforma)`, ESLint e Vitest verdes.

### T-003 · Ambiente de desenvolvimento
- **Agente:** devops
- **Pronto quando:** `docker compose up` sobe Postgres 16, Redis, backend, worker Celery, beat e frontend; `.env.example` completo; `make up`, `make down`, `make check`.

### T-004 · Portar o design system para código
- **Agente:** design-system
- **Depende de:** T-002
- **Pronto quando:** `frontend/src/design-system/` com tokens (claro e escuro), variáveis `--brand`, `--brand-soft`, `--on-brand` trocáveis em tempo de execução, e os 12 componentes de `docs/design-system/components/` como componentes React com página de preview.

### T-005 · CI
- **Agente:** devops
- **Depende de:** T-001, T-002
- **Pronto quando:** os 5 pontos para o devops do handoff da T-001 resolvidos (desvio do Makefile, `MSYS_NO_PATHCONV`, CORS fora do `.env.example`, proxy de mesma origem `/api/`); GitHub Actions roda lint, testes e build do backend e do frontend em todo PR; gera o OpenAPI e falha se `docs/api/openapi.yaml` estiver desatualizado.

### T-006 · ADRs iniciais revisadas
- **Agente:** arquiteto
- **Pronto quando:** as ADRs de `docs/decisoes/` revisadas e o modelo de dados das 25 entidades desenhado em `docs/decisoes/modelo-de-dados.md`, com schema (público ou empresa) de cada uma.

### T-030 · Contratos da API de plataforma e filiais
- **Agente:** arquiteto
- **Depende de:** T-006
- **Regras:** PLT-01, PLT-03, PLT-08, PLT-09, USR-07
- **Pronto quando:** `docs/api/plataforma.md` e `docs/api/filiais.md` com endpoints, payloads, erros e permissões por perfil. Destrava T-010 e T-012.

### T-031 · Responder as dúvidas de regra da T-006
- **Agente:** produto
- **Depende de:** T-006
- **Pronto quando:** as cinco `[decisão]` levantadas pelo arquiteto (status não listados, `cancelada` na venda, venda aberta, arredondamento, chassi único) analisadas com recomendação em "Pontos em aberto" de `docs/regras-de-negocio.md`, para o dono do produto aprovar.

### T-032 · Revisão de segurança do desenho da fundação
- **Agente:** seguranca
- **Depende de:** T-006
- **Pronto quando:** ADRs 0008 a 0012 e o modelo de dados revisados, com atenção a campos mascarados na auditoria (0010), guarda de `plataforma.ContaPagamento.chave_api_cifrada` e token de suporte (0008). Relatório em `docs/seguranca/`; achados altos viram tarefas.

### T-033 · Dados sensíveis na fundação: cifra, hash de busca e classificação da auditoria
- **Agente:** backend
- **Depende de:** T-001
- **Regras:** CLI-01, AUD-01, AUD-04, AUD-06 · **ADR:** 0014 (itens 2 e 3) · **Segurança:** S-05, S-06, S-07
- **Pronto quando:** `comum/cripto.py`, `CampoCifrado`, `CampoHashBusca`, `CAMPOS_AUDITORIA` aplicado por `comum.auditoria` e o teste de arquitetura de campos sensíveis; os testes obrigatórios da ADR 0014 que não dependem de cliente ou sessão; `cryptography` registrada no PR e os três segredos no `.env.example`. Inclui C-01 (diff da auditoria calculado antes da máscara) e C-02 (tarefa com schema apagado não cai no public) da T-039. Bloqueia T-011 e T-014.

### T-034 · Auditoria e Celery endurecidos
- **Agente:** backend (papéis do banco com ADR do arquiteto e configuração do devops)
- **Depende de:** T-001
- **Regras:** AUD-01, AUD-02 · **Segurança:** S-10, S-11, C-03 (IP real atrás do proxy, só de proxies confiáveis), C-05 (trigger sem `TRUNCATE`, mesmo que S-10)
- **Pronto quando:** critério do item "[média] Auditoria e Celery endurecidos" de `docs/seguranca/2026-10-07-fundacao.md` (trigger também em `TRUNCATE`, expurgo só com mais de 5 anos, `na_empresa` restaura ator e schema, `task_prerun`/`task_postrun` voltam ao public, cache com `make_key`, `@tarefa_de_empresa` recusa `public` e schema inexistente, tasks recebem só ids).

### T-035 · Endurecimento de produção
- **Agente:** devops
- **Depende de:** T-001, T-002
- **Segurança:** S-16, S-17, S-18, C-04 (`wsgi.py`, `asgi.py` e `config/celery.py` sem padrão `dev`; falha se `DJANGO_SETTINGS_MODULE` não vier em produção)
- **Pronto quando:** `SHOW_PUBLIC_IF_NO_TENANT_FOUND = False` em `prod.py`; HSTS com preload, `Referrer-Policy`, `X-Frame-Options: DENY`, CSP no front; `/api/schema/` e `/api/docs/` fechados em produção; `SIMPLE_JWT["SIGNING_KEY"]` com variável própria. Precisa estar pronta antes do primeiro deploy de homologação.

### T-036 · Contratos da API de contas, veículos e clientes
- **Agente:** arquiteto
- **Depende de:** T-030
- **Regras:** USR-01 a USR-07, VEI-01 a VEI-07, CLI-01 a CLI-08, AUD-04, AUD-05 · **ADRs:** 0013, 0014
- **Pronto quando:** `docs/api/contas.md` (inclui sessões, 2 etapas e convite), `docs/api/veiculos.md` e `docs/api/clientes.md` no padrão de `docs/api/README.md`. Destrava T-011, T-013 e T-014.

### T-037 · Dúvidas da T-030 e critérios de aceite de T-010 a T-014
- **Agente:** produto
- **Depende de:** T-030, T-031
- **Pronto quando:** recomendação para as `[decisão]` da T-030 (campos da tela Filial sem regra, desativação de filial com operação) em "Pontos em aberto"; critérios de aceite com números do seed para T-010, T-011, T-012, T-013 e T-014, no formato que o qa transforma em teste.

### T-038 · Contratos da API de locações, vistorias e devolução
- **Agente:** arquiteto
- **Depende de:** T-036
- **Regras:** LOC-01 a LOC-15, VIS-01 a VIS-05, DEV-01 a DEV-06 · **Segurança:** S-09 (marcadores fechados do `ModeloContrato`, `url_fetcher`), S-15 (token de assinatura)
- **Pronto quando:** `docs/api/locacoes.md` (reserva, contrato, ciclo de status, assinatura) e `docs/api/vistorias.md` (saída, devolução e acerto) no padrão de `docs/api/README.md`, com o caso LOC-2836 = R$ 183,00 descrito no exemplo de resposta do acerto. Destrava T-015 e T-016.

### T-039 · Revisão de segurança do código da T-001
- **Agente:** seguranca
- **Depende de:** T-001
- **Pronto quando:** `comum/autenticacao.py`, `comum/auditoria.py` (máscaras), o trigger de `apps/auditoria/migrations/0002_trigger_imutavel.py`, settings e rotas revisados contra as ADRs 0008 a 0013; relatório em `docs/seguranca/`; achados viram tarefas.

### T-040 · Cobertura de regras e esqueleto dos testes de aceitação de T-010 a T-014
- **Agente:** qa
- **Depende de:** T-001, T-037
- **Pronto quando:** `docs/qa/cobertura-de-regras.md` com a tabela regra → teste → status para todas as regras com código; em `backend/tests/aceitacao/`, um teste por critério de `docs/qa/criterios/T-010.md` a `T-014.md`, com o código da regra no nome, marcados `xfail` (motivo: tarefa ainda não implementada) até o backend entregar. Os testes rodam no CI sem quebrar.

### T-041 · Critérios de aceite de T-015 a T-018
- **Agente:** produto
- **Depende de:** T-037, T-038
- **Pronto quando:** `docs/qa/criterios/T-015.md` a `T-018.md` com números do seed (LOC-2836 = R$ 183,00, caixa de 07 out = gaveta R$ 281,00 e os demais casos da tabela de referência), apontados no "Pronto quando" das tarefas.

### T-042 · Componente de código de 6 dígitos (OTP)
- **Agente:** design-system
- **Depende de:** T-004, T-026
- **Pronto quando:** componente `CodigoVerificacao` em `frontend/src/design-system/` como na tela `Ativar-2FA` (6 casas, colar o código inteiro, avanço e volta com teclado, estado de erro, `autocomplete="one-time-code"`, acessível), com preview e testes. Usado pela T-020.

### T-043 · Contratos da API de financeiro e auditoria
- **Agente:** arquiteto
- **Depende de:** T-038
- **Regras:** FIN-01 a FIN-08, AUD-01 a AUD-03, AUD-09 · **Segurança:** S-14 (webhooks)
- **Pronto quando:** `docs/api/financeiro.md` (contas a receber, caixa do dia, baixa, interface de pagamentos para a T-029) e `docs/api/auditoria.md`, com o caso do caixa de 07 out (gaveta R$ 281,00). Inclui alinhar `vistorias.md` (fórmula do combustível da DEV-01, exemplo com chegada em 3/4) e `locacoes.md` (renovação e troca decididas: LOC-08, LOC-09) às decisões da T-041. Destrava T-017 e T-018.

## Fase 1 · MVP

### T-010 · Plataforma: planos, empresas, criação de schema
- **Agente:** backend · **Depende de:** T-001, T-006, T-030 · **Regras:** PLT-01, PLT-03, PLT-08, PLT-09 (cobrança, suporte e cancelamento ficam para a fase 2) · **Telas:** Plat-Empresas, Plat-Empresa-Detalhe, Plat-Planos · **Nota:** no MVP a empresa piloto é criada pelo Django Admin; as telas da plataforma ficam para a fase 2. · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-010.md` (CA-010-01 a 17) passam, com o código da regra no nome do teste.

### T-011 · Contas, perfis, permissões, 2FA, convite
- **Agente:** backend · **Depende de:** T-012, T-033 · **ADRs:** 0013, 0014 (sessões) · **Segurança:** S-02, S-03, S-08, S-13 · **Regras:** USR-01 a USR-07 · **Telas:** Login, Acesso-Senha, Convite, Admin-Usuarios · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-011.md` (CA-011-01 a 28) passam, com o código da regra no nome do teste.

### T-012 · Filiais
- **Agente:** backend · **Depende de:** T-010, T-030 · **Segurança:** SVG do logo sanitizado e exibido só por `<img>` (S-12) · **Regras:** PLT-03 (limite), USR-07 · **Telas:** Filiais, Filial · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-012.md` (CA-012-01 a 17) passam, com o código da regra no nome do teste.

### T-013 · Veículos, categorias, documentos, histórico de status
- **Agente:** backend · **Depende de:** T-012 · **Regras:** VEI-01 a VEI-06 · **Telas:** Frota, Veiculo, Precos · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-013.md` (CA-013-01 a 26) passam, com o código da regra no nome do teste.

### T-014 · Clientes, documentos, bloqueio, LGPD
- **Agente:** backend · **Depende de:** T-011, T-033 · **Segurança:** S-07, upload validado pelo conteúdo (S-12) · **Regras:** CLI-01 a CLI-08, AUD-04, AUD-05 · **Telas:** Clientes, Cliente · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-014.md` (CA-014-01 a 22; os marcados [integração] voltam no seed completo da T-019) passam, com o código da regra no nome do teste.

### T-015 · Locação: reserva, contrato, ciclo de status
- **Agente:** backend · **Depende de:** T-013, T-014 · **Segurança:** token de assinatura com prazo e uso único, S-09 no `ModeloContrato` (S-15) · **Regras:** LOC-01 a LOC-13 · **Telas:** Locacao, Locacoes, Locacao-Detalhe, Contratos-Modelos · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-015.md` (CA-015-01 a 25) passam, com o código da regra no nome do teste.

### T-016 · Vistoria de saída e devolução com acerto
- **Agente:** backend · **Depende de:** T-015 · **Regras:** VIS-01 a VIS-05, DEV-01 a DEV-06 · **Telas:** Vistoria, Devolucao, Vistoriador
- **Pronto quando:** caso LOC-2836 devolve R$ 183,00 e todos os critérios de `docs/qa/criterios/T-016.md` (CA-016-01 a 20) passam, com o código da regra no nome do teste.

### T-017 · Contas a receber, caixa do dia, baixa
- **Agente:** backend · **Depende de:** T-015 · **Regras:** FIN-01 a FIN-08 · **Telas:** Receber, Caixa, Financeiro · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-017.md` (CA-017-01 a 22) passam, com o código da regra no nome do teste.

### T-018 · Tela e consulta da auditoria
- **Agente:** backend · **Depende de:** T-011 · **Regras:** AUD-01 a AUD-03 (o registro dos eventos já vem de T-001) · **Telas:** Admin-Auditoria, Plat-Auditoria · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-018.md` (CA-018-01 a 16) passam, com o código da regra no nome do teste.

### T-019 · Seed Moto Rápida
- **Agente:** qa · **Depende de:** T-013 a T-017 · **Pronto quando:** `make seed` cria a empresa de exemplo e todos os casos da tabela "Dados de referência para testes" passam.

### T-026 · Desenhar telas que faltam para o MVP
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** "Esqueci a senha" e "Ativar verificação em 2 etapas" (desktop e celular) em `docs/telas/html/`, no mesmo padrão das telas de acesso, e no índice. Bloqueia a parte de 2FA de T-020.

### T-027 · Importação de veículos e clientes por planilha
- **Agente:** backend · **Depende de:** T-013, T-014 · **Regras:** IMP (passo de importar) · **Telas:** Onboarding-Importar · **Por quê:** critério de pronto do MVP "dados antigos migrados e conferidos".

### T-028 · Limpar dados de exemplo das telas
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** os números das telas batem com as regras e o seed. Já se sabe de: Patrícia (LOC-2812) aparece em Contas a receber com parcela de R$ 279,00 (plano Entregador, placa SAB-2K90), mas é mensal NMax SBC-0J44 nas outras telas; Marcos (LOC-2850) aparece com a placa SBC-0J44; ficha do veículo QXA-4B21 mostra "Plano padrão Semanal R$ 299,40" (Street agora é R$ 329,00); Juliana aparece "em dia" em Clientes e com parcela atrasada em Contas a receber; Financeiro mostra "3 clientes com 7+ dias R$ 1.299,40". Corrigir no canvas e em `docs/telas/html/`.

### T-029 · Integração com o Asaas (sandbox)
- **Agente:** backend · **Depende de:** T-017 · **Segurança:** `WebhookRecebido` com `evento_id` único e conferência na API do Asaas, throttle (S-14, S-17) · **Regras:** FIN-01 a FIN-04, AUT-04, AUT-05 · **Pronto quando:** `backend/integracoes/pagamentos/asaas.py` implementa a interface de pagamentos (criar subconta da empresa, cobrança Pix e boleto, assinatura recorrente, webhook de baixa com verificação e idempotência), testado contra o sandbox; a implementação falsa continua sendo a padrão em testes.

### T-020 · Telas de acesso e casca do app (sidebar e menu do celular)
- **Agente:** frontend · **Depende de:** T-002, T-004, T-011 · **Telas:** Login, Acesso-Senha, Convite, Main, Menu, e a navegação padrão descrita em `docs/telas/README.md`

### T-021 · Telas de veículos e clientes
- **Agente:** frontend · **Depende de:** T-020, T-013, T-014 · **Telas:** Frota, Veiculo, Clientes, Cliente

### T-022 · Telas de locação, vistoria e devolução
- **Agente:** frontend · **Depende de:** T-021, T-015, T-016 · **Telas:** Locacao, Locacoes, Locacao-Detalhe, Vistoria, Devolucao, Vistoriador

### T-023 · Telas do financeiro básico
- **Agente:** frontend · **Depende de:** T-020, T-017 · **Telas:** Receber, Caixa, Financeiro

### T-024 · Revisão de segurança do MVP
- **Agente:** seguranca · **Depende de:** T-011, T-014, T-018 · **Pronto quando:** checklist de `.claude/agents/seguranca.md` aplicado, achados viram tarefas.

### T-025 · Testes ponta a ponta do fluxo de locação
- **Agente:** qa · **Depende de:** T-022, T-023 · **Pronto quando:** Playwright cobre login → nova locação → vistoria de saída → devolução → baixa no caixa, no desktop e no celular.

## Fase 2 em diante

Vendas e aprovações (VEN, APR), despesas, comissões e conciliação (FIN-05 a FIN-13), manutenção (MAN), automações (AUT), implantação self-service (IMP), cobrança da assinatura (PLT), relatórios e DRE, exportação e cancelamento (AUD-06 a AUD-08). O orquestrador quebra em tarefas quando a fase 1 fechar.

# Backlog

Ordem = prioridade. A fase 1 entrega o MVP (rodar uma locação de ponta a ponta numa filial piloto). O orquestrador revisa esta lista a cada fim de tarefa.

## Decisões

As pendências de regra foram decididas em 07 out 2026 (seção "Decisões de 07 out 2026" de `docs/regras-de-negocio.md`). Continuam com o dono do produto, fora do código:

- [bloqueada] Registrar girolocadoras.com.br e girolocacao.com.br.
- [bloqueada] Busca no INPI da marca "Giro" (classes 42 e 9).
- [bloqueada] Abrir a conta do Asaas (a integração começa no sandbox, não depende disso).

Levantadas pelo arquiteto em T-030 (07 out 2026):

- [divergência] Dados de exemplo nas telas da plataforma (para T-028): `Plat-Empresa-Detalhe` mostra CNPJ 41.208.733/0001-52 (seed: 12.345.678/0001-10), FAT-0001 vencendo em 21 out (PLT-01: dia seguinte ao fim do teste, 22 out) e "13 dias" de teste em 07 out (contrato: 14); `Plat-Empresas` mostra Moto Rápida com 4 usuários (seed: 5).

Levantadas pelo arquiteto em T-036 (07 out 2026):

- [divergência] `Frota` mostra a reserva do Kwid como `RES-0412`, mas a reserva é uma locação `aguardando_retirada` com código `LOC-` (regras, Veículos e Locação). `docs/api/veiculos.md` mostra o código `LOC-`. Para T-028, junto com as diárias da Frota que não batem com a tabela (CG 160 R$ 49,90, Pop R$ 39,90, NMax R$ 69,90, Mobi R$ 119,00).
- [decisão] Desbloqueio manual de cliente: com o dono do produto (item 12 de "Pontos em aberto", T-037). O contrato segue o padrão A do produto: gerente e administrador desbloqueiam direto (`CLI-05`); o vendedor pede (`APR-05`).

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
- **Pronto quando:** GitHub Actions roda lint, testes e build do backend e do frontend em todo PR; gera o OpenAPI e falha se `docs/api/openapi.yaml` estiver desatualizado.

### T-006 · ADRs iniciais revisadas
- **Agente:** arquiteto
- **Pronto quando:** as ADRs de `docs/decisoes/` revisadas e o modelo de dados das 25 entidades desenhado em `docs/decisoes/modelo-de-dados.md`, com schema (público ou empresa) de cada uma.

## Fase 1 · MVP

### T-010 · Plataforma: planos, empresas, criação de schema
- **Agente:** backend · **Depende de:** T-001, T-006 · **Regras:** PLT-01, PLT-03, PLT-08, PLT-09 (cobrança, suporte e cancelamento ficam para a fase 2) · **Telas:** Plat-Empresas, Plat-Empresa-Detalhe, Plat-Planos · **Nota:** no MVP a empresa piloto é criada pelo Django Admin; as telas da plataforma ficam para a fase 2.

### T-011 · Contas, perfis, permissões, 2FA, convite
- **Agente:** backend · **Depende de:** T-012 · **Regras:** USR-01 a USR-07 · **Telas:** Login, Acesso-Senha, Convite, Admin-Usuarios

### T-012 · Filiais
- **Agente:** backend · **Depende de:** T-010 · **Regras:** PLT-03 (limite), USR-07 · **Telas:** Filiais, Filial

### T-013 · Veículos, categorias, documentos, histórico de status
- **Agente:** backend · **Depende de:** T-012 · **Regras:** VEI-01 a VEI-06 · **Telas:** Frota, Veiculo, Precos

### T-014 · Clientes, documentos, bloqueio, LGPD
- **Agente:** backend · **Depende de:** T-011 · **Regras:** CLI-01 a CLI-08, AUD-04, AUD-05 · **Telas:** Clientes, Cliente

### T-015 · Locação: reserva, contrato, ciclo de status
- **Agente:** backend · **Depende de:** T-013, T-014 · **Regras:** LOC-01 a LOC-13 · **Telas:** Locacao, Locacoes, Locacao-Detalhe, Contratos-Modelos

### T-016 · Vistoria de saída e devolução com acerto
- **Agente:** backend · **Depende de:** T-015 · **Regras:** VIS-01 a VIS-05, DEV-01 a DEV-06 · **Telas:** Vistoria, Devolucao, Vistoriador
- **Pronto quando:** caso LOC-2836 devolve R$ 183,00.

### T-017 · Contas a receber, caixa do dia, baixa
- **Agente:** backend · **Depende de:** T-015 · **Regras:** FIN-01 a FIN-08 · **Telas:** Receber, Caixa, Financeiro

### T-018 · Tela e consulta da auditoria
- **Agente:** backend · **Depende de:** T-011 · **Regras:** AUD-01 a AUD-03 (o registro dos eventos já vem de T-001) · **Telas:** Admin-Auditoria, Plat-Auditoria

### T-019 · Seed Moto Rápida
- **Agente:** qa · **Depende de:** T-013 a T-017 · **Pronto quando:** `make seed` cria a empresa de exemplo e todos os casos da tabela "Dados de referência para testes" passam.

### T-026 · Desenhar telas que faltam para o MVP
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** "Esqueci a senha" e "Ativar verificação em 2 etapas" (desktop e celular) em `docs/telas/html/`, no mesmo padrão das telas de acesso, e no índice. Bloqueia a parte de 2FA de T-020.

### T-027 · Importação de veículos e clientes por planilha
- **Agente:** backend · **Depende de:** T-013, T-014 · **Regras:** IMP (passo de importar) · **Telas:** Onboarding-Importar · **Por quê:** critério de pronto do MVP "dados antigos migrados e conferidos".

### T-028 · Limpar dados de exemplo das telas
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** os números das telas batem com as regras e o seed. Já se sabe de: Patrícia (LOC-2812) aparece em Contas a receber com parcela de R$ 279,00 (plano Entregador, placa SAB-2K90), mas é mensal NMax SBC-0J44 nas outras telas; Marcos (LOC-2850) aparece com a placa SBC-0J44; ficha do veículo QXA-4B21 mostra "Plano padrão Semanal R$ 299,40" (Street agora é R$ 329,00); Juliana aparece "em dia" em Clientes e com parcela atrasada em Contas a receber; Financeiro mostra "3 clientes com 7+ dias R$ 1.299,40". Corrigir no canvas e em `docs/telas/html/`.

### T-029 · Integração com o Asaas (sandbox)
- **Agente:** backend · **Depende de:** T-017 · **Regras:** FIN-01 a FIN-04, AUT-04, AUT-05 · **Pronto quando:** `backend/integracoes/pagamentos/asaas.py` implementa a interface de pagamentos (criar subconta da empresa, cobrança Pix e boleto, assinatura recorrente, webhook de baixa com verificação e idempotência), testado contra o sandbox; a implementação falsa continua sendo a padrão em testes.

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
